from itertools import chain

from django.db.models import Q
from wedo_core_service.models import ChallengeChatContent, Coach, Challenger


def get_challenge_chats(challenge, content_object, language):
    query_filter = Q(
        challenge_chat__challenge=challenge) & Q(
        challenge_chat__is_active=True)

    if isinstance(content_object, Coach):
        query_filter &= (
            Q(challenge_chat__is_visible_from_position__isnull=True) |
            Q(challenge_chat__is_visible_from_position__order__lte=content_object.position.order)
        ) & Q(challenge_chat__visible_by__in=['ALL', 'COACH'])
    if isinstance(content_object, Challenger):
        query_filter &= Q(challenge_chat__visible_by__in=['ALL', 'CHALLENGER'])

    language_chat = ChallengeChatContent.objects.filter(
        query_filter & Q(language=language)
    )
    default_chat = ChallengeChatContent.objects.filter(
        query_filter & Q(default=True)
    ).exclude(
        Q(challenge_chat__id__in=language_chat.values_list('challenge_chat__id'))
    )
    return list(chain(language_chat, default_chat))
