import datetime
from datetime import timedelta

from django.db import models
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CodingProblem
from .serializers import CodingProblemSerializer


class CodingProblemListCreateView(generics.ListCreateAPIView):
    serializer_class = CodingProblemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CodingProblem.objects.filter(
            student=self.request.user
        ).order_by("-solved_at")

        platform = self.request.query_params.get("platform")
        difficulty = self.request.query_params.get("difficulty")
        topic = self.request.query_params.get("topic")

        if platform:
            queryset = queryset.filter(platform=platform)

        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        if topic:
            queryset = queryset.filter(topic__icontains=topic)

        return queryset

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


class CodingProblemDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CodingProblemSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return CodingProblem.objects.filter(
            student=self.request.user
        )


class CodingProblemStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_qs = CodingProblem.objects.filter(student=request.user)

        total_problems = user_qs.count()

        diff_agg = user_qs.aggregate(
            EASY=Count("id", filter=models.Q(difficulty=CodingProblem.Difficulty.EASY)),
            MEDIUM=Count("id", filter=models.Q(difficulty=CodingProblem.Difficulty.MEDIUM)),
            HARD=Count("id", filter=models.Q(difficulty=CodingProblem.Difficulty.HARD)),
        )
        problems_by_difficulty = {
            "EASY": diff_agg["EASY"] or 0,
            "MEDIUM": diff_agg["MEDIUM"] or 0,
            "HARD": diff_agg["HARD"] or 0,
        }

        platform_agg = user_qs.aggregate(
            **{
                plat.value: Count("id", filter=models.Q(platform=plat.value))
                for plat in CodingProblem.Platform
            }
        )
        problems_by_platform = {
            plat.value: platform_agg.get(plat.value, 0) or 0
            for plat in CodingProblem.Platform
        }

        topic_counts = (
            user_qs.exclude(topic="")
            .values("topic")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        problems_by_topic = {item["topic"]: item["count"] for item in topic_counts}

        indep_agg = user_qs.aggregate(
            independent=Count("id", filter=models.Q(solved_independently=True)),
            assisted=Count("id", filter=models.Q(solved_independently=False)),
        )
        independent_vs_assisted = {
            "independent": indep_agg["independent"] or 0,
            "assisted": indep_agg["assisted"] or 0,
        }

        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)

        activity_agg = user_qs.aggregate(
            last_7_days=Count("id", filter=models.Q(solved_at__gte=seven_days_ago)),
            last_30_days=Count("id", filter=models.Q(solved_at__gte=thirty_days_ago)),
        )
        last_7_days = activity_agg["last_7_days"] or 0
        last_30_days = activity_agg["last_30_days"] or 0

        # Latest 6 calendar months (chronological order)
        months = []
        curr_y = now.year
        curr_m = now.month
        for i in range(6):
            m = curr_m - i
            y = curr_y
            while m <= 0:
                m += 12
                y -= 1
            months.append((y, m, f"{y:04d}-{m:02d}"))
        months.reverse()

        earliest_y, earliest_m, _ = months[0]
        earliest_start = timezone.make_aware(
            datetime.datetime(earliest_y, earliest_m, 1, 0, 0, 0)
        )

        monthly_agg = (
            user_qs.filter(solved_at__gte=earliest_start)
            .annotate(month_trunc=TruncMonth("solved_at"))
            .values("month_trunc")
            .annotate(count=Count("id"))
            .order_by("month_trunc")
        )
        counts_map = {}
        for row in monthly_agg:
            if row["month_trunc"]:
                counts_map[row["month_trunc"].strftime("%Y-%m")] = row["count"]

        monthly_trend = [
            {"month": label, "count": counts_map.get(label, 0)}
            for _, _, label in months
        ]

        return Response(
            {
                "total_problems": total_problems,
                "problems_by_difficulty": problems_by_difficulty,
                "problems_by_platform": problems_by_platform,
                "problems_by_topic": problems_by_topic,
                "independent_vs_assisted": independent_vs_assisted,
                "last_7_days": last_7_days,
                "last_30_days": last_30_days,
                "monthly_trend": monthly_trend,
            }
        )
