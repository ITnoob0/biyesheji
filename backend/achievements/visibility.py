from __future__ import annotations

from django.db.models import QuerySet


APPROVED_STATUS = 'APPROVED'


def approved_queryset(queryset: QuerySet) -> QuerySet:
    return queryset.filter(status=APPROVED_STATUS)
