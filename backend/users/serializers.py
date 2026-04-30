import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.utils import timezone
from rest_framework import serializers

from .access import is_admin_user, is_college_admin_user, is_system_admin_user, is_teacher_user
from .college_catalog import normalize_college_name
from .services import (
    build_teacher_management_summary,
    build_public_contact_channels,
    get_teacher_profile,
    get_user_account_status_label,
    get_user_contact_visibility_label,
    get_user_next_action_hint,
    get_user_password_status_label,
    get_user_permission_scope,
    get_user_role_code,
    get_user_role_label,
    get_user_security_notice,
    clear_password_change_notifications,
    build_forgot_password_cache_key,
    FORGOT_PASSWORD_CODE_TTL_SECONDS,
    generate_local_verification_code,
    is_valid_contact_phone,
    ensure_password_change_notification,
    set_user_password,
    sync_teacher_profile,
    update_teacher_account_and_profile,
)
from .models import College, TeacherTitleChangeRequest, UserNotification
from .title_catalog import is_valid_teacher_professional_title, normalize_title

DEFAULT_TEACHER_PASSWORD = "teacher123456"


def mask_contact_value(value: str | None, reset_via: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        return ""
    if reset_via == "phone":
        if len(normalized) <= 7:
            return normalized[:1] + "*" * max(len(normalized) - 2, 3) + normalized[-1:]
        return f"{normalized[:3]}{'*' * (len(normalized) - 7)}{normalized[-4:]}"

    local, separator, domain = normalized.partition("@")
    if not separator:
        return normalized[:1] + "*" * max(len(normalized) - 2, 3) + normalized[-1:]
    if len(local) <= 2:
        masked_local = local[:1] + "***"
    else:
        masked_local = f"{local[:1]}{'*' * max(len(local) - 2, 3)}{local[-1:]}"
    domain_name, dot, suffix = domain.partition(".")
    masked_domain = f"{domain_name[:1]}***"
    if dot:
        masked_domain = f"{masked_domain}.{suffix}"
    return f"{masked_local}@{masked_domain}"


def validate_existing_college_department(value: str | None) -> str:
    normalized = normalize_college_name(value)
    if not normalized:
        raise serializers.ValidationError("请选择所属学院。")
    if not College.objects.filter(name=normalized, is_active=True).exists():
        raise serializers.ValidationError("所属学院不存在，请先由系统管理员在学院管理中维护。")
    return normalized


class CollegeSerializer(serializers.ModelSerializer):
    account_count = serializers.SerializerMethodField()
    teacher_count = serializers.SerializerMethodField()
    college_admin_count = serializers.SerializerMethodField()

    class Meta:
        model = College
        fields = (
            "id",
            "name",
            "is_active",
            "sort_order",
            "account_count",
            "teacher_count",
            "college_admin_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_name(self, value):
        normalized = normalize_college_name(value)
        if not normalized:
            raise serializers.ValidationError("请填写学院名称。")
        queryset = College.objects.filter(name=normalized)
        if self.instance is not None:
            queryset = queryset.exclude(id=self.instance.id)
        if queryset.exists():
            raise serializers.ValidationError("该学院已经存在。")
        return normalized

    def get_account_count(self, obj):
        user_model = get_user_model()
        return user_model.objects.filter(department=obj.name, is_superuser=False).count()

    def get_teacher_count(self, obj):
        user_model = get_user_model()
        return user_model.objects.filter(department=obj.name, is_staff=False, is_superuser=False).count()

    def get_college_admin_count(self, obj):
        user_model = get_user_model()
        return user_model.objects.filter(department=obj.name, is_staff=True, is_superuser=False).count()


class TeacherAccountSerializer(serializers.ModelSerializer):
    employee_id = serializers.IntegerField(source="id", read_only=True)
    is_admin = serializers.SerializerMethodField()
    role_code = serializers.SerializerMethodField()
    role_label = serializers.SerializerMethodField()
    permission_scope = serializers.SerializerMethodField()
    discipline = serializers.SerializerMethodField()
    research_interests = serializers.SerializerMethodField()
    security_notice = serializers.SerializerMethodField()
    contact_visibility_label = serializers.SerializerMethodField()
    public_contact_channels = serializers.SerializerMethodField()
    account_status_label = serializers.SerializerMethodField()
    password_status_label = serializers.SerializerMethodField()
    next_action_hint = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "employee_id",
            "username",
            "real_name",
            "department",
            "title",
            "email",
            "contact_phone",
            "avatar_url",
            "contact_visibility",
            "contact_visibility_label",
            "public_contact_channels",
            "research_direction",
            "bio",
            "discipline",
            "research_interests",
            "is_active",
            "is_admin",
            "role_code",
            "role_label",
            "permission_scope",
            "password_reset_required",
            "password_updated_at",
            "security_notice",
            "account_status_label",
            "password_status_label",
            "next_action_hint",
        )

    def get_is_admin(self, obj):
        return bool(obj.is_staff or obj.is_superuser)

    def get_role_code(self, obj):
        return get_user_role_code(obj)

    def get_role_label(self, obj):
        return get_user_role_label(obj)

    def get_permission_scope(self, obj):
        return get_user_permission_scope(obj)

    def get_discipline(self, obj):
        profile = get_teacher_profile(obj)
        return profile.discipline if profile else ""

    def get_research_interests(self, obj):
        profile = get_teacher_profile(obj)
        return profile.research_interests if profile else ""

    def get_security_notice(self, obj):
        return get_user_security_notice(obj)

    def get_contact_visibility_label(self, obj):
        return get_user_contact_visibility_label(obj)

    def get_public_contact_channels(self, obj):
        return build_public_contact_channels(obj)

    def get_account_status_label(self, obj):
        return get_user_account_status_label(obj)

    def get_password_status_label(self, obj):
        return get_user_password_status_label(obj)

    def get_next_action_hint(self, obj):
        return get_user_next_action_hint(obj)


class CurrentUserSerializer(TeacherAccountSerializer):
    class Meta(TeacherAccountSerializer.Meta):
        fields = TeacherAccountSerializer.Meta.fields


class CurrentUserUpdateSerializer(serializers.ModelSerializer):
    discipline = serializers.CharField(required=False, allow_blank=True, max_length=200)
    research_interests = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    avatar_url = serializers.URLField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(required=False, allow_blank=True, max_length=30)
    current_password = serializers.CharField(required=False, write_only=True, style={"input_type": "password"})
    contact_visibility = serializers.ChoiceField(
        required=False,
        choices=("email_only", "phone_only", "both", "internal_only"),
    )

    class Meta:
        model = get_user_model()
        fields = (
            "real_name",
            "department",
            "title",
            "email",
            "contact_phone",
            "avatar_url",
            "contact_visibility",
            "research_direction",
            "bio",
            "discipline",
            "research_interests",
            "current_password",
        )

    def validate_title(self, value: str):
        normalized = normalize_title(value)
        request = self.context.get("request")
        request_user = getattr(request, "user", None)
        instance = getattr(self, "instance", None)
        if instance is not None and is_admin_user(instance):
            return normalized
        if instance is not None and request_user is not None and is_teacher_user(request_user) and request_user.id == instance.id:
            current_title = normalize_title(getattr(instance, "title", ""))
            if normalized != current_title:
                raise serializers.ValidationError("职称变更需提交学院管理员审核，请使用“提交职称变更申请”。")
            return current_title
        if normalized and not is_valid_teacher_professional_title(normalized):
            raise serializers.ValidationError("职称需从系统预设选项中选择。")
        return normalized

    def validate_contact_phone(self, value: str):
        normalized = (value or "").strip()
        if normalized and not is_valid_contact_phone(normalized):
            raise serializers.ValidationError("联系电话必须为 11 位手机号。")
        return normalized

    def validate(self, attrs):
        request = self.context.get("request")
        request_user = getattr(request, "user", None)
        instance = getattr(self, "instance", None)
        email = (attrs.get("email", getattr(instance, "email", "")) or "").strip()
        contact_phone = (attrs.get("contact_phone", getattr(instance, "contact_phone", "")) or "").strip()

        if "department" in attrs:
            requested_department = normalize_college_name(attrs.get("department"))
            current_department = normalize_college_name(getattr(instance, "department", ""))

            if instance is not None and is_system_admin_user(instance):
                attrs["department"] = requested_department
            elif request_user is not None and is_college_admin_user(request_user):
                allowed_department = normalize_college_name(getattr(request_user, "department", ""))
                if requested_department != allowed_department:
                    raise serializers.ValidationError({"department": "学院管理员只能维护本学院账号，不能调整所属学院。"})
                attrs["department"] = validate_existing_college_department(allowed_department)
            elif (
                instance is not None
                and request_user is not None
                and request_user.id == instance.id
                and not is_system_admin_user(request_user)
            ):
                if requested_department != current_department:
                    raise serializers.ValidationError({"department": "所属学院由管理员维护，教师本人不能自行调整。"})
                attrs["department"] = validate_existing_college_department(current_department)
            else:
                attrs["department"] = validate_existing_college_department(requested_department)

        if instance is not None and request_user is not None and is_teacher_user(request_user) and request_user.id == instance.id:
            errors = {}
            if not email:
                errors["email"] = "教师账号必须绑定个人邮箱。"
            if not contact_phone:
                errors["contact_phone"] = "教师账号必须绑定联系电话。"
            original_email = (getattr(instance, "email", "") or "").strip()
            original_phone = (getattr(instance, "contact_phone", "") or "").strip()
            contact_changed = (
                ("email" in attrs and email != original_email)
                or ("contact_phone" in attrs and contact_phone != original_phone)
            )
            if contact_changed:
                current_password = attrs.get("current_password", "")
                if not current_password:
                    errors["current_password"] = "修改手机号或邮箱时需要输入当前密码验证身份。"
                elif not instance.check_password(current_password):
                    errors["current_password"] = "当前密码输入不正确。"
            if errors:
                raise serializers.ValidationError(errors)

        attrs["email"] = email
        attrs["contact_phone"] = contact_phone
        return attrs

    def update(self, instance, validated_data):
        profile = get_teacher_profile(instance)
        discipline = validated_data.pop("discipline", profile.discipline if profile else "")
        research_interests = validated_data.pop(
            "research_interests", profile.research_interests if profile else ""
        )
        validated_data.pop("current_password", None)
        update_teacher_account_and_profile(
            instance,
            validated_data,
            {
                "discipline": discipline,
                "research_interests": research_interests,
            },
        )

        return instance


class TeacherCreateSerializer(serializers.ModelSerializer):
    role_code = serializers.CharField(write_only=True, required=False, allow_blank=True)
    employee_id = serializers.CharField(write_only=True)
    discipline = serializers.CharField(required=False, allow_blank=True, max_length=200)
    research_interests = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    avatar_url = serializers.URLField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(required=False, allow_blank=True, max_length=30)
    contact_visibility = serializers.ChoiceField(
        required=False,
        choices=("email_only", "phone_only", "both", "internal_only"),
    )
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=False, style={"input_type": "password"}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=False,
        style={"input_type": "password"},
    )
    initial_password = serializers.CharField(read_only=True)

    class Meta:
        model = get_user_model()
        fields = (
            "employee_id",
            "role_code",
            "username",
            "real_name",
            "department",
            "title",
            "email",
            "contact_phone",
            "avatar_url",
            "contact_visibility",
            "research_direction",
            "bio",
            "discipline",
            "research_interests",
            "password",
            "confirm_password",
            "initial_password",
        )
        extra_kwargs = {
            "username": {"read_only": True},
            "real_name": {"required": True},
            "department": {"required": True},
            "title": {"required": False},
        }

    def validate_employee_id(self, value):
        if not re.fullmatch(r"\d{6}", value):
            raise serializers.ValidationError("工号必须是 6 位数字。")

        user_model = get_user_model()
        if user_model.objects.filter(id=int(value)).exists():
            raise serializers.ValidationError("该工号已存在。")

        if user_model.objects.filter(username=value).exists():
            raise serializers.ValidationError("该工号已被占用为登录账号。")

        return value

    def validate_contact_phone(self, value: str):
        normalized = (value or "").strip()
        if normalized and not is_valid_contact_phone(normalized):
            raise serializers.ValidationError("联系电话必须为 11 位手机号。")
        return normalized

    def validate(self, attrs):
        employee_id = attrs.get("employee_id", "")
        request = self.context.get("request")
        request_user = getattr(request, "user", None)
        is_admin_creation = bool(request and is_admin_user(request_user))
        password = attrs.get("password")
        confirm_password = attrs.get("confirm_password")
        requested_role_code = (attrs.get("role_code") or "").strip() or "teacher"

        if is_system_admin_user(request_user):
            if requested_role_code != "college_admin":
                raise serializers.ValidationError({"role_code": "系统管理员当前仅可创建学院管理员账号。"})
        elif is_college_admin_user(request_user):
            if requested_role_code != "teacher":
                raise serializers.ValidationError({"role_code": "学院管理员当前仅可创建本学院教师账号。"})
            attrs["department"] = request_user.department or ""
        else:
            attrs["role_code"] = "teacher"

        if is_college_admin_user(request_user):
            attrs["department"] = request_user.department or ""

        try:
            attrs["department"] = validate_existing_college_department(attrs.get("department"))
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({"department": exc.detail}) from exc

        title = normalize_title(attrs.get("title"))
        email = (attrs.get("email") or "").strip()
        contact_phone = (attrs.get("contact_phone") or "").strip()
        if requested_role_code == "teacher":
            if not title:
                raise serializers.ValidationError({"title": "请选择教师职称。"})
            if not is_valid_teacher_professional_title(title):
                raise serializers.ValidationError({"title": "教师职称需从系统预设选项中选择。"})
            if not email:
                raise serializers.ValidationError({"email": "创建教师账号时必须填写个人邮箱。"})
            if not contact_phone:
                raise serializers.ValidationError({"contact_phone": "创建教师账号时必须填写联系电话。"})
        else:
            title = "学院管理员"
            attrs["research_direction"] = []
            attrs["bio"] = ""
            attrs["discipline"] = ""
            attrs["research_interests"] = ""
            attrs["email"] = email
            attrs["contact_phone"] = contact_phone
        attrs["title"] = title
        attrs["email"] = email
        attrs["contact_phone"] = contact_phone
        attrs["role_code"] = requested_role_code

        if not is_admin_creation and not password:
            raise serializers.ValidationError({"password": "教师自助注册时必须设置登录密码。"})

        if password or confirm_password:
            if password != confirm_password:
                raise serializers.ValidationError({"confirm_password": "两次输入的密码不一致。"})

            temp_user = get_user_model()(
                id=int(employee_id) if employee_id.isdigit() else None,
                username=employee_id,
                real_name=attrs.get("real_name", ""),
            )
            validate_password(password, user=temp_user)

        return attrs

    def create(self, validated_data):
        role_code = (validated_data.pop("role_code", "") or "teacher").strip() or "teacher"
        employee_id = int(validated_data.pop("employee_id"))
        discipline = validated_data.pop("discipline", "")
        research_interests = validated_data.pop("research_interests", "")
        password = validated_data.pop("password", "") or DEFAULT_TEACHER_PASSWORD
        validated_data.pop("confirm_password", None)

        request = self.context.get("request")
        request_user = getattr(request, "user", None)
        is_admin_creation = bool(request and is_admin_user(request_user))
        login_account = str(employee_id)
        if is_college_admin_user(request_user):
            validated_data["department"] = validate_existing_college_department(request_user.department)
        user_model = get_user_model()
        user = user_model(
            id=employee_id,
            username=login_account,
            is_active=True,
            is_staff=role_code == "college_admin",
            is_superuser=False,
            password_reset_required=is_admin_creation,
            password_updated_at=timezone.now(),
            **validated_data,
        )
        user.set_password(password)
        user.save()

        sync_teacher_profile(
            user,
            {
                "department": user.department or "",
                "title": user.title or "",
                "discipline": discipline,
                "research_interests": research_interests,
            },
        )

        if is_admin_creation:
            user.initial_password = password
            ensure_password_change_notification(
                user,
                temporary_password=password,
                created_by_admin=True,
            )

        return user

    def to_representation(self, instance):
        data = TeacherAccountSerializer(instance).data
        if hasattr(instance, "initial_password"):
            data["initial_password"] = instance.initial_password
        return data


