from itertools import chain
from typing import List

from django.db.models import Q, FilteredRelation, F
from wedo_core_service.models import (
    ChallengeComponent, ChallengeCalendarEventContent, ChallengeVideoContent, ChallengeResourceContent,
    ChallengeImageRecipeContent, ChallengeVideoRecipeContent, ChallengeWorkoutVideoContent, ChallengeImageContent,
    ChallengeCourseVideoContent, ChallengeCourseResourceContent, Coach, Challenger, ChallengeLinkContent,
)

from api.schemas.view_models import (
    FullChallengeCalendarResponseV2, FullComponentResponseV2, ChallengeVideoContentResponseV2,
    ChallengeResourceContentResponseV2, ChallengeImageRecipeContentResponseV2, ChallengeVideoRecipeContentResponseV2,
    ChallengeWorkoutVideoContentResponseV2, ChallengeComponentResponseV2, ChallengeImageContentResponseV2,
    ChallengeCourseVideoContentResponseV2, ChallengeCourseResourceContentResponseV2,
)


def get_full_challenge_calendar(challenge_calendar, content_object, language) -> FullChallengeCalendarResponseV2:
    query_filter = Q(challenge_calendar_event__challenge_calendar=challenge_calendar)
    if isinstance(content_object, Coach):
        query_filter &= (
            Q(challenge_calendar_event__is_visible_from_position__order__lte=content_object.position.order) |
            Q(challenge_calendar_event__is_visible_from_position__isnull=True)
        ) & Q(challenge_calendar_event__visible_by__in=['ALL', 'COACH'])
    if isinstance(content_object, Challenger):
        query_filter &= Q(challenge_calendar_event__visible_by__in=['ALL', 'CHALLENGER'])

    language_events = ChallengeCalendarEventContent.objects.select_related(
        'challenge_calendar_event'
    ).filter(
        query_filter & Q(language=language)
    )
    default_events = ChallengeCalendarEventContent.objects.select_related(
        'challenge_calendar_event'
    ).filter(
        query_filter & Q(default=True)
    ).exclude(challenge_calendar_event__id__in=language_events.values_list('challenge_calendar_event__id'))

    challenge_events = list(chain(language_events, default_events))
    if challenge_events:
        challenge_events = sorted(challenge_events, key=lambda x: x.challenge_calendar_event.date)

    return FullChallengeCalendarResponseV2(
        show_list=challenge_calendar.show_list,
        events=challenge_events
    )


def get_full_challenge_video(challenge_video, language):
    return ChallengeVideoContent.objects.select_related(
        'challenge_video'
    ).filter(
        Q(challenge_video=challenge_video) &
        (Q(language=language) | Q(default=True))
    ).order_by('default').first()


def get_full_challenge_resource(challenge_resource, language):
    return ChallengeResourceContent.objects.select_related(
        'challenge_resource'
    ).filter(
        Q(challenge_resource=challenge_resource) &
        (Q(language=language) | Q(default=True))
    ).order_by('default').first()


def get_full_challenge_link(challenge_link, language):
    return ChallengeLinkContent.objects.select_related(
        'challenge_link'
    ).filter(
        Q(challenge_link=challenge_link) &
        (Q(language=language) | Q(default=True))
    ).order_by('default').first()


def get_full_challenge_recipe_image(challenge_image_recipe, language):
    return ChallengeImageRecipeContent.objects.select_related(
        'challenge_image_recipe'
    ).filter(
        Q(challenge_image_recipe=challenge_image_recipe) &
        (Q(language=language) | Q(default=True))
    ).order_by('default').first()


def get_full_challenge_image(challenge_image, language):
    return ChallengeImageContent.objects.select_related(
        'challenge_image'
    ).filter(
        Q(challenge_image=challenge_image) &
        (Q(language=language) | Q(default=True))
    ).order_by('default').first()


def get_full_challenge_recipe_video(challenge_video_recipe, language):
    return ChallengeVideoRecipeContent.objects.select_related(
        'challenge_video_recipe'
    ).filter(
        Q(challenge_video_recipe=challenge_video_recipe) &
        (Q(language=language) | Q(default=True))
    ).order_by('default').first()


