import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .services import get_teacher_profile, sync_teacher_profile, update_teacher_account_and_profile

DEFAULT_TEACHER_PASSWORD = 'teacher123456'


class TeacherAccountSerializer(serializers.ModelSerializer):
    employee_id = serializers.IntegerField(source='id', read_only=True)
    is_admin = serializers.SerializerMethodField()
    discipline = serializers.SerializerMethodField()
    research_interests = serializers.SerializerMethodField()
    h_index = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = (
            'id',
            'employee_id',
            'username',
            'real_name',
            'department',
            'title',
            'research_direction',
            'bio',
            'discipline',
            'research_interests',
            'h_index',
            'is_active',
            'is_admin',
        )

    def get_is_admin(self, obj):
        return bool(obj.is_staff or obj.is_superuser)

    def get_discipline(self, obj):
        profile = get_teacher_profile(obj)
        return profile.discipline if profile else ''

    def get_research_interests(self, obj):
        profile = get_teacher_profile(obj)
        return profile.research_interests if profile else ''

    def get_h_index(self, obj):
        profile = get_teacher_profile(obj)
        return profile.h_index if profile else 0


class CurrentUserSerializer(TeacherAccountSerializer):
    class Meta(TeacherAccountSerializer.Meta):
        fields = TeacherAccountSerializer.Meta.fields


class CurrentUserUpdateSerializer(serializers.ModelSerializer):
    discipline = serializers.CharField(required=False, allow_blank=True, max_length=200)
    research_interests = serializers.CharField(required=False, allow_blank=True)
    h_index = serializers.IntegerField(required=False, min_value=0)

    class Meta:
        model = get_user_model()
        fields = (
            'real_name',
            'department',
            'title',
            'research_direction',
            'bio',
            'discipline',
            'research_interests',
            'h_index',
        )

    def update(self, instance, validated_data):
        profile = get_teacher_profile(instance)
        discipline = validated_data.pop('discipline', profile.discipline if profile else '')
        research_interests = validated_data.pop('research_interests', profile.research_interests if profile else '')
        h_index = validated_data.pop('h_index', profile.h_index if profile else 0)

        update_teacher_account_and_profile(
            instance,
            validated_data,
            {
                'discipline': discipline,
                'research_interests': research_interests,
                'h_index': h_index,
            },
        )

        return instance


class TeacherCreateSerializer(serializers.ModelSerializer):
    employee_id = serializers.CharField(write_only=True)
    discipline = serializers.CharField(required=False, allow_blank=True, max_length=200)
    research_interests = serializers.CharField(required=False, allow_blank=True)
    h_index = serializers.IntegerField(required=False, min_value=0, default=0)
    password = serializers.CharField(write_only=True, required=False, allow_blank=False, style={'input_type': 'password'})
    confirm_password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=False,
        style={'input_type': 'password'},
    )
    initial_password = serializers.CharField(read_only=True)

    class Meta:
        model = get_user_model()
        fields = (
            'employee_id',
            'username',
            'real_name',
            'department',
            'title',
            'research_direction',
            'bio',
            'discipline',
            'research_interests',
            'h_index',
            'password',
            'confirm_password',
            'initial_password',
        )
        extra_kwargs = {
            'username': {'read_only': True},
            'real_name': {'required': True},
            'department': {'required': True},
            'title': {'required': True},
        }

    def validate_employee_id(self, value):
        if not re.fullmatch(r'\d{6}', value):
            raise serializers.ValidationError('Employee ID must be a 6-digit number.')

        user_model = get_user_model()
        if user_model.objects.filter(id=int(value)).exists():
            raise serializers.ValidationError('This employee ID already exists.')

        if user_model.objects.filter(username=value).exists():
            raise serializers.ValidationError('This employee ID is already used as a login account.')

        return value

    def validate(self, attrs):
        employee_id = attrs.get('employee_id', '')
        request = self.context.get('request')
        is_admin_creation = bool(request and request.user and request.user.is_authenticated)
        password = attrs.get('password')
        confirm_password = attrs.get('confirm_password')

        if not is_admin_creation and not password:
            raise serializers.ValidationError({'password': 'Please set a password during registration.'})

        if password or confirm_password:
            if password != confirm_password:
                raise serializers.ValidationError({'confirm_password': 'The two passwords do not match.'})

            temp_user = get_user_model()(
                id=int(employee_id) if employee_id.isdigit() else None,
                username=employee_id,
                real_name=attrs.get('real_name', ''),
            )
            validate_password(password, user=temp_user)

        return attrs

    def create(self, validated_data):
        employee_id = int(validated_data.pop('employee_id'))
        discipline = validated_data.pop('discipline', '')
        research_interests = validated_data.pop('research_interests', '')
        h_index = validated_data.pop('h_index', 0)
        password = validated_data.pop('password', '') or DEFAULT_TEACHER_PASSWORD
        validated_data.pop('confirm_password', None)

        user_model = get_user_model()
        login_account = str(employee_id)
        user = user_model(
            id=employee_id,
            username=login_account,
            is_active=True,
            is_staff=False,
            is_superuser=False,
            **validated_data,
        )
        user.set_password(password)
        user.save()

        sync_teacher_profile(
            user,
            {
                'department': user.department or '',
                'title': user.title or '',
                'discipline': discipline,
                'research_interests': research_interests,
                'h_index': h_index,
            },
        )

        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            user.initial_password = password

        return user

    def to_representation(self, instance):
        data = TeacherAccountSerializer(instance).data
        if hasattr(instance, 'initial_password'):
            data['initial_password'] = instance.initial_password
        return data


class TeacherUpdateSerializer(CurrentUserUpdateSerializer):
    class Meta(CurrentUserUpdateSerializer.Meta):
        fields = CurrentUserUpdateSerializer.Meta.fields + ('is_active',)


class ForgotPasswordResetSerializer(serializers.Serializer):
    employee_id = serializers.CharField()
    real_name = serializers.CharField()
    new_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    default_error_messages = {
        'identity_mismatch': 'The employee ID or real name is incorrect.',
        'inactive_user': 'This account is inactive. Please contact an administrator.',
    }

    def validate_employee_id(self, value):
        if not re.fullmatch(r'\d{6}', value):
            raise serializers.ValidationError('Employee ID must be a 6-digit number.')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'The two passwords do not match.'})

        user_model = get_user_model()
        login_account = attrs['employee_id']
        try:
            user = user_model.objects.get(id=int(attrs['employee_id']), username=login_account)
        except user_model.DoesNotExist as exc:
            raise serializers.ValidationError({'detail': self.error_messages['identity_mismatch']}) from exc

        if (user.real_name or '').strip() != attrs['real_name'].strip():
            raise serializers.ValidationError({'detail': self.error_messages['identity_mismatch']})

        if not user.is_active:
            raise serializers.ValidationError({'detail': self.error_messages['inactive_user']})

        validate_password(attrs['new_password'], user=user)
        attrs['user'] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data['user']
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        return user
