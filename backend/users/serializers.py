from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import UserRole

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(
        choices=[UserRole.APPLICANT, UserRole.HELPER],
        required=False,
        default=UserRole.APPLICANT,
    )

    class Meta:
        model = User
        fields = ("id", "username", "email", "password", "role", "region")
        read_only_fields = ("id",)

    def validate_role(self, value):
        allowed_roles = {UserRole.APPLICANT, UserRole.HELPER}
        if value not in allowed_roles:
            raise serializers.ValidationError(
                "Public registration is available only for applicant and helper roles."
            )
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "role", "region")