def get_full_challenge_workout_video(challenge_workout_video, language):
    return ChallengeWorkoutVideoContent.objects.select_related(
        'challenge_workout_video'
    ).filter(
        Q(challenge_workout_video=challenge_workout_video) &
        (Q(language=language) | Q(default=True))
    ).order_by('default').first()


def get_full_challenge_course_video(challenge_course_video, language):
    return ChallengeCourseVideoContent.objects.select_related(
        'challenge_course_video'
    ).filter(
        Q(challenge_course_video=challenge_course_video) &
        (Q(language=language) | Q(default=True))
    ).order_by('default').first()


def get_full_challenge_course_resource(challenge_course_resource, language):
    return ChallengeCourseResourceContent.objects.select_related(
        'challenge_course_resource'
    ).filter(
        Q(challenge_course_resource=challenge_course_resource) &
        (Q(language=language) | Q(default=True))
    ).order_by('default').first()


def get_challenge_components_by_group(
        challenge_group, content_object, language, deep_component=True
) -> List[FullComponentResponseV2]:
    query_filter = Q(challenge_group=challenge_group) & Q(is_active=True)

    if isinstance(content_object, Coach):
        query_filter &= (
                            Q(is_visible_from_position__isnull=True) |
                            Q(is_visible_from_position__order__lte=content_object.position.order)
                        ) & Q(challenge_group__visible_by__in=['ALL', 'COACH'])
    if isinstance(content_object, Challenger):
        query_filter &= Q(challenge_group__visible_by__in=['ALL', 'CHALLENGER'])

    challenge_components = ChallengeComponent.objects.prefetch_related('usercompletedcomponent_set').filter(
        query_filter
    ).annotate(
        user_completed_component=FilteredRelation(
            'usercompletedcomponent',
            condition=Q(
                usercompletedcomponent__user=content_object.user_profile.user,
                usercompletedcomponent__completed=True
            )
        )
    ).annotate(
        completed=F('user_completed_component')
    ).order_by('order')

    full_challenge_components = []
    for challenge_component in challenge_components:
        is_completed_by_user = True if challenge_component.completed else False
        if not deep_component:
            full_challenge_components.append(
                FullComponentResponseV2(
                    challenge_component=ChallengeComponentResponseV2(
                        id=challenge_component.id,
                        accept_progress=challenge_component.accept_progress
                    ),
                    is_completed_by_user=is_completed_by_user
                )
            )
        elif challenge_component.content_type.model.upper() == 'CHALLENGECALENDAR':
            full_challenge_components.append(
                FullComponentResponseV2(
                    challenge_component=ChallengeComponentResponseV2(
                        id=challenge_component.id,
                        accept_progress=challenge_component.accept_progress
                    ),
                    challenge_calendar=get_full_challenge_calendar(
                        challenge_calendar=challenge_component.content_object,
                        content_object=content_object,
                        language=language
                    ),
                    is_completed_by_user=is_completed_by_user
                )
            )
        elif challenge_component.content_type.model.upper() == 'CHALLENGEVIDEO':
            challenge_video = get_full_challenge_video(
                challenge_video=challenge_component.content_object,
                language=language
            )
            full_challenge_components.append(
                FullComponentResponseV2(
                    challenge_component=ChallengeComponentResponseV2(
                        id=challenge_component.id,
                        accept_progress=challenge_component.accept_progress
                    ),
                    search_text=challenge_video.title,
                    challenge_video=challenge_video,
                    is_completed_by_user=is_completed_by_user
                )
            )

        elif challenge_component.content_type.model.upper() == 'CHALLENGERESOURCE':
            challenge_resource = get_full_challenge_resource(
                challenge_resource=challenge_component.content_object,
                language=language
            )
            full_challenge_components.append(
                FullComponentResponseV2(
                    challenge_component=ChallengeComponentResponseV2(
                        id=challenge_component.id,
                        accept_progress=challenge_component.accept_progress
                    ),
                    search_text=challenge_resource.title,
                    challenge_resource=challenge_resource,
                    is_completed_by_user=is_completed_by_user
                )
            )
        elif challenge_component.content_type.model.upper() == 'CHALLENGELINK':
            challenge_link = get_full_challenge_link(
                challenge_link=challenge_component.content_object,
                language=language
            )
            full_challenge_components.append(
                FullComponentResponseV2(
                    challenge_component=ChallengeComponentResponseV2(
                        id=challenge_component.id,
                        accept_progress=challenge_component.accept_progress
                    ),
                    search_text=challenge_link.title,
                    challenge_link=challenge_link,
                    is_completed_by_user=is_completed_by_user
                )
            )

        elif challenge_component.content_type.model.upper() == 'CHALLENGEIMAGERECIPE':
            challenge_image_recipe = get_full_challenge_recipe_image(
                challenge_image_recipe=challenge_component.content_object,
                language=language
            )
            full_challenge_components.append(
                FullComponentResponseV2(
                    challenge_component=ChallengeComponentResponseV2(
                        id=challenge_component.id,
                        accept_progress=challenge_component.accept_progress
                    ),
                    search_text=challenge_image_recipe.title,
                    challenge_image_recipe=challenge_image_recipe,
                    is_completed_by_user=is_completed_by_user
                )
            )

        elif challenge_component.content_type.model.upper() == 'CHALLENGEVIDEORECIPE':
            challenge_video_recipe = get_full_challenge_recipe_video(
                challenge_video_recipe=challenge_component.content_object,
                language=language
            )
            full_challenge_components.append(
                FullComponentResponseV2(
                    challenge_component=ChallengeComponentResponseV2(
                        id=challenge_component.id,
                        accept_progress=challenge_component.accept_progress
                    ),
                    search_text=challenge_video_recipe.title,
                    challenge_video_recipe=challenge_video_recipe,
                    is_completed_by_user=is_completed_by_user
                )
            )

        elif challenge_component.content_type.model.upper() == 'CHALLENGEWORKOUTVIDEO':
            challenge_workout_video = get_full_challenge_workout_video(
                challenge_workout_video=challenge_component.content_object,
                language=language
            )
            full_challenge_components.append(
                FullComponentResponseV2(
                    challenge_component=ChallengeComponentResponseV2(
                        id=challenge_component.id,
                        accept_progress=challenge_component.accept_progress
                    ),
                    search_text=challenge_workout_video.title,
                    challenge_workout_video=challenge_workout_video,
                    is_completed_by_user=is_completed_by_user
                )
            )

        elif challenge_component.content_type.model.upper() == 'CHALLENGEIMAGE':
            challenge_image = get_full_challenge_image(
                challenge_image=challenge_component.content_object,
                language=language
            )
            full_challenge_components.append(
                FullComponentResponseV2(
                    challenge_component=ChallengeComponentResponseV2(
                        id=challenge_component.id,
                        accept_progress=challenge_component.accept_progress
                    ),
                    search_text=challenge_image.title,
                    challenge_image=challenge_image,
                    is_completed_by_user=is_completed_by_user
                )
            )

        elif challenge_component.content_type.model.upper() == 'CHALLENGECOURSEVIDEO':
            challenge_course_video = get_full_challenge_course_video(
                challenge_course_video=challenge_component.content_object,
                language=language
            )
            full_challenge_components.append(
                FullComponentResponseV2(
                    challenge_component=ChallengeComponentResponseV2(
                        id=challenge_component.id,
                        accept_progress=challenge_component.accept_progress
                    ),
                    search_text=challenge_course_video.title,
                    challenge_course_video=challenge_course_video,
                    is_completed_by_user=is_completed_by_user
                )
            )

        elif challenge_component.content_type.model.upper() == 'CHALLENGECOURSERESOURCE':
            challenge_course_resource = get_full_challenge_course_resource(
                challenge_course_resource=challenge_component.content_object,
                language=language
            )
            full_challenge_components.append(
                FullComponentResponseV2(
                    challenge_component=ChallengeComponentResponseV2(
                        id=challenge_component.id,
                        accept_progress=challenge_component.accept_progress
                    ),
                    search_text=challenge_course_resource.title,
                    challenge_course_resource=challenge_course_resource,
                    is_completed_by_user=is_completed_by_user
                )
            )

    return full_challenge_components
