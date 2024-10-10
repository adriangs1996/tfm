import datetime
from itertools import chain
from api.services.custom_translate import get_translate_text as _
from django.db.models import Value, Count, Q, F
from wedo_core_service.models import (
    ChallengeConfig, Language, MainChallengeConfig, Challenge, ChallengerVotingRoundPanel, ChallengeVotingRoundJury,
    ChallengeRoundVotingResult, ChallengeGroupContent, MainChallenge, CoachChallenge, ChallengerInvitationChallenge,
    Coach, Challenger
)
from api.schemas.view_models import (
    PendingActionResponseV2, BuyOtherChallengeResponseV2,
)
from api.services.challenge_group import get_challenge_group_detail
from api.services.notifications import send_notification


def get_active_challenges(challenge_ids, language: Language, active_type=None):
    query_filters = Q(challenge__id__in=challenge_ids) & Q(challenge__active=True)
    if active_type:
        current_month = datetime.datetime.utcnow().month
        if active_type == 'NEXT':
            query_filters &= Q(challenge__start__month__gt=current_month)
        if active_type == 'CURRENT':
            query_filters &= Q(challenge__start__month__lte=current_month)

    language_active_challenges = ChallengeConfig.objects.select_related(
        'challenge'
    ).filter(
        query_filters & Q(language=language)
    ).annotate(
        challengers=Count('challenge__coachchallenge__challengerchallenge'),
        type_image=Value('joined'),
        was_like_challenger=Value(False)
    )

    default_active_challenges = ChallengeConfig.objects.select_related(
        'challenge'
    ).filter(
        query_filters & Q(default=True)
    ).exclude(
        Q(challenge__id__in=language_active_challenges.values_list('challenge__id'))
    ).annotate(
        challengers=Count('challenge__coachchallenge__challengerchallenge'),
        type_image=Value('joined'),
        was_like_challenger=Value(False)
    )

    active_challenges = list(chain(language_active_challenges, default_active_challenges))
    if active_challenges:
        active_challenges = sorted(
            active_challenges,
            key=lambda x: x.challenge.start
        )

    return active_challenges


def get_past_challenges(challenge_ids, language: Language):
    query_filters = Q(
        challenge__challengevotinground__is_active__in=['C']) & Q(
        challenge__challengevotinground__is_final=True) & Q(
        challenge__id__in=challenge_ids) & Q(challenge__active=False)

    language_past_challenges = ChallengeConfig.objects.select_related(
        'challenge'
    ).filter(
        query_filters & Q(language=language)
    ).annotate(
        challengers=Count('challenge__coachchallenge__challengerchallenge'),
        type_image=Value('previous'),
        was_like_challenger=Value(False)
    )

    default_past_challenges = ChallengeConfig.objects.select_related(
        'challenge'
    ).filter(
        query_filters & Q(default=True)
    ).exclude(
        Q(challenge__id__in=language_past_challenges.values_list('challenge__id'))
    ).annotate(
        challengers=Count('challenge__coachchallenge__challengerchallenge'),
        type_image=Value('previous'),
        was_like_challenger=Value(False)
    )

    past_challenges = list(chain(language_past_challenges, default_past_challenges))
    if past_challenges:
        past_challenges = sorted(
            past_challenges,
            key=lambda x: x.challenge.start
        )

    return past_challenges


def get_next_challenge(main_challenge_ids, language: Language, user_type, main_challenge_id=None):
    query_filters = Q(main_challenge__challenge__active=True)

    if user_type == 'COACH':
        query_filters &= Q(main_challenge__challenge__is_active_register_coach=True)
    if user_type == 'CHALLENGER':
        query_filters &= Q(main_challenge__challenge__is_active_register_challenger=True)
    if main_challenge_id:
        query_filters &= Q(main_challenge__id=main_challenge_id)

    language_next_challenges = MainChallengeConfig.objects.select_related(
        'main_challenge'
    ).filter(
        query_filters & Q(language=language)
    ).exclude(
        Q(main_challenge__id__in=main_challenge_ids)
    ).annotate(
        type_image=Value('available')
    ).distinct()

    default_next_challenges = MainChallengeConfig.objects.select_related(
        'main_challenge'
    ).filter(
        query_filters & Q(default=True)
    ).exclude(
        Q(main_challenge__id__in=main_challenge_ids) |
        Q(main_challenge__id__in=language_next_challenges.values_list('main_challenge__id'))
    ).annotate(
        type_image=Value('available')
    ).distinct()

    next_challenges = list(chain(language_next_challenges, default_next_challenges))
    if next_challenges:
        next_challenges = sorted(next_challenges, key=lambda x: x.main_challenge.start, reverse=True)
    return next_challenges


