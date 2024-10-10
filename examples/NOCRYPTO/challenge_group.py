from itertools import chain

from django.db.models import Q
from wedo_core_service.models import (
    ChallengeGroupContent, UserPriorityGroup, Coach, Challenger,
)

from api.schemas.view_models import (
    ChallengeGroupContentResponseV2, ChallengeGroupResponseV2,
)
from api.services.challenge_component import get_challenge_components_by_group


def get_percentage_completed_from_components(challenge_components):
    completed_components = sum(
        [
            1 if component.is_completed_by_user and component.challenge_component.accept_progress else 0
            for component in challenge_components
        ]
    )
    total_components = sum(
        [1 if component.challenge_component.accept_progress else 0 for component in challenge_components]
    )
    return round(float(completed_components * 100 / total_components), 2) if total_components > 0 else 0.00


def get_percentage_completed_from_subgroups(subgroups):
    total_complete_percentage = sum(
        [
            subgroup.percentage_completed if subgroup.challenge_group.accept_progress else 0
            for subgroup in subgroups
        ]
    )
    total_subgroups = sum(
        [
            1 if subgroup.challenge_group.accept_progress else 0
            for subgroup in subgroups
        ]
    )
    return round(float(total_complete_percentage / total_subgroups), 2) if total_subgroups > 0 else 0.00


def get_challenge_group_detail(
        challenge_group_content, content_object, language, is_first_group_search=False, is_subgroup_level=False
):
    challenge_group = challenge_group_content.challenge_group
    deep_challenge_subgroups = []
    challenge_components = []
    if (is_first_group_search and challenge_group.type not in ['CARD', 'CARD_LARGER_IMAGE']) or is_subgroup_level:
        query_filter = Q(
            challenge_group__parent=challenge_group) & Q(
            challenge_group__is_active=True)

        if isinstance(content_object, Coach):
            query_filter &= (
                Q(challenge_group__is_visible_from_position__isnull=True) |
                Q(challenge_group__is_visible_from_position__order__lte=content_object.position.order)
            ) & Q(challenge_group__visible_by__in=['ALL', 'COACH'])
        if isinstance(content_object, Challenger):
            query_filter &= Q(challenge_group__visible_by__in=['ALL', 'CHALLENGER'])

        language_sub_challenge_groups_content = ChallengeGroupContent.objects.select_related(
            'challenge_group'
        ).filter(
            query_filter & Q(language=language)
        )
        default_sub_challenge_groups_content = ChallengeGroupContent.objects.select_related(
            'challenge_group'
        ).filter(
            query_filter & Q(default=True)
        ).exclude(
            Q(challenge_group__id__in=language_sub_challenge_groups_content.values_list('challenge_group__id'))
        )
        challenge_sub_groups_content = list(
            chain(language_sub_challenge_groups_content, default_sub_challenge_groups_content)
        )
        if challenge_sub_groups_content:
            challenge_sub_groups_content = sorted(challenge_sub_groups_content, key=lambda x: x.challenge_group.order)

        for challenge_sub_group_content in challenge_sub_groups_content:
            deep_challenge_subgroups.append(
                get_challenge_group_detail(
                    challenge_group_content=challenge_sub_group_content,
                    content_object=content_object,
                    language=language,
                    is_first_group_search=False,
                    is_subgroup_level=is_subgroup_level
                )
            )
        deep_component = is_first_group_search or challenge_group.type in [
            'GROUPER', 'GROUPER_TAP', 'GROUPER_SELECTOR', 'CAROUSEL', 'CARD_WITH_SINGLE_SELECTOR'
        ]
        challenge_components = get_challenge_components_by_group(
            challenge_group=challenge_group,
            content_object=content_object,
            language=language,
            deep_component=deep_component
        )

    is_user_priority_group = False
    if challenge_group.type in ['CARD_WITH_SINGLE_SELECTOR']:
        is_user_priority_group = UserPriorityGroup.objects.filter(
            user=content_object.user_profile.user, challenge_group=challenge_group, active=True
        ).exists()

    percentage_completed = 0.00
    if challenge_group.accept_progress:
        if challenge_components and challenge_group.type in [
            'CARD', 'CARD_LARGER_IMAGE', 'CARD_STEPPER', 'CARD_WITH_PROGRESS_BAR'
        ]:
            percentage_completed = get_percentage_completed_from_components(challenge_components)
        if not challenge_components and deep_challenge_subgroups and challenge_group.type in [
            'CARD_WITH_PROGRESS_BAR', 'CARD_WITH_ACTION_BUTTON'
        ]:
            percentage_completed = get_percentage_completed_from_subgroups(subgroups=deep_challenge_subgroups)

    components_count = len(challenge_components) + sum(
        [subgroup.components_count for subgroup in deep_challenge_subgroups]
    )

    description = challenge_group_content.description
    if challenge_group.show_component_counter and components_count > 0:
        if components_count > 1:
            description = f'{components_count} {challenge_group_content.counter_plural_text}'
        else:
            description = f'{components_count} {challenge_group_content.counter_singular_text}'

    if challenge_group.type == 'GROUPER_SELECTOR':
        any_priority = False
        for subgroup in deep_challenge_subgroups:
            if subgroup.challenge_group.type == 'CARD_WITH_SINGLE_SELECTOR' and subgroup.is_user_priority_group:
                any_priority = True
                break
        if not any_priority:
            for subgroup in deep_challenge_subgroups:
                if subgroup.challenge_group.type == 'CARD_WITH_SINGLE_SELECTOR':
                    subgroup.is_user_priority_group = True
                    break

    return ChallengeGroupContentResponseV2(
        challenge_group=ChallengeGroupResponseV2.from_orm(challenge_group),
        default=challenge_group_content.default,
        title=challenge_group_content.title,
        description=description,
        percentage_completed=percentage_completed,
        is_user_priority_group=is_user_priority_group,
        sub_groups=deep_challenge_subgroups,
        challenge_components=challenge_components,
        action_text=challenge_group_content.action_text,
        components_count=components_count
    )