class TeacherUpdateSerializer(CurrentUserUpdateSerializer):
    class Meta(CurrentUserUpdateSerializer.Meta):
        fields = CurrentUserUpdateSerializer.Meta.fields + ("is_active",)


class TeacherTitleChangeRequestSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    teacher_id = serializers.IntegerField(source="teacher.id", read_only=True)
    teacher_name = serializers.CharField(source="teacher.real_name", read_only=True)
    teacher_employee_id = serializers.CharField(source="teacher.username", read_only=True)
    teacher_department = serializers.CharField(source="teacher.department", read_only=True)
    reviewer_name = serializers.SerializerMethodField()

    class Meta:
        model = TeacherTitleChangeRequest
        fields = (
            "id",
            "teacher_id",
            "teacher_name",
            "teacher_employee_id",
            "teacher_department",
            "current_title",
            "requested_title",
            "apply_reason",
            "status",
            "status_label",
            "review_comment",
            "reviewer_name",
            "created_at",
            "reviewed_at",
        )

    def get_reviewer_name(self, obj):
        if not obj.reviewer_id:
            return ""
        return obj.reviewer.real_name or obj.reviewer.username


class TeacherTitleChangeRequestCreateSerializer(serializers.Serializer):
    requested_title = serializers.CharField(max_length=50)
    apply_reason = serializers.CharField(required=False, allow_blank=True, max_length=300)

    default_error_messages = {
        "same_title": "申请职称与当前职称一致，无需提交审核。",
        "pending_exists": "已有待审核的职称变更申请，请等待学院管理员处理。",
    }

    def validate_requested_title(self, value):
        normalized = normalize_title(value)
        if not is_valid_teacher_professional_title(normalized):
            raise serializers.ValidationError("申请职称需从系统预设选项中选择。")
        return normalized

    def validate(self, attrs):
        user = self.context["request"].user
        current_title = normalize_title(getattr(user, "title", ""))
        requested_title = attrs["requested_title"]

        if requested_title == current_title:
            raise serializers.ValidationError({"requested_title": self.error_messages["same_title"]})

        has_pending = TeacherTitleChangeRequest.objects.filter(
            teacher=user,
            status=TeacherTitleChangeRequest.STATUS_PENDING,
        ).exists()
        if has_pending:
            raise serializers.ValidationError({"detail": self.error_messages["pending_exists"]})

        attrs["current_title"] = current_title
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        return TeacherTitleChangeRequest.objects.create(
            teacher=user,
            current_title=validated_data["current_title"],
            requested_title=validated_data["requested_title"],
            apply_reason=(validated_data.get("apply_reason") or "").strip(),
            status=TeacherTitleChangeRequest.STATUS_PENDING,
        )


