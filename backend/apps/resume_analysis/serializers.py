from rest_framework import serializers

from .models import ResumeAnalysis


class ResumeAnalysisSerializer(serializers.ModelSerializer):
    analysis_id = serializers.IntegerField(
        source="id",
        read_only=True,
    )
    resume_id = serializers.IntegerField(
        source="resume.id",
        read_only=True,
    )
    original_filename = serializers.CharField(
        source="resume.original_filename",
        read_only=True,
    )

    class Meta:
        model = ResumeAnalysis
        fields = [
            "id",
            "analysis_id",
            "resume",
            "resume_id",
            "original_filename",
            "status",
            "extracted_text",
            "analysis_result",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
