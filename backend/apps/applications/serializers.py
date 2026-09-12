from rest_framework import serializers

from .models import Application


class ApplicationSerializer(serializers.ModelSerializer):

    company_name = serializers.CharField(
        source="company.name",
        read_only=True,
    )

    class Meta:
        model = Application
        fields = [
            "id",
            "company",
            "company_name",
            "status",
            "applied_at",
            "notes",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "company_name",
            "applied_at",
            "created_at",
            "updated_at",
        ]

    def validate_company(self, company):
        request = self.context.get("request")

        if request and request.user.is_authenticated:
            already_exists = Application.objects.filter(
                student=request.user,
                company=company,
            ).exists()

            if already_exists:
                raise serializers.ValidationError(
                    "You have already applied to this company."
                )

        return company