class TeacherTitleChangeRequestReviewSerializer(serializers.Serializer):
    review_comment = serializers.CharField(required=False, allow_blank=True, max_length=300)


class TeacherTitleChangeRequestRejectSerializer(serializers.Serializer):
    review_comment = serializers.CharField(required=True, allow_blank=False, max_length=300)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    confirm_password = serializers.CharField(write_only=True, style={"input_type": "password"})

    default_error_messages = {
        "current_password_incorrect": "当前密码输入不正确。",
        "same_password": "新密码不能与当前密码相同。",
        "inactive_user": "当前账户已停用，无法修改密码。",
    }

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.is_active:
            raise serializers.ValidationError({"detail": self.error_messages["inactive_user"]})

        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError(
                {"current_password": self.error_messages["current_password_incorrect"]}
            )

        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "两次输入的新密码不一致。"})

        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError({"new_password": self.error_messages["same_password"]})

        validate_password(attrs["new_password"], user=user)
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        set_user_password(user, self.validated_data["new_password"], require_password_change=False)
        clear_password_change_notifications(user)
        return user


class ForgotPasswordCodeSerializer(serializers.Serializer):
    employee_id = serializers.CharField()
    reset_via = serializers.ChoiceField(choices=("phone", "email"))

    default_error_messages = {
        "identity_mismatch": "工号与绑定信息不匹配，请重新确认。",
        "admin_account": "管理员账号不支持通过该入口找回密码，请联系上级管理员处理。",
        "inactive_account": "当前账号已停用，请联系管理员处理。",
        "missing_phone": "当前账号尚未绑定手机号，暂时无法通过手机号找回密码。",
        "missing_email": "当前账号尚未绑定邮箱，暂时无法通过邮箱找回密码。",
    }

    def validate_employee_id(self, value):
        normalized = (value or "").strip()
        if not re.fullmatch(r"\d{6}", normalized):
            raise serializers.ValidationError("工号必须是 6 位数字。")
        return normalized

    def validate(self, attrs):
        user_model = get_user_model()
        employee_id = attrs["employee_id"]
        reset_via = attrs["reset_via"]
        try:
            user = user_model.objects.get(id=int(employee_id), username=employee_id)
        except user_model.DoesNotExist as exc:
            raise serializers.ValidationError({"detail": self.error_messages["identity_mismatch"]}) from exc

        if is_admin_user(user):
            raise serializers.ValidationError({"detail": self.error_messages["admin_account"]})
        if not user.is_active:
            raise serializers.ValidationError({"detail": self.error_messages["inactive_account"]})

        if reset_via == "phone":
            contact_value = (getattr(user, "contact_phone", "") or "").strip()
            if not contact_value:
                raise serializers.ValidationError({"detail": self.error_messages["missing_phone"]})
        else:
            contact_value = (getattr(user, "email", "") or "").strip()
            if not contact_value:
                raise serializers.ValidationError({"detail": self.error_messages["missing_email"]})

        attrs["user"] = user
        attrs["contact_value"] = contact_value
        return attrs

    def save(self, **kwargs):
        employee_id = self.validated_data["employee_id"]
        reset_via = self.validated_data["reset_via"]
        contact_value = self.validated_data["contact_value"]
        contact_masked = mask_contact_value(contact_value, reset_via)
        verification_code = generate_local_verification_code()
        cache.set(
            build_forgot_password_cache_key(employee_id, reset_via),
            verification_code,
            FORGOT_PASSWORD_CODE_TTL_SECONDS,
        )
        terminal_message = (
            "[ForgotPasswordCode] "
            f"employee_id={employee_id} reset_via={reset_via} "
            f"contact={contact_masked} code={verification_code} "
            f"ttl_seconds={FORGOT_PASSWORD_CODE_TTL_SECONDS}"
        )
        print(terminal_message, flush=True)
        return {
            "employee_id": employee_id,
            "reset_via": reset_via,
            "ttl_seconds": FORGOT_PASSWORD_CODE_TTL_SECONDS,
            "contact_masked": contact_masked,
            "delivery_hint": "验证码已输出到后端运行终端，请在终端查看后输入。",
        }


