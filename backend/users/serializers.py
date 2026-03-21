import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers

from .access import is_admin_user
from .services import (
    get_teacher_profile,
    get_user_role_code,
    get_user_role_label,
    get_user_security_notice,
    set_user_password,
    sync_teacher_profile,
    update_teacher_account_and_profile,
)

DEFAULT_TEACHER_PASSWORD = "teacher123456"


class TeacherAccountSerializer(serializers.ModelSerializer):
    employee_id = serializers.IntegerField(source="id", read_only=True)
    is_admin = serializers.SerializerMethodField()
    role_code = serializers.SerializerMethodField()
    role_label = serializers.SerializerMethodField()
    discipline = serializers.SerializerMethodField()
    research_interests = serializers.SerializerMethodField()
    h_index = serializers.SerializerMethodField()
    security_notice = serializers.SerializerMethodField()

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
            "research_direction",
            "bio",
            "discipline",
            "research_interests",
            "h_index",
            "is_active",
            "is_admin",
            "role_code",
            "role_label",
            "password_reset_required",
            "password_updated_at",
            "security_notice",
        )

    def get_is_admin(self, obj):
        return bool(obj.is_staff or obj.is_superuser)

    def get_role_code(self, obj):
        return get_user_role_code(obj)

    def get_role_label(self, obj):
        return get_user_role_label(obj)

    def get_discipline(self, obj):
        profile = get_teacher_profile(obj)
        return profile.discipline if profile else ""

    def get_research_interests(self, obj):
        profile = get_teacher_profile(obj)
        return profile.research_interests if profile else ""

    def get_h_index(self, obj):
        profile = get_teacher_profile(obj)
        return profile.h_index if profile else 0

    def get_security_notice(self, obj):
        return get_user_security_notice(obj)


class CurrentUserSerializer(TeacherAccountSerializer):
    class Meta(TeacherAccountSerializer.Meta):
        fields = TeacherAccountSerializer.Meta.fields


class CurrentUserUpdateSerializer(serializers.ModelSerializer):
    discipline = serializers.CharField(required=False, allow_blank=True, max_length=200)
    research_interests = serializers.CharField(required=False, allow_blank=True)
    h_index = serializers.IntegerField(required=False, min_value=0)
    email = serializers.EmailField(required=False, allow_blank=True)
    avatar_url = serializers.URLField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(required=False, allow_blank=True, max_length=30)

    class Meta:
        model = get_user_model()
        fields = (
            "real_name",
            "department",
            "title",
            "email",
            "contact_phone",
            "avatar_url",
            "research_direction",
            "bio",
            "discipline",
            "research_interests",
            "h_index",
        )

    def update(self, instance, validated_data):
        profile = get_teacher_profile(instance)
        discipline = validated_data.pop("discipline", profile.discipline if profile else "")
        research_interests = validated_data.pop(
            "research_interests", profile.research_interests if profile else ""
        )
        h_index = validated_data.pop("h_index", profile.h_index if profile else 0)

        update_teacher_account_and_profile(
            instance,
            validated_data,
            {
                "discipline": discipline,
                "research_interests": research_interests,
                "h_index": h_index,
            },
        )

        return instance


class TeacherCreateSerializer(serializers.ModelSerializer):
    employee_id = serializers.CharField(write_only=True)
    discipline = serializers.CharField(required=False, allow_blank=True, max_length=200)
    research_interests = serializers.CharField(required=False, allow_blank=True)
    h_index = serializers.IntegerField(required=False, min_value=0, default=0)
    email = serializers.EmailField(required=False, allow_blank=True)
    avatar_url = serializers.URLField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(required=False, allow_blank=True, max_length=30)
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
            "username",
            "real_name",
            "department",
            "title",
            "email",
            "contact_phone",
            "avatar_url",
            "research_direction",
            "bio",
            "discipline",
            "research_interests",
            "h_index",
            "password",
            "confirm_password",
            "initial_password",
        )
        extra_kwargs = {
            "username": {"read_only": True},
            "real_name": {"required": True},
            "department": {"required": True},
            "title": {"required": True},
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

    def validate(self, attrs):
        employee_id = attrs.get("employee_id", "")
        request = self.context.get("request")
        is_admin_creation = bool(request and is_admin_user(getattr(request, "user", None)))
        password = attrs.get("password")
        confirm_password = attrs.get("confirm_password")

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
        employee_id = int(validated_data.pop("employee_id"))
        discipline = validated_data.pop("discipline", "")
        research_interests = validated_data.pop("research_interests", "")
        h_index = validated_data.pop("h_index", 0)
        password = validated_data.pop("password", "") or DEFAULT_TEACHER_PASSWORD
        validated_data.pop("confirm_password", None)

        request = self.context.get("request")
        is_admin_creation = bool(request and is_admin_user(getattr(request, "user", None)))
        login_account = str(employee_id)
        user_model = get_user_model()
        user = user_model(
            id=employee_id,
            username=login_account,
            is_active=True,
            is_staff=False,
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
                "h_index": h_index,
            },
        )

        if is_admin_creation:
            user.initial_password = password

        return user

    def to_representation(self, instance):
        data = TeacherAccountSerializer(instance).data
        if hasattr(instance, "initial_password"):
            data["initial_password"] = instance.initial_password
        return data


class TeacherUpdateSerializer(CurrentUserUpdateSerializer):
    class Meta(CurrentUserUpdateSerializer.Meta):
        fields = CurrentUserUpdateSerializer.Meta.fields + ("is_active",)


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
        return user


class ForgotPasswordResetSerializer(serializers.Serializer):
    employee_id = serializers.CharField()
    real_name = serializers.CharField()
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    confirm_password = serializers.CharField(write_only=True, style={"input_type": "password"})

    default_error_messages = {
        "identity_mismatch": "工号与姓名不匹配，请重新确认。",
        "inactive_user": "当前账户已停用，请联系管理员处理。",
        "admin_account": "管理员账户请联系系统负责人处理密码重置。",
    }

    def validate_employee_id(self, value):
        if not re.fullmatch(r"\d{6}", value):
            raise serializers.ValidationError("工号必须是 6 位数字。")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "两次输入的新密码不一致。"})

        user_model = get_user_model()
        login_account = attrs["employee_id"]
        try:
            user = user_model.objects.get(id=int(attrs["employee_id"]), username=login_account)
        except user_model.DoesNotExist as exc:
            raise serializers.ValidationError({"detail": self.error_messages["identity_mismatch"]}) from exc

        if is_admin_user(user):
            raise serializers.ValidationError({"detail": self.error_messages["admin_account"]})

        if (user.real_name or "").strip() != attrs["real_name"].strip():
            raise serializers.ValidationError({"detail": self.error_messages["identity_mismatch"]})

        if not user.is_active:
            raise serializers.ValidationError({"detail": self.error_messages["inactive_user"]})

        validate_password(attrs["new_password"], user=user)
        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        set_user_password(user, self.validated_data["new_password"], require_password_change=False)
        return user
