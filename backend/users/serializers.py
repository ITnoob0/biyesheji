from rest_framework import serializers

from .models import CustomUser


class CurrentUserSerializer(serializers.ModelSerializer):
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'real_name', 'department', 'title', 'is_admin')

    def get_is_admin(self, obj):
        return bool(obj.is_staff or obj.is_superuser)