class ForgotPasswordConfirmSerializer(serializers.Serializer):
    employee_id = serializers.CharField()
    reset_via = serializers.ChoiceField(choices=("phone", "email"))
    verification_code = serializers.CharField()
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    confirm_password = serializers.CharField(write_only=True, style={"input_type": "password"})

    default_error_messages = {
        "identity_mismatch": "工号与绑定信息不匹配，请重新确认。",
        "admin_account": "管理员账号不支持通过该入口找回密码，请联系上级管理员处理。",
        "inactive_account": "当前账号已停用，请联系管理员处理。",
        "invalid_code": "验证码无效或已过期，请重新获取。",
    }

    def validate_employee_id(self, value):
        normalized = (value or "").strip()
        if not re.fullmatch(r"\d{6}", normalized):
            raise serializers.ValidationError("工号必须是 6 位数字。")
        return normalized

    def validate(self, attrs):
        user_model = get_user_model()
        employee_id = attrs["employee_id"]
        reset_via = attrs["reset_via"]
        try:
            user = user_model.objects.get(id=int(employee_id), username=employee_id)
        except user_model.DoesNotExist as exc:
            raise serializers.ValidationError({"employee_id": self.error_messages["identity_mismatch"]}) from exc

        if is_admin_user(user):
            raise serializers.ValidationError({"detail": self.error_messages["admin_account"]})
        if not user.is_active:
            raise serializers.ValidationError({"detail": self.error_messages["inactive_account"]})

        cached_code = cache.get(build_forgot_password_cache_key(employee_id, reset_via))
        if not cached_code or str(cached_code) != (attrs.get("verification_code") or "").strip():
            raise serializers.ValidationError({"verification_code": self.error_messages["invalid_code"]})

        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "两次输入的新密码不一致。"})
        if user.check_password(attrs["new_password"]):
            raise serializers.ValidationError({"new_password": "新密码不能与当前密码相同。"})

        validate_password(attrs["new_password"], user=user)
        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        set_user_password(user, self.validated_data["new_password"], require_password_change=False)
        clear_password_change_notifications(user)
        cache.delete(
            build_forgot_password_cache_key(
                self.validated_data["employee_id"],
                self.validated_data["reset_via"],
            )
        )
        return user


class TeacherBulkActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("activate", "deactivate", "reset_password"))
    user_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )

    default_error_messages = {
        "duplicate_ids": "批量操作中的教师 ID 不能重复。",
    }

    def validate_user_ids(self, value):
        if len(set(value)) != len(value):
            raise serializers.ValidationError(self.error_messages["duplicate_ids"])
        return value


class TeacherManagementSummarySerializer(serializers.Serializer):
    total_count = serializers.IntegerField()
    active_count = serializers.IntegerField()
    inactive_count = serializers.IntegerField()
    password_reset_required_count = serializers.IntegerField()
    stable_password_count = serializers.IntegerField()
    recovery_guidance = serializers.CharField()
    future_extension_hint = serializers.CharField()

    @classmethod
    def from_queryset(cls, queryset):
        return cls(build_teacher_management_summary(queryset))


class CurrentUserAvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.FileField()

    default_error_messages = {
        "invalid_type": "头像上传仅支持 JPG、PNG、WEBP 或 GIF 图片。",
        "file_too_large": "头像文件不能超过 2MB。",
    }

    def validate_avatar(self, value):
        content_type = (getattr(value, "content_type", "") or "").lower()
        file_name = (getattr(value, "name", "") or "").lower()
        allowed_content_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        allowed_extensions = (".jpg", ".jpeg", ".png", ".webp", ".gif")

        if content_type not in allowed_content_types and not file_name.endswith(allowed_extensions):
            raise serializers.ValidationError(self.error_messages["invalid_type"])

        if value.size > 2 * 1024 * 1024:
            raise serializers.ValidationError(self.error_messages["file_too_large"])

        return value


class UserNotificationSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = UserNotification
        fields = (
            "id",
            "category",
            "category_label",
            "title",
            "content",
            "action_path",
            "action_query",
            "payload",
            "is_read",
            "read_at",
            "created_at",
            "sender_name",
        )

    def get_sender_name(self, obj):
        if not obj.sender_id:
            return ""
        return obj.sender.real_name or obj.sender.username
