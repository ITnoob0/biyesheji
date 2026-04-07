from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet

from .models import AchievementClaim, CoAuthor, Paper
from .visibility import APPROVED_STATUS


def _normalize_person_name(name: str) -> str:
    return ' '.join((name or '').strip().split())


def _extract_unique_coauthor_names(coauthors: Iterable[CoAuthor]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for coauthor in coauthors:
        normalized = _normalize_person_name(coauthor.name)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        names.append(normalized)
    return names


def build_teacher_related_paper_queryset(
    teacher_user,
    *,
    approved_only: bool = True,
    include_claimed: bool = True,
) -> QuerySet[Paper]:
    queryset = Paper.objects.all()
    if approved_only:
        queryset = queryset.filter(status=APPROVED_STATUS)

    if include_claimed:
        queryset = queryset.filter(
            Q(teacher=teacher_user)
            | Q(claims__target_user=teacher_user, claims__status__in=['ACCEPTED', 'CONFLICT'])
        )
    else:
        queryset = queryset.filter(teacher=teacher_user)

    return queryset.distinct()


def sync_paper_claim_invitations(paper: Paper) -> dict:
    coauthors = list(paper.coauthors.all())
    coauthor_names = _extract_unique_coauthor_names(coauthors)
    initiator = paper.teacher
    initiator_names = {
        _normalize_person_name(getattr(initiator, 'real_name', '') or ''),
        _normalize_person_name(getattr(initiator, 'username', '') or ''),
    }
    valid_coauthor_names = [name for name in coauthor_names if name not in initiator_names]

    user_model = get_user_model()
    explicit_user_ids = {
        coauthor.internal_teacher_id
        for coauthor in coauthors
        if coauthor.internal_teacher_id and coauthor.internal_teacher_id != initiator.id
    }
    matched_users = list(
        user_model.objects.filter(
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
        .filter(Q(id__in=explicit_user_ids) | Q(real_name__in=valid_coauthor_names))
        .exclude(id=initiator.id)
        .only('id', 'real_name')
    )

    matched_map: dict[str, list] = defaultdict(list)
    for user in matched_users:
        normalized = _normalize_person_name(user.real_name)
        if normalized:
            matched_map[normalized].append(user)

    matched_target_ids: set[int] = set()
    coauthor_to_candidate_ids: dict[int, list[int]] = {}
    candidate_map = {user.id: user for user in matched_users}
    for coauthor in coauthors:
        if coauthor.internal_teacher_id == initiator.id:
            coauthor_to_candidate_ids[coauthor.id] = []
            coauthor.is_internal = True
            coauthor.internal_teacher = initiator
            coauthor.save(update_fields=['is_internal', 'internal_teacher'])
            continue

        candidates = []
        if coauthor.internal_teacher_id and coauthor.internal_teacher_id in candidate_map:
            candidates = [candidate_map[coauthor.internal_teacher_id]]
        else:
            normalized = _normalize_person_name(coauthor.name)
            candidates = matched_map.get(normalized, [])
        coauthor_to_candidate_ids[coauthor.id] = [candidate.id for candidate in candidates]
        matched_target_ids.update(candidate.id for candidate in candidates)

        coauthor.is_internal = bool(candidates)
        coauthor.internal_teacher = candidates[0] if len(candidates) == 1 else None
        coauthor.save(update_fields=['is_internal', 'internal_teacher'])

    created_count = 0
    for coauthor in coauthors:
        candidate_ids = coauthor_to_candidate_ids.get(coauthor.id, [])
        for candidate_id in candidate_ids:
            target_user = candidate_map.get(candidate_id)
            if target_user is None:
                continue
            claim, created = AchievementClaim.objects.get_or_create(
                achievement=paper,
                target_user=target_user,
                defaults={
                    'initiator': initiator,
                    'coauthor': coauthor,
                    'status': 'PENDING',
                    'proposed_author_rank': coauthor.author_rank,
                    'proposed_is_corresponding': coauthor.is_corresponding,
                },
            )
            if created:
                created_count += 1
                continue

            update_fields: list[str] = []
            if claim.initiator_id != initiator.id:
                claim.initiator = initiator
                update_fields.append('initiator')
            if claim.coauthor_id != coauthor.id:
                claim.coauthor = coauthor
                update_fields.append('coauthor')
            if claim.proposed_author_rank != coauthor.author_rank:
                claim.proposed_author_rank = coauthor.author_rank
                update_fields.append('proposed_author_rank')
            if claim.proposed_is_corresponding != bool(coauthor.is_corresponding):
                claim.proposed_is_corresponding = bool(coauthor.is_corresponding)
                update_fields.append('proposed_is_corresponding')
            if claim.status in {'REJECTED', 'CONFLICT'}:
                claim.status = 'PENDING'
                update_fields.append('status')
            if update_fields:
                claim.save(update_fields=update_fields)

    stale_pending_claims = AchievementClaim.objects.filter(
        achievement=paper,
        status='PENDING',
    ).exclude(target_user_id__in=matched_target_ids)
    stale_pending_count = stale_pending_claims.count()
    if stale_pending_count:
        stale_pending_claims.delete()

    return {
        'coauthor_count': len(coauthors),
        'matched_teacher_count': len(matched_target_ids),
        'created_claim_count': created_count,
        'deleted_stale_pending_count': stale_pending_count,
    }