def get_pending_actions(coach_challenge_ids, challenge_ids, language: Language):
    pending_actions = []
    active_panels_where_coach_is_jury = ChallengeVotingRoundJury.objects.select_related(
        'challenge_voting_round_panel__challenge_voting_round'
    ).annotate(
        is_final=F('challenge_voting_round_panel__challenge_voting_round__is_final')
    ).filter(
        jury__in=coach_challenge_ids,
        challenge_voting_round_panel__is_active="I"
    )
    for active_panel in active_panels_where_coach_is_jury:
        pending_vote = ChallengerVotingRoundPanel.objects.filter(
            challenge_voting_round_panel=active_panel.challenge_voting_round_panel
        ).exclude(
            challengeroundvotingresult__in=ChallengeRoundVotingResult.objects.filter(
                challenger_voting_round_panel__challenge_voting_round_panel=active_panel.challenge_voting_round_panel,
                challenger_voting_round_jury=active_panel
            )
        ).count()

        if pending_vote > 0:
            pending_actions.append(
                PendingActionResponseV2(
                    action_type="pending_vote",
                    pending_vote=pending_vote,
                    voting_round=active_panel,
                    challenge=active_panel.jury.challenge,
                    region_name=ChallengeConfig.objects.filter(
                        Q(challenge=active_panel.jury.challenge) &
                        (Q(language=language) | Q(default=True))
                    ).order_by('default').first().region_name
                )
            )

    challenges_joined_with_active_initial_upload_files = Challenge.objects.filter(
        Q(challengevotinground__is_active='N') &
        Q(challengevotinground__order=1) &
        Q(id__in=challenge_ids) &
        Q(coachchallenge__id__in=coach_challenge_ids) &
        Q(is_active_upload_files=True) &
        Q(coachchallenge__challengerchallenge__id__isnull=False) & (
            Q(coachchallenge__challengerchallenge__initial_video__isnull=True) |
            Q(coachchallenge__challengerchallenge__initial_side_photo__isnull=True) |
            Q(coachchallenge__challengerchallenge__initial_front_photo__isnull=True) |
            Q(coachchallenge__challengerchallenge__initial_back_photo__isnull=True) |
            Q(coachchallenge__challengerchallenge__initial_video='') |
            Q(coachchallenge__challengerchallenge__initial_side_photo='') |
            Q(coachchallenge__challengerchallenge__initial_front_photo='') |
            Q(coachchallenge__challengerchallenge__initial_back_photo='')
        )
    ).distinct()

    for challenge_joined_with_active_initial_upload_files in challenges_joined_with_active_initial_upload_files:
        pending_actions.append(
            PendingActionResponseV2(
                action_type="upload_initial_file",
                pending_vote=None,
                voting_round=None,
                challenge=challenge_joined_with_active_initial_upload_files,
                region_name=ChallengeConfig.objects.filter(
                    Q(challenge=challenge_joined_with_active_initial_upload_files) &
                    (Q(language=language) | Q(default=True))
                ).order_by('default').first().region_name
            )
        )

    challenges_joined_with_active_final_upload_files = Challenge.objects.filter(
        Q(challengevotinground__is_active='N') &
        Q(challengevotinground__order=1) &
        Q(id__in=challenge_ids) &
        Q(coachchallenge__id__in=coach_challenge_ids) &
        Q(is_active_upload_final_files=True) &
        Q(coachchallenge__challengerchallenge__id__isnull=False) & (
                Q(coachchallenge__challengerchallenge__final_video__isnull=True) |
                Q(coachchallenge__challengerchallenge__final_side_photo__isnull=True) |
                Q(coachchallenge__challengerchallenge__final_front_photo__isnull=True) |
                Q(coachchallenge__challengerchallenge__final_back_photo__isnull=True) |
                Q(coachchallenge__challengerchallenge__final_video='') |
                Q(coachchallenge__challengerchallenge__final_side_photo='') |
                Q(coachchallenge__challengerchallenge__final_front_photo='') |
                Q(coachchallenge__challengerchallenge__final_back_photo='')
        )
    ).exclude(
        id__in=challenges_joined_with_active_initial_upload_files.values_list('id')
    ).distinct()

    for challenge_joined_with_active_final_upload_files in challenges_joined_with_active_final_upload_files:
        pending_actions.append(
            PendingActionResponseV2(
                action_type="upload_final_file",
                pending_vote=None,
                voting_round=None,
                challenge=challenge_joined_with_active_final_upload_files,
                region_name=ChallengeConfig.objects.filter(
                    Q(challenge=challenge_joined_with_active_final_upload_files) &
                    (Q(language=language) | Q(default=True))
                ).order_by('default').first().region_name
            )
        )

    return pending_actions


