from rest_framework import serializers

from apps.aptitude.models import AptitudeAnswer, AptitudeAttempt, AptitudeQuestion


class AptitudeQuestionSerializer(serializers.ModelSerializer):
    """
    Student-facing serializer for active aptitude questions.
    Never exposes correct_option or explanation to prevent leakage.
    """

    class Meta:
        model = AptitudeQuestion
        fields = [
            "id",
            "category",
            "topic",
            "difficulty",
            "question_text",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "marks",
        ]
        read_only_fields = fields


class AptitudeQuestionDetailSerializer(serializers.ModelSerializer):
    """
    Full question serializer exposing correct_option and explanation.
    Used ONLY after an attempt has been finalized/submitted.
    """

    class Meta:
        model = AptitudeQuestion
        fields = [
            "id",
            "category",
            "topic",
            "difficulty",
            "question_text",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "correct_option",
            "explanation",
            "marks",
        ]
        read_only_fields = fields


class AptitudeAttemptStartSerializer(serializers.Serializer):
    """
    Serializer to validate incoming request to start an aptitude attempt.
    """

    category = serializers.ChoiceField(
        choices=AptitudeQuestion.Category.choices,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    topic = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=100,
    )
    difficulty = serializers.ChoiceField(
        choices=AptitudeQuestion.Difficulty.choices,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    number_of_questions = serializers.IntegerField(
        required=False,
        default=10,
        min_value=1,
        max_value=50,
    )


class AptitudeAnswerSubmitSerializer(serializers.Serializer):
    """
    Serializer for submitting an individual answer during an in-progress attempt.
    """

    question_id = serializers.IntegerField(required=True)
    selected_option = serializers.ChoiceField(
        choices=AptitudeQuestion.Option.choices,
        required=True,
    )


class AptitudeAttemptSerializer(serializers.ModelSerializer):
    """
    Serializer for listing and retrieving student's aptitude attempts summary.
    """

    student = serializers.EmailField(
        source="student.email",
        read_only=True,
    )

    class Meta:
        model = AptitudeAttempt
        fields = [
            "id",
            "student",
            "category",
            "topic",
            "difficulty",
            "total_questions",
            "correct_answers",
            "wrong_answers",
            "unanswered",
            "score",
            "accuracy",
            "time_taken_seconds",
            "started_at",
            "submitted_at",
            "created_at",
        ]
        read_only_fields = fields


class AptitudeAnswerDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for answers attached to an attempt.
    """

    question = serializers.SerializerMethodField()

    class Meta:
        model = AptitudeAnswer
        fields = [
            "id",
            "question",
            "selected_option",
            "is_correct",
            "marks_awarded",
            "answered_at",
        ]
        read_only_fields = fields

    def get_question(self, obj):
        attempt = obj.attempt
        if attempt.is_submitted:
            return AptitudeQuestionDetailSerializer(obj.question).data
        return AptitudeQuestionSerializer(obj.question).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # If the attempt has not been submitted yet, hide correctness details
        if not instance.attempt.is_submitted:
            data.pop("is_correct", None)
            data.pop("marks_awarded", None)
        return data


class AptitudeAttemptDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for an attempt, including its answers and questions.
    """

    student = serializers.EmailField(
        source="student.email",
        read_only=True,
    )
    answers = AptitudeAnswerDetailSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = AptitudeAttempt
        fields = [
            "id",
            "student",
            "category",
            "topic",
            "difficulty",
            "total_questions",
            "correct_answers",
            "wrong_answers",
            "unanswered",
            "score",
            "accuracy",
            "time_taken_seconds",
            "started_at",
            "submitted_at",
            "created_at",
            "answers",
        ]
        read_only_fields = fields
