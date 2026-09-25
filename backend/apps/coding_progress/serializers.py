from django.utils import timezone
from rest_framework import serializers

from .models import CodingProblem


class CodingProblemSerializer(serializers.ModelSerializer):
    student = serializers.EmailField(
        source="student.email",
        read_only=True,
    )

    class Meta:
        model = CodingProblem
        fields = [
            "id",
            "student",
            "platform",
            "difficulty",
            "topic",
            "title",
            "problem_url",
            "solved_independently",
            "solved_at",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "student",
            "created_at",
            "updated_at",
        ]

    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Title cannot be blank or whitespace only.")
        return value.strip()

    def validate_solved_at(self, value):
        if timezone.is_naive(value):
            value = timezone.make_aware(value)
        if value > timezone.now():
            raise serializers.ValidationError("solved_at cannot be in the future.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            student = request.user
            platform = attrs.get("platform", getattr(self.instance, "platform", None))
            title = attrs.get("title", getattr(self.instance, "title", None))
            solved_at = attrs.get("solved_at", getattr(self.instance, "solved_at", None))

            if title and platform and solved_at:
                qs = CodingProblem.objects.filter(
                    student=student,
                    platform=platform,
                    title=title,
                    solved_at=solved_at,
                )
                if self.instance:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    raise serializers.ValidationError(
                        "A coding problem with this title, platform, and solved timestamp already exists."
                    )

        return attrs