def get_main_challenge_groups(challenge, content_object, language):
    query_filters = Q(
        challenge_group__challenge=challenge) & Q(
        challenge_group__is_active=True)

    if isinstance(content_object, Coach):
        query_filters &= (
                Q(challenge_group__is_visible_from_position__isnull=True) |
                Q(challenge_group__is_visible_from_position__order__lte=content_object.position.order)
        ) & Q(challenge_group__visible_by__in=['ALL', 'COACH'])
    if isinstance(content_object, Challenger):
        query_filters &= Q(challenge_group__visible_by__in=['ALL', 'CHALLENGER'])

    language_challenge_groups_content = ChallengeGroupContent.objects.select_related(
        'challenge_group'
    ).filter(
        query_filters & Q(language=language)
    )

    default_challenge_groups_content = ChallengeGroupContent.objects.select_related(
        'challenge_group'
    ).filter(
        query_filters & Q(default=True)
    ).exclude(
        Q(challenge_group__id__in=language_challenge_groups_content.values_list('challenge_group__id'))
    )

    challenge_groups_content = list(chain(language_challenge_groups_content, default_challenge_groups_content))
    if challenge_groups_content:
        challenge_groups_content = sorted(challenge_groups_content, key=lambda x: x.challenge_group.order)

    groups_list_response = []
    for challenge_group_content in challenge_groups_content:
        groups_list_response.append(
            get_challenge_group_detail(
                challenge_group_content=challenge_group_content,
                content_object=content_object,
                language=language,
                is_first_group_search=True,
                is_subgroup_level=False
            )
        )

    return groups_list_response


def can_show_buy_button(content_object) -> BuyOtherChallengeResponseV2:
    if isinstance(content_object, Coach):
        main_challenge_with_active_register = MainChallenge.objects.filter(
            Q(challenge__is_active_register_coach=True) &
            Q(challenge__active=True)
        ).order_by('-start').distinct().first()
        if main_challenge_with_active_register:
            challenges = main_challenge_with_active_register.challenge_set.all()
            coach_challenges = CoachChallenge.objects.filter(
                challenge__id__in=challenges.values_list('id'), coach=content_object
            )
            if coach_challenges.count() > 0 and coach_challenges.count() < challenges.count():
                return BuyOtherChallengeResponseV2(
                    main_challenge_id=main_challenge_with_active_register.id,
                    start_main_challenge=str(main_challenge_with_active_register.start),
                    show_buy_button=True
                )

    return BuyOtherChallengeResponseV2(
        main_challenge_id=None,
        start_main_challenge=None,
        show_buy_button=False
    )


def get_active_invitations(content_object, language: Language):
    if isinstance(content_object, Coach):
        return []

    invalid_invitations = ChallengerInvitationChallenge.objects.filter(
        (Q(challenger=content_object) | Q(email=content_object.user_profile.user.email)) &
        Q(coach_challenge__challenge__is_active_register_challenger=True) &
        Q(status='P') &
        ~Q(coach_challenge__challenge__nickname=content_object.user_profile.country.default_challenge_nickname)
    )

    for invitation in invalid_invitations:
        invitation.is_active = False
        invitation.status = 'R'
        invitation.save()

        challenge_month = invitation.coach_challenge.challenge.start.month

        token = invitation.coach_challenge.coach.user_profile.firebase_token
        challenger_name = content_object.user_profile.user.first_name
        if token and challenger_name:
            nemo = invitation.coach_challenge.coach.user_profile.get_content_language.nemo
            challenger_challenge_nickname = content_object.user_profile.country.default_challenge_nickname
            challenge_to_invite = Challenge.objects.filter(start__month=challenge_month,
                                                           nickname=challenger_challenge_nickname).first()
            title = _(text="title_rejected_other_region_invitation_coach_message", nemo=nemo)
            body = _(text="body_rejected_other_region_invitation_coach_message", nemo=nemo).format(name=challenger_name,
                                                                                                   challenge_name=challenge_to_invite.name)
            send_notification(registration_token=token,
                              title=title,
                              body=body,
                              object_id=str(invitation.id),
                              context='INVITATION_REJECTED_OTHER_REGION')

    invitation_ids = ChallengerInvitationChallenge.objects.filter(
        (Q(challenger=content_object) | Q(email=content_object.user_profile.user.email)) &
        Q(coach_challenge__challenge__is_active_register_challenger=True) &
        Q(status='P') &
        Q(coach_challenge__challenge__nickname=content_object.user_profile.country.default_challenge_nickname)
    ).values_list('id')

    language_active_invitations = ChallengeConfig.objects.select_related(
        'challenge'
    ).filter(
        Q(challenge__coachchallenge__challengerinvitationchallenge__in=invitation_ids),
        Q(language=language)
    ).annotate(
        challengers=Count('challenge__coachchallenge__challengerchallenge'),
        type_image=Value('available'),
        invitation_id=F('challenge__coachchallenge__challengerinvitationchallenge__id'),
        coach_name=F('challenge__coachchallenge__coach__profile__user__first_name')
    ).order_by('-id')
    default_active_invitations = ChallengeConfig.objects.select_related(
        'challenge'
    ).filter(
        Q(challenge__coachchallenge__challengerinvitationchallenge__in=invitation_ids),
        Q(default=True)
    ).exclude(
        Q(challenge__id__in=language_active_invitations.values_list('challenge__id'))
    ).annotate(
        challengers=Count('challenge__coachchallenge__challengerchallenge'),
        type_image=Value('available'),
        invitation_id=F('challenge__coachchallenge__challengerinvitationchallenge__id'),
        coach_name=F('challenge__coachchallenge__coach__profile__user__first_name')
    ).order_by('-id')

    return list(chain(language_active_invitations, default_active_invitations))
