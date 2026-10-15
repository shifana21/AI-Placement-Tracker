from rest_framework import serializers

from apps.ai_interview.models import (
    InterviewAnswer,
    InterviewQuestion,
    MockInterview,
)


class InterviewQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewQuestion
        fields = [
            "id",
            "question_number",
            "question_text",
            "question_type",
            "topic",
            "created_at",
        ]
        read_only_fields = fields


class InterviewAnswerSerializer(serializers.ModelSerializer):
    question = InterviewQuestionSerializer(read_only=True)

    class Meta:
        model = InterviewAnswer
        fields = [
            "id",
            "question",
            "answer_text",
            "score",
            "evaluation",
            "strengths",
            "weaknesses",
            "improvement_suggestions",
            "answered_at",
        ]
        read_only_fields = [
            "id",
            "question",
            "score",
            "evaluation",
            "strengths",
            "weaknesses",
            "improvement_suggestions",
            "answered_at",
        ]


class InterviewAnswerSubmitSerializer(serializers.Serializer):
    answer_text = serializers.CharField(
        max_length=10000,
        required=True,
    )

    def validate_answer_text(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Answer text cannot be empty or whitespace only.")
        return stripped


class MockInterviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MockInterview
        fields = [
            "id",
            "interview_type",
            "target_role",
            "experience_level",
            "number_of_questions",
        ]
        read_only_fields = ["id"]

    def validate_target_role(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Target role cannot be blank.")
        return stripped

    def validate_number_of_questions(self, value):
        if value < 1 or value > 20:
            raise serializers.ValidationError("Number of questions must be between 1 and 20.")
        return value


class MockInterviewSerializer(serializers.ModelSerializer):
    student = serializers.EmailField(
        source="student.email",
        read_only=True,
    )

    class Meta:
        model = MockInterview
        fields = [
            "id",
            "student",
            "interview_type",
            "target_role",
            "experience_level",
            "number_of_questions",
            "current_question",
            "status",
            "overall_score",
            "overall_feedback",
            "strengths",
            "weaknesses",
            "recommendations",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class QuestionResultItemSerializer(serializers.ModelSerializer):
    answer = InterviewAnswerSerializer(read_only=True)

    class Meta:
        model = InterviewQuestion
        fields = [
            "id",
            "question_number",
            "question_text",
            "question_type",
            "topic",
            "answer",
        ]
        read_only_fields = fields


class MockInterviewResultSerializer(serializers.ModelSerializer):
    student = serializers.EmailField(
        source="student.email",
        read_only=True,
    )
    questions = QuestionResultItemSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = MockInterview
        fields = [
            "id",
            "student",
            "interview_type",
            "target_role",
            "experience_level",
            "number_of_questions",
            "status",
            "overall_score",
            "overall_feedback",
            "strengths",
            "weaknesses",
            "recommendations",
            "started_at",
            "completed_at",
            "questions",
        ]
        read_only_fields = fields
