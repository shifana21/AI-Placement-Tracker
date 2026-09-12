from rest_framework import serializers
from django.db import transaction
from .models import Resume


class ResumeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Resume
        fields = [
            "id",
            "file",
            "original_filename",
            "uploaded_at",
            "updated_at",
            "is_active",
        ]
        read_only_fields = [
            "id",
            "original_filename",
            "uploaded_at",
            "updated_at",
            "is_active",
        ]

    def validate_file(self, uploaded_file):
        allowed_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]

        if uploaded_file.content_type not in allowed_types:
            raise serializers.ValidationError(
                "Only PDF and DOCX files are allowed."
            )

        max_size = 5 * 1024 * 1024

        if uploaded_file.size > max_size:
            raise serializers.ValidationError(
                "Resume file size must not exceed 5 MB."
            )

        return uploaded_file

    def create(self, validated_data):
        request = self.context["request"]
        uploaded_file = validated_data["file"]

        with transaction.atomic():
            Resume.objects.filter(
                student=request.user,
                is_active=True,
            ).update(is_active=False)

            return Resume.objects.create(
                student=request.user,
                file=uploaded_file,
                original_filename=uploaded_file.name,
                is_active=True,
            )