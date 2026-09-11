from rest_framework import serializers

from .models import Company


class CompanySerializer(serializers.ModelSerializer):

    class Meta:
        model = Company
        fields = [
            'id',
            'name',
            'description',
            'website',
            'minimum_cgpa',
            'eligible_branches',
            'required_skills',
            'maximum_backlogs',
            'package_lpa',
            'job_role',
            'location',
            'application_deadline',
            'created_at',
            'updated_at',
        ]

        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]