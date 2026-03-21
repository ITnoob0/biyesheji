from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class EmployeeTokenObtainPairSerializer(TokenObtainPairSerializer):
    default_error_messages = {
        "no_active_account": "工号/账号或密码错误，请重新输入。",
    }

    def validate(self, attrs):
        username = (attrs.get(self.username_field) or "").strip()
        password = attrs.get("password") or ""
        attrs[self.username_field] = username
        attrs["password"] = password

        user_model = get_user_model()
        user = user_model.objects.filter(username=username).first()

        if user and not user.is_active:
            raise AuthenticationFailed("账户已停用，请联系管理员处理。", code="account_inactive")

        return super().validate(attrs)


class EmployeeTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmployeeTokenObtainPairSerializer
