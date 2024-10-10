import datetime
from itertools import chain

from django.db.models import Q
from wedo_core_service.models import (
    Coach, Challenger, HighlightContent, HighlightComponent, UserViewedHighlightComponent,
)


def get_all_highlights(content_object, language):
    now = datetime.datetime.utcnow()
    user = content_object.user_profile.user
    query = Q(highlight__is_active=True)

    if isinstance(content_object, Coach):
        position = content_object.position
        query &= Q(highlight__visible_by__in=['ALL', 'COACH'])
        query &= (
            Q(highlight__is_visible_from_position__order__lte=position.order) |
            Q(highlight__is_visible_from_position__isnull=True)
        )

    if isinstance(content_object, Challenger):
        query &= Q(highlight__visible_by__in=['ALL', 'CHALLENGER'])
        query &= Q(highlight__is_visible_from_position__isnull=True)

    results1 = HighlightContent.objects.filter(query & Q(language=language))
    highlight_ids = results1.values_list('highlight_id')
    results2 = HighlightContent.objects.filter(query & Q(default=True)).exclude(highlight_id__in=highlight_ids)
    results = list(chain(results1, results2))
    if results:
        results = sorted(results, key=lambda x: x.highlight.order)

    highlights = []
    for highlight_content in results:
        component_query = Q(highlight=highlight_content.highlight) & \
                          Q(start__lte=now) & \
                          Q(end__gt=now) & \
                          Q(is_active=True)
        if isinstance(content_object, Coach):
            position = content_object.position
            component_query &= Q(visible_by__in=['ALL', 'COACH'])
            component_query &= (
                Q(is_visible_from_position__order__lte=position.order) |
                Q(is_visible_from_position__isnull=True)
            )
        if isinstance(content_object, Challenger):
            component_query &= Q(visible_by__in=['ALL', 'CHALLENGER'])
            component_query &= Q(is_visible_from_position__isnull=True)
        components = HighlightComponent.objects.filter(component_query)
        total_components = components.count()
        if total_components > 0:
            viewed = UserViewedHighlightComponent.objects.filter(
                highlight_component__in=components, viewed=True, user=user
            ).count()
            highlight_content.has_new_content = not (total_components == viewed)
            highlights.append(highlight_content)

    return highlights
