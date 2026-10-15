from rest_framework import serializers

from apps.career_recommendations.models import CareerRecommendation


class CareerRecommendationSerializer(serializers.ModelSerializer):
    student = serializers.EmailField(
        source="student.email",
        read_only=True,
    )

    class Meta:
        model = CareerRecommendation
        fields = [
            "id",
            "student",
            "target_role",
            "match_score",
            "explanation",
            "matching_skills",
            "missing_skills",
            "recommended_skills",
            "suggested_projects",
            "learning_roadmap",
            "source_summary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SkillGapItemSerializer(serializers.ModelSerializer):
    priority_skills = serializers.SerializerMethodField()

    class Meta:
        model = CareerRecommendation
        fields = [
            "id",
            "target_role",
            "match_score",
            "matching_skills",
            "missing_skills",
            "priority_skills",
        ]
        read_only_fields = fields

    def get_priority_skills(self, obj):
        if obj.recommended_skills:
            return obj.recommended_skills[:5]
        return obj.missing_skills[:5]


class LearningRoadmapItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerRecommendation
        fields = [
            "id",
            "target_role",
            "match_score",
            "suggested_projects",
            "learning_roadmap",
        ]
        read_only_fields = fields
