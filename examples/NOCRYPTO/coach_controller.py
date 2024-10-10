import datetime
from itertools import chain
from typing import List

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, Subquery, Count, Value, F
from ninja import Form, UploadedFile
from ninja_extra import ControllerBase, api_controller, route
from wedo_core_service.models import (
    Coach, CoachChallenge, Challenge, ChallengeVotingRoundJury, ChallengerVotingRoundPanel, ChallengeRoundVotingResult,
    ChallengeConfig, ChallengerChallenge, Challenger, ChallengerInvitationChallenge, UserProfile, EventTrack,
    ChallengerPromotedCoach, CoachPayment, AdminUser,
)
from wedo_core_service.repository.challenger import get_challenger_by_email
from wedo_core_service.repository.coach import (
    get_coach_by_id_herbalife,
    get_if_coach_active_in_future_challenges,
)
from wedo_core_service.repository.coach_black_list import is_id_herbalife_in_black_list
from wedo_core_service.repository.position import get_minor_jury_position
from wedo_core_service.services.auth import ProfileCoachJWTAuth
from wedo_core_service.utils import get_default_content_language_for_challenge

from api.schemas.view_models import (
    ResponseError, DetailError, CoachRegisterInput, CoachResponse, DashboardResponse, PendingActionResponse,
    RegisterCoachChallengeInput, CoachChallengeResponse, InvitationChallengerInput, InvitationChallengerResponse,
    ChallengerProfileResponse, VerifyChallengerInput, ChallengerChallengeResponse, UploadChallengerMultimediaInput,
    GeneralChallengersChallengeResponse, PartnerResponse, PartnerRegisterInput, PromotedChallengerInput,
    PromotedChallengerResponse, VerifyChallengerToPromoteInput, InvitationChallengerNewInput, ProfileSchema,
    ChallengeInvitationPending, CountrySchema,
)
from api.services.coach import verify_is_coach, verify_active_coach
from api.services.collage_image import create_challenger_collage
from api.services.custom_translate import get_translate_text as _
from api.services.email import send_challenger_invitation_email
from api.services.notifications import send_notification

get = route.get
post = route.post


@api_controller("coach", tags=["Coach"])
class CoachController(ControllerBase):
    """
    Group functionalities to coach model
    """

    @post(
        path="register_coach_info",
        operation_id="register_coach_info",
        response={200: CoachResponse, 409: ResponseError},
        auth=ProfileCoachJWTAuth(),
    )
    def register_coach_info(self, payload: CoachRegisterInput):
        user_profile = self.context.request.auth

        if user_profile.content_object:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["coach"],
                        msg=_(
                            text="coach already exist",
                            nemo=user_profile.get_content_language.nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        if not get_coach_by_id_herbalife(payload.id_herbalife) is None:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["request.id_herbalife"],
                        msg=_(
                            text="id herbalife already exist",
                            nemo=user_profile.get_content_language.nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        if is_id_herbalife_in_black_list(payload.id_herbalife):
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["coach"],
                        msg=_(
                            text="the id herbalife you entered is restricted",
                            nemo=user_profile.get_content_language.nemo,
                        ),
                    )
                ]
            )

        try:
            # create coach
            coach = Coach()
            coach.id_herbalife = payload.id_herbalife
            coach.position_id = payload.position
            coach.sponsor = payload.sponsor
            coach.asc_president = payload.asc_president
            coach.contact_medium = payload.contact_medium

            if payload.business_partner_email:

                if AdminUser.objects.filter(profile__user__email=payload.business_partner_email).exists():
                    return 409, ResponseError(
                        detail=[
                            DetailError(
                                loc=["register_coach_info"],
                                msg=_(
                                    text="email belongs to a coach with an spouse or legal partner. please try another.",
                                    nemo=user_profile.get_content_language.nemo,
                                ),
                            )
                        ],
                        description="Bad Request",
                    )

                if not payload.couple_identifier:
                    return 409, ResponseError(
                        detail=[
                            DetailError(
                                loc=["register_coach_info"],
                                msg=_(
                                    text="couple identifier is required",
                                    nemo=user_profile.get_content_language.nemo,
                                ),
                            )
                        ],
                        description="Bad Request",
                    )

                if (
                    user_profile.user.email.lower().strip()
                    == payload.business_partner_email.lower().strip()
                ):
                    return 409, ResponseError(
                        detail=[
                            DetailError(
                                loc=["register_coach_info"],
                                msg=_(
                                    text="the email address of the spouse or partner can't be the same as the one being used to register",
                                    nemo=user_profile.get_content_language.nemo,
                                ),
                            )
                        ],
                        description="Bad Request",
                    )

                if Coach.objects.filter(
                    business_partner_email=payload.business_partner_email
                ).exists():
                    return 409, ResponseError(
                        detail=[
                            DetailError(
                                loc=["register_coach_info"],
                                msg=_(
                                    text="email is associated with another coach. please try another.",
                                    nemo=user_profile.get_content_language.nemo,
                                ),
                            )
                        ],
                        description="Bad Request",
                    )

                if Coach.objects.filter(
                    profile__user__email=payload.business_partner_email,
                    business_partner_email__isnull=False,
                ).exists():
                    return 409, ResponseError(
                        detail=[
                            DetailError(
                                loc=["register_coach_info"],
                                msg=_(
                                    text="email belongs to a coach with an spouse or legal partner. please try another.",
                                    nemo=user_profile.get_content_language.nemo,
                                ),
                            )
                        ],
                        description="Bad Request",
                    )

                partner_profile = UserProfile.objects.filter(
                    user__email=payload.business_partner_email
                ).first()
                if partner_profile:
                    if CoachChallenge.objects.filter(
                        coach__profile__user__email=payload.business_partner_email
                    ).exists():
                        return 409, ResponseError(
                            detail=[
                                DetailError(
                                    loc=["register_coach_info"],
                                    msg=_(
                                        text="there is a registered active coach with that email. please try another.",
                                        nemo=user_profile.get_content_language.nemo,
                                    ),
                                )
                            ],
                            description="Bad Request",
                        )

                    if ChallengerChallenge.objects.filter(
                        challenger__profile__user__email=payload.business_partner_email
                    ).exists():
                        return 409, ResponseError(
                            detail=[
                                DetailError(
                                    loc=["register_coach_info"],
                                    msg=_(
                                        text="there is a registered challenger with that email. please try another.",
                                        nemo=user_profile.get_content_language.nemo,
                                    ),
                                )
                            ],
                            description="Bad Request",
                        )
                    Coach.objects.filter(profile=partner_profile).delete()
                    Challenger.objects.filter(profile=partner_profile).delete()
                    partner_user = partner_profile.user
                    partner_user.delete()

                coach.business_partner_email = payload.business_partner_email
                if payload.business_partner_name is not None:
                    coach.business_partner_name = payload.business_partner_name
                user = user_profile.user
                user.first_name = payload.couple_identifier
                user.save()

            coach.save()

            # update profile
            user_profile.content_object = coach
            user_profile.save()

            return coach

        except Exception as e:
            return 409, ResponseError(detail=[DetailError(loc=["coach"], msg=str(e))])

    @route.post(
        path="update_coach_info",
        operation_id="update_coach_info",
        response={200: CoachResponse, 409: ResponseError},
    )
    def update_coach_info(self, payload: CoachRegisterInput):
        coach = self.context.request.auth

        if (
            coach.user_profile is None
            or coach.user_profile.language is None
            or coach.user_profile.country is None
        ):
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["update_coach_info"],
                        msg=_(
                            text="coach profile is not complete",
                            nemo=coach.user_profile.get_content_language.nemo,
                        ),
                    )
                ]
            )

        try:
            # update coach
            if payload.id_herbalife and coach.id_herbalife != payload.id_herbalife:
                if is_id_herbalife_in_black_list(coach.id_herbalife):
                    return 409, ResponseError(
                        detail=[
                            DetailError(
                                loc=["update_coach_info"],
                                msg=_(
                                    text="your account is restricted, you can not update your id herbalife",
                                    nemo=coach.user_profile.get_content_language.nemo,
                                ),
                            )
                        ]
                    )
                if (
                    Coach.objects.filter(id_herbalife=payload.id_herbalife)
                    .exclude(id=coach.id)
                    .exists()
                ):
                    return 409, ResponseError(
                        detail=[
                            DetailError(
                                loc=["update_coach_info"],
                                msg=_(
                                    text="id herbalife already exist",
                                    nemo=coach.user_profile.get_content_language.nemo,
                                ),
                            )
                        ]
                    )
                coach.id_herbalife = payload.id_herbalife

            if (payload.business_partner_email is not None) and (payload.business_partner_email != coach.business_partner_email):

                if AdminUser.objects.filter(profile__user__email=payload.business_partner_email).exists():
                    return 409, ResponseError(
                        detail=[
                            DetailError(
                                loc=["update_coach_info"],
                                msg=_(
                                    text="email belongs to a coach with an spouse or legal partner. please try another.",
                                    nemo=coach.user_profile.get_content_language.nemo,
                                ),
                            )
                        ],
                        description="Bad Request",
                    )

                if (
                    coach.user_profile.user.email.lower().strip()
                    == payload.business_partner_email.lower().strip()
                ):
                    return 409, ResponseError(
                        detail=[
                            DetailError(
                                loc=["update_coach_info"],
                                msg=_(
                                    text="the email address of the spouse or partner can't be the same as the one being used to register",
                                    nemo=coach.user_profile.get_content_language.nemo,
                                ),
                            )
                        ],
                        description="Bad Request",
                    )

                if Coach.objects.filter(
                    business_partner_email=payload.business_partner_email
                ).exists():
                    return 409, ResponseError(
                        detail=[
                            DetailError(
                                loc=["update_coach_info"],
                                msg=_(
                                    text="email is associated with another coach. please try another.",
                                    nemo=coach.user_profile.get_content_language.nemo,
                                ),
                            )
                        ],
                        description="Bad Request",
                    )

                if Coach.objects.filter(
                    profile__user__email=payload.business_partner_email,
                    business_partner_email__isnull=False,
                ).exists():
                    return 409, ResponseError(
                        detail=[
                            DetailError(
                                loc=["update_coach_info"],
                                msg=_(
                                    text="email belongs to a coach with an spouse or legal partner. please try another.",
                                    nemo=coach.user_profile.get_content_language.nemo,
                                ),
                            )
                        ],
                        description="Bad Request",
                    )
                if Coach.objects.filter(
                    profile__user__email=payload.business_partner_email,
                ).exists():
                    return 409, ResponseError(
                        detail=[
                            DetailError(
                                loc=["update_coach_info"],
                                msg=_(
                                    text="there is a registered active coach with that email. please try another.",
                                    nemo=coach.user_profile.get_content_language.nemo,
                                ),
                            )
                        ],
                        description="Bad Request",
                    )
                partner_profile = UserProfile.objects.filter(
                    user__email=payload.business_partner_email
                ).first()
                if partner_profile:
                    if CoachChallenge.objects.filter(
                        coach__profile__user__email=payload.business_partner_email
                    ).exists():
                        return 409, ResponseError(
                            detail=[
                                DetailError(
                                    loc=["update_coach_info"],
                                    msg=_(
                                        text="there is a registered active coach with that email. please try another.",
                                        nemo=coach.user_profile.get_content_language.nemo,
                                    ),
                                )
                            ],
                            description="Bad Request",
                        )

                    if ChallengerChallenge.objects.filter(
                        challenger__profile__user__email=payload.business_partner_email
                    ).exists():
                        return 409, ResponseError(
                            detail=[
                                DetailError(
                                    loc=["update_coach_info"],
                                    msg=_(
                                        text="there is a registered challenger with that email. please try another.",
                                        nemo=coach.user_profile.get_content_language.nemo,
                                    ),
                                )
                            ],
                            description="Bad Request",
                        )
                    Coach.objects.filter(profile=partner_profile).delete()
                    Challenger.objects.filter(profile=partner_profile).delete()
                    partner_user = partner_profile.user
                    partner_user.delete()

            if payload.position:
                coach.position_id = payload.position
            if payload.sponsor:
                coach.sponsor = payload.sponsor
            if payload.asc_president:
                coach.asc_president = payload.asc_president
            if payload.business_partner_email:
                coach.business_partner_email = payload.business_partner_email
            if payload.business_partner_name:
                coach.business_partner_name = payload.business_partner_name
            if payload.contact_medium:
                coach.contact_medium = payload.contact_medium
            if payload.couple_identifier:
                user = coach.user_profile.user
                user.first_name = payload.couple_identifier
                user.save()
            coach.save()

            return coach

        except Exception:
            return 409, ResponseError(
                detail=[
                    DetailError(loc=["coach"], msg="An error occurred updating coach")
                ]
            )

    @route.get(
        path="get_dashboard_info",
        operation_id="get_dashboard_info",
        response={200: DashboardResponse, 409: ResponseError},
    )
    def get_dashboard_info(self):
        coach = self.context.request.auth
        language = coach.user_profile.get_content_language
        default_challenge_nickname = (
            coach.user_profile.country.default_challenge_nickname
        )

        EventTrack.track(
            user_id=coach.user_profile.user.id,
            event_kind="DASHBOARD_ACCESS",
            context={
                "email_used": coach.user_profile.user.email,
            },
        )

        try:
            coach_challenges = CoachChallenge.objects.filter(coach=coach)
            challenges_id = coach_challenges.values("challenge_id").distinct()
            coaches_id = coach_challenges.values("id").distinct()

            language_active_joined_challenge_as_challenger = []
            default_active_joined_challenge_as_challenger = []
            challenger_challenges_id = []
            if coach.user_profile.transform_to_coach is True:
                try:
                    promoted_challenger = ChallengerPromotedCoach.objects.get(
                        promoted_user=coach.user_profile.user, status="A"
                    )
                    challenger_challenges_id = (
                        ChallengerChallenge.objects.filter(
                            challenger=promoted_challenger.challenger
                        )
                        .values("coach__challenge_id")
                        .distinct()
                    )
                except ChallengerPromotedCoach.DoesNotExist:
                    pass

                if challenger_challenges_id:
                    language_active_joined_challenge_as_challenger = (
                        ChallengeConfig.objects.select_related("challenge")
                        .filter(
                            Q(
                                challenge__challengevotinground__is_active__in=[
                                    "N",
                                    "I",
                                ]
                            ),
                            Q(challenge__challengevotinground__is_final=True),
                            Q(challenge__id__in=Subquery(challenger_challenges_id)),
                            Q(challenge__active=True),
                            Q(language=language),
                        )
                        .annotate(
                            challengers=Count(
                                "challenge__coachchallenge__challengerchallenge"
                            ),
                            type_image=Value("joined"),
                            was_like_challenger=Value(True),
                        )
                    )
                    for (
                        language_active_joined_as_challenger
                    ) in language_active_joined_challenge_as_challenger:
                        language_active_joined_as_challenger.challengers = 0
                    default_active_joined_challenge_as_challenger = (
                        ChallengeConfig.objects.select_related("challenge")
                        .filter(
                            Q(
                                challenge__challengevotinground__is_active__in=[
                                    "N",
                                    "I",
                                ]
                            ),
                            Q(challenge__challengevotinground__is_final=True),
                            Q(challenge__id__in=Subquery(challenger_challenges_id)),
                            Q(challenge__active=True),
                            Q(default=True),
                        )
                        .exclude(
                            Q(
                                challenge__id__in=language_active_joined_challenge_as_challenger.values_list(
                                    "challenge__id"
                                )
                            )
                        )
                        .annotate(
                            challengers=Count(
                                "challenge__coachchallenge__challengerchallenge"
                            ),
                            type_image=Value("joined"),
                            was_like_challenger=Value(True),
                        )
                    )
                    for (
                        default_active_joined_as_challenger
                    ) in default_active_joined_challenge_as_challenger:
                        default_active_joined_as_challenger.challengers = 0

            # Active Joined Challenge
            language_active_joined_challenge = (
                ChallengeConfig.objects.select_related("challenge")
                .filter(
                    Q(challenge__challengevotinground__is_active__in=["N", "I"]),
                    Q(challenge__challengevotinground__is_final=True),
                    Q(challenge__id__in=Subquery(challenges_id)),
                    Q(challenge__active=True),
                    Q(language=language),
                )
                .annotate(
                    challengers=Count("challenge__coachchallenge__challengerchallenge"),
                    type_image=Value("joined"),
                    was_like_challenger=Value(False),
                )
            )
            for language_active_joined in language_active_joined_challenge:
                total_challenger = ChallengerChallenge.objects.filter(
                    coach__coach=coach,
                    coach__challenge=language_active_joined.challenge,
                ).count()
                language_active_joined.challengers = total_challenger
            default_active_joined_challenge = (
                ChallengeConfig.objects.select_related("challenge")
                .filter(
                    Q(challenge__challengevotinground__is_active__in=["N", "I"]),
                    Q(challenge__challengevotinground__is_final=True),
                    Q(challenge__id__in=Subquery(challenges_id)),
                    Q(challenge__active=True),
                    Q(default=True),
                )
                .exclude(
                    Q(
                        challenge__id__in=language_active_joined_challenge.values_list(
                            "challenge__id"
                        )
                    )
                )
                .annotate(
                    challengers=Count("challenge__coachchallenge__challengerchallenge"),
                    type_image=Value("joined"),
                    was_like_challenger=Value(False),
                )
            )
            for default_active_joined in default_active_joined_challenge:
                total_challenger = ChallengerChallenge.objects.filter(
                    coach__coach=coach,
                    coach__challenge=default_active_joined.challenge,
                ).count()
                default_active_joined.challengers = total_challenger

            active_joined_challenge = list(
                chain(
                    language_active_joined_challenge_as_challenger,
                    default_active_joined_challenge_as_challenger,
                    language_active_joined_challenge,
                    default_active_joined_challenge,
                )
            )

            # Inactive Joined Challenge
            language_inactive_joined_challenge = (
                ChallengeConfig.objects.select_related("challenge")
                .filter(
                    Q(challenge__challengevotinground__is_active__in=["C"]),
                    Q(challenge__challengevotinground__is_final=True),
                    Q(challenge__id__in=Subquery(challenges_id)),
                    Q(language=language),
                )
                .annotate(
                    challengers=Count("challenge__coachchallenge__challengerchallenge"),
                    type_image=Value("previous"),
                    was_like_challenger=Value(False),
                )
            )
            default_inactive_joined_challenge = (
                ChallengeConfig.objects.select_related("challenge")
                .filter(
                    Q(challenge__challengevotinground__is_active__in=["C"]),
                    Q(challenge__challengevotinground__is_final=True),
                    Q(challenge__id__in=Subquery(challenges_id)),
                    Q(default=True),
                )
                .exclude(
                    Q(
                        challenge__id__in=language_inactive_joined_challenge.values_list(
                            "challenge__id"
                        )
                    )
                )
                .annotate(
                    challengers=Count("challenge__coachchallenge__challengerchallenge"),
                    type_image=Value("previous"),
                    was_like_challenger=Value(False),
                )
            )
            inactive_joined_challenge = list(
                chain(
                    language_inactive_joined_challenge,
                    default_inactive_joined_challenge,
                )
            )

            # Active Challenge with Active Coach Registration
            # if coach is in black list, return empty list
            if is_id_herbalife_in_black_list(coach.id_herbalife):
                active_challenge = []
            else:
                language_active_challenge = (
                    ChallengeConfig.objects.select_related("challenge")
                    .filter(
                        Q(challenge__is_active_register_coach=True),
                        Q(challenge__active=True),
                        Q(language=language),
                    )
                    .exclude(
                        Q(challenge__id__in=Subquery(challenges_id))
                        | Q(challenge__id__in=challenger_challenges_id)
                    )
                    .annotate(
                        challengers=Count(
                            "challenge__coachchallenge__challengerchallenge"
                        ),
                        type_image=Value("available"),
                        was_like_challenger=Value(False),
                    )
                    .order_by("-challenge__created_date")
                )
                default_active_challenge = (
                    ChallengeConfig.objects.select_related("challenge")
                    .filter(
                        Q(challenge__is_active_register_coach=True),
                        Q(challenge__active=True),
                        Q(default=True),
                    )
                    .exclude(
                        Q(challenge__id__in=Subquery(challenges_id))
                        | Q(
                            challenge__id__in=language_active_challenge.values_list(
                                "challenge__id"
                            )
                        )
                        | Q(challenge__id__in=challenger_challenges_id)
                    )
                    .annotate(
                        challengers=Count(
                            "challenge__coachchallenge__challengerchallenge"
                        ),
                        type_image=Value("available"),
                        was_like_challenger=Value(False),
                    )
                    .order_by("-challenge__created_date")
                )
                active_challenge = list(
                    chain(language_active_challenge, default_active_challenge)
                )
                if active_challenge:
                    active_challenge = sorted(
                        active_challenge,
                        key=lambda x: 1
                        if x.challenge.nickname == default_challenge_nickname
                        else 2,
                    )

            pending_actions = []
            active_panels_where_coach_is_jury = (
                ChallengeVotingRoundJury.objects.select_related(
                    "challenge_voting_round_panel__challenge_voting_round"
                )
                .annotate(
                    is_final=F(
                        "challenge_voting_round_panel__challenge_voting_round__is_final"
                    )
                )
                .filter(
                    jury__in=coaches_id, challenge_voting_round_panel__is_active="I"
                )
            )
            for active_panel in active_panels_where_coach_is_jury:
                pending_vote = (
                    ChallengerVotingRoundPanel.objects.filter(
                        challenge_voting_round_panel=active_panel.challenge_voting_round_panel
                    )
                    .exclude(
                        challengeroundvotingresult__in=ChallengeRoundVotingResult.objects.filter(
                            challenger_voting_round_panel__challenge_voting_round_panel=active_panel.challenge_voting_round_panel,
                            challenger_voting_round_jury=active_panel,
                        )
                    )
                    .count()
                )

                if pending_vote > 0:
                    pending_actions.append(
                        PendingActionResponse(
                            action_type="pending_vote",
                            pending_vote=pending_vote,
                            voting_round=active_panel,
                            challenge=active_panel.jury.challenge,
                        )
                    )

            challenges_joined_with_active_upload_files = Challenge.objects.filter(
                Q(challengevotinground__is_active="N")
                & Q(challengevotinground__order=1)
                & Q(id__in=Subquery(challenges_id))
                & Q(coachchallenge__id__in=coaches_id)
                & (
                    (
                        Q(is_active_upload_files=True)
                        & Q(coachchallenge__challengerchallenge__id__isnull=False)
                        & (
                            Q(
                                coachchallenge__challengerchallenge__initial_video__isnull=True
                            )
                            | Q(
                                coachchallenge__challengerchallenge__initial_side_photo__isnull=True
                            )
                            | Q(
                                coachchallenge__challengerchallenge__initial_front_photo__isnull=True
                            )
                            | Q(
                                coachchallenge__challengerchallenge__initial_back_photo__isnull=True
                            )
                            | Q(coachchallenge__challengerchallenge__initial_video="")
                            | Q(
                                coachchallenge__challengerchallenge__initial_side_photo=""
                            )
                            | Q(
                                coachchallenge__challengerchallenge__initial_front_photo=""
                            )
                            | Q(
                                coachchallenge__challengerchallenge__initial_back_photo=""
                            )
                        )
                    )
                    | (
                        Q(is_active_upload_final_files=True)
                        & Q(coachchallenge__challengerchallenge__id__isnull=False)
                        & (
                            Q(
                                coachchallenge__challengerchallenge__final_video__isnull=True
                            )
                            | Q(
                                coachchallenge__challengerchallenge__final_side_photo__isnull=True
                            )
                            | Q(
                                coachchallenge__challengerchallenge__final_front_photo__isnull=True
                            )
                            | Q(
                                coachchallenge__challengerchallenge__final_back_photo__isnull=True
                            )
                            | Q(coachchallenge__challengerchallenge__final_video="")
                            | Q(
                                coachchallenge__challengerchallenge__final_side_photo=""
                            )
                            | Q(
                                coachchallenge__challengerchallenge__final_front_photo=""
                            )
                            | Q(
                                coachchallenge__challengerchallenge__final_back_photo=""
                            )
                        )
                    )
                )
            ).distinct()

            for (
                challenge_joined_with_pending_upload_files
            ) in challenges_joined_with_active_upload_files:
                pending_actions.append(
                    PendingActionResponse(
                        action_type="upload_file",
                        pending_vote=None,
                        voting_round=None,
                        challenge=challenge_joined_with_pending_upload_files,
                    )
                )

            return DashboardResponse(
                pending_actions=pending_actions,
                active_challenge=active_challenge,
                inactive_joined_challenge=inactive_joined_challenge,
                active_joined_challenge=active_joined_challenge,
            )

        except Exception as error:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["challenges"], msg="An error occurred getting challenges"
                    )
                ]
            )

    @route.post(
        path="register_coach_challenge",
        operation_id="register_coach_challenge",
        response={200: CoachChallengeResponse, 409: ResponseError},
    )
    def register_coach_challenge(self, payload: RegisterCoachChallengeInput):
        coach = self.context.request.auth

        try:
            # verify challenge exist, is active and is active register coach
            challenge = Challenge.objects.get(
                id=payload.challenge_id, is_active_register_coach=True, active=True
            )
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[DetailError(loc=["challenge"], msg="Challenge not exist")],
                description="Bad Request",
            )

        default_content_language = get_default_content_language_for_challenge(
            challenge=challenge, coach=coach
        )

        try:
            # verify coach_challenge not exist
            if CoachChallenge.objects.filter(coach=coach, challenge=challenge).exists():
                return 409, ResponseError(
                    detail=[
                        DetailError(
                            loc=["coach_challenge"],
                            msg="Coach Already register in this challenge",
                        )
                    ]
                )

            # create coach_challenge
            coach_challenge = CoachChallenge()
            coach_challenge.coach = coach
            coach_challenge.challenge = challenge
            coach_challenge.content_language = default_content_language
            coach_challenge.status = True

            minor_jury_position = get_minor_jury_position()
            if coach.position.order >= minor_jury_position.order:
                coach_challenge.is_jury = True

            coach_challenge.save()

            return coach_challenge

        except Exception:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["coach_challenge"],
                        msg="An error occurred while registering coach_challenge",
                    )
                ]
            )

    @route.get(
        path="is_active/{email}/{month}/{year}",
        operation_id="is_coach_active",
        response={200: bool, 409: ResponseError},
        auth=None,
    )
    def is_coach_active(self, email: str, month: int, year: int):
        try:
            if not get_if_coach_active_in_future_challenges(email, month, year):
                usa = verify_active_coach(settings.OLD_WEDO_USA_URL, email, month, year)
                if usa:
                    return True

                return (
                    False
                    if not verify_active_coach(
                        settings.OLD_WEDO_LATAM_URL, email, month, year
                    )
                    else True
                )

            return True
        except AttributeError:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["is_coach_active"],
                        msg="Email, Month and Year can't be None",
                    )
                ]
            )

    @route.get(
        path="main/{email}",
        operation_id="coach_main_account",
        response={200: str, 409: ResponseError},
        auth=None,
    )
    def coach_main_account(self, email: str):
        try:
            query = Q(profile__user__username=email) | Q(business_partner_email=email)
            if not Coach.objects.filter(query).exists():
                return 409, ResponseError(
                    detail=[DetailError(loc=["coach"], msg="Coach not exist")],
                    description="Bad Request",
                )
            coach = Coach.objects.get(query)
            return coach.user_profile.user.email
        except Exception as error:
            return 409, ResponseError(
                detail=[
                    DetailError(loc=["coach"], msg="An error occurred getting coach")
                ]
            )

    @route.get(
        path="old/is_active/{email}/{month}/{year}",
        operation_id="is_coach_active_old",
        response={200: bool, 409: ResponseError},
        auth=None,
    )
    def is_coach_active_old(self, email: str, month: int, year: int):
        # Verify if coach is active in Wedo USA
        usa = verify_active_coach(settings.OLD_WEDO_USA_URL, email, month, year)
        if usa:
            return True

        return (
            False
            if not verify_active_coach(settings.OLD_WEDO_LATAM_URL, email, month, year)
            else True
        )

    @post(
        path="was_challenger_but_has_no_active_challenge",
        operation_id="was_challenger_but_has_no_active_challenge",
        auth=None,
        response={200: List[str]},
    )
    def was_challenger_but_has_no_active_challenge(self, payload: List[str]):
        """
        From the list of emails, return the ones beloging to challengers but that
        does not have an active challenge.
        """
        emails_set = set(payload)
        challenger_emails_in_active_challenge = set(
            Challenger.in_active_challenge().values_list(
                "profile__user__email", flat=True
            )
        )
        return list(emails_set.difference(challenger_emails_in_active_challenge))

    @route.get(
        path="was_coach_by_email/{email}/",
        operation_id="was_coach_by_email",
        response={200: bool, 409: ResponseError},
        auth=None,
    )
    def was_coach_by_email(self, email: str):
        query = Q(coach__profile__user__username=email) | Q(
            coach__business_partner_email=email
        )
        if not CoachChallenge.objects.filter(query).exists():
            usa = verify_is_coach(settings.OLD_WEDO_USA_URL, email)
            if usa:
                return True

            return (
                False
                if not verify_is_coach(settings.OLD_WEDO_LATAM_URL, email)
                else True
            )

        return True

    @route.get(
        path="old/was_coach_by_email/{email}/",
        operation_id="was_coach_by_email_old",
        response={200: bool, 409: ResponseError},
        auth=None,
    )
    def was_coach_by_email_old(self, email: str):
        # Verify if coach exists in Wedo USA
        usa = verify_is_coach(settings.OLD_WEDO_USA_URL, email)
        if usa:
            return True

        return (
            False if not verify_is_coach(settings.OLD_WEDO_LATAM_URL, email) else True
        )

    @route.post(
        path="verify_challenger_by_email",
        operation_id="verify_challenger_by_email",
        response={200: ChallengerProfileResponse, 409: ResponseError},
        deprecated=True,
    )
    def verify_challenger_by_email(self, payload: VerifyChallengerInput):
        coach = self.context.request.auth
        nemo = coach.user_profile.get_content_language.nemo
        # verify challenge exist and is_active register challenger
        try:
            challenge = Challenge.objects.get(
                id=payload.challenge_id, is_active_register_challenger=True, active=True
            )
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["challenge_id"],
                        msg=_(
                            text="challenge not exist or challenger register is inactive",
                            nemo=nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        # verify coach is registered in challenge
        try:
            coach_challenge = CoachChallenge.objects.get(
                challenge=challenge, coach=coach
            )
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["coach_challenge"],
                        msg=_(
                            text="coach is not registered in challenge",
                            nemo=nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        challenger = Challenger.objects.filter(
            profile__user__email=payload.email.strip()
        ).annotate(
            coach_language_nemo=Value(nemo)
        ).first()
        if challenger:
            message = None
            message_type = "info"

            # verify challenger is not registered in challenge with coach
            if ChallengerChallenge.objects.filter(
                challenger=challenger, coach=coach_challenge
            ).exists():
                message = _(
                    text="user already participating in this challenge with you",
                    nemo=nemo,
                )
                message_type = "error"
            # verify challenger is not registered in challenge with another coach
            elif (
                ChallengerChallenge.objects.filter(
                    challenger=challenger, coach__challenge=challenge
                )
                .exclude(coach=coach_challenge)
                .exists()
            ):
                message = _(
                    text="user is already participating in the challenge with another coach",
                    nemo=nemo,
                )
                message_type = "error"
            # verify challenger not has a active invitation
            elif ChallengerInvitationChallenge.objects.filter(
                challenger=challenger,
                coach_challenge__challenge=challenge,
                is_active=True,
            ).exists():
                message = _(
                    text="user already has an active invitation",
                    nemo=nemo,
                )
                message_type = "error"
            # verify challenger is not registered in another challenge in month
            elif ChallengerChallenge.objects.filter(
                challenger=challenger,
                coach__challenge__start__month=challenge.start.month,
            ).exists():
                message = _(
                    text="user is already participating in other challenge this month",
                    nemo=nemo,
                )
                message_type = "error"
            # verify challenger not previously registered with another coach
            elif (
                ChallengerChallenge.objects.filter(challenger=challenger)
                .exclude(coach__coach=coach)
                .exclude(coach__challenge=challenge)
                .exists()
            ):
                message = _(
                    text="this user has participated in previous challenges with another coach",
                    nemo=nemo,
                )
                message_type = "warning"

            return ChallengerProfileResponse(
                challenger=challenger, message_type=message_type, message=message
            )

        return ChallengerProfileResponse(
            challenger=None,
            message_type="error",
            message=_(
                text="user not registered in wedo app as challenger",
                nemo=nemo,
            ),
        )

    @route.post(
        path="verify_challenger_by_email_new",
        operation_id="verify_challenger_by_email_new",
        response={200: ChallengerProfileResponse, 409: ResponseError},
    )
    def verify_challenger_by_email_new(self, payload: VerifyChallengerInput):
        coach = self.context.request.auth
        nemo = coach.user_profile.get_content_language.nemo
        # verify challenge exist and is_active register challenger
        try:
            challenge = Challenge.objects.get(
                id=payload.challenge_id, is_active_register_challenger=True, active=True
            )
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["challenge_id"],
                        msg=_(
                            text="challenge not exist or challenger register is inactive",
                            nemo=nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        # verify coach is registered in challenge
        try:
            coach_challenge = CoachChallenge.objects.get(
                challenge=challenge, coach=coach
            )
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["coach_challenge"],
                        msg=_(
                            text="coach is not registered in challenge",
                            nemo=nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        challenger = Challenger.objects.filter(
            profile__user__email=payload.email.strip()
        ).annotate(
            coach_language_nemo=Value(nemo)
        ).first()
        if challenger:
            # verify challenger is not registered in challenge with coach
            if ChallengerChallenge.objects.filter(
                challenger=challenger, coach=coach_challenge
            ).exists():
                message = _(
                    text="user already participating in this challenge with you",
                    nemo=nemo,
                )
                message_type = "error"
            # verify challenger is not registered in challenge with another coach
            elif (
                ChallengerChallenge.objects.filter(
                    challenger=challenger, coach__challenge=challenge
                )
                .exclude(coach=coach_challenge)
                .exists()
            ):
                message = _(
                    text="user is already participating in the challenge with another coach",
                    nemo=nemo,
                )
                message_type = "error"
            # verify challenger not has a active invitation with same coach
            elif ChallengerInvitationChallenge.objects.filter(
                (Q(challenger=challenger) | Q(email=challenger.user_profile.user.email))
                & Q(coach_challenge__challenge=challenge)
                & Q(status="P")
                & Q(coach_challenge__coach=coach)
            ).exists():
                message = _(
                    text="user already has an active invitation from you",
                    nemo=nemo,
                )
                message_type = "error"
            # verify challenger not has a active invitation
            elif (
                ChallengerInvitationChallenge.objects.filter(
                    (
                        Q(challenger=challenger)
                        | Q(email=challenger.user_profile.user.email)
                    )
                    & Q(coach_challenge__challenge=challenge)
                    & Q(status="P")
                )
                .exclude(coach_challenge__coach=coach)
                .exists()
            ):
                message = _(
                    text="user has an active invitation from other coach. must reject it before send a new",
                    nemo=nemo,
                )
                message_type = "error"
            # verify challenger is not registered in another challenge in month
            elif ChallengerChallenge.objects.filter(
                challenger=challenger,
                coach__challenge__start__month=challenge.start.month,
            ).exists():
                message = _(
                    text="user is already participating in other challenge this month",
                    nemo=nemo,
                )
                message_type = "error"
            # verify challenger not previously registered with another coach
            elif (
                ChallengerChallenge.objects.filter(challenger=challenger)
                .exclude(coach__coach=coach)
                .exclude(coach__challenge=challenge)
                .exists()
            ):
                message = _(
                    text="this user has participated in previous challenges with another coach",
                    nemo=nemo,
                )
                message_type = "warning"
            else:
                message = _(
                    text="user is already registered. invite him so he can access the challenge",
                    nemo=nemo,
                )
                message_type = "info"

            return ChallengerProfileResponse(
                challenger=challenger,
                message_type=message_type,
                message=message,
                email=None,
            )

        if coach.user_profile.user.email.lower() == payload.email.lower().strip():
            message = _(
                text="you can not invite yourself",
                nemo=nemo,
            )
            message_type = "error"
        elif Coach.objects.filter(
            Q(business_partner_email=payload.email.strip())
            | Q(profile__user__email=payload.email.strip())
        ).exists():
            message = _(
                text="not possible to invite this user since he is registered as a coach",
                nemo=nemo,
            )
            message_type = "error"
        elif (
            ChallengerInvitationChallenge.objects.filter(
                email=payload.email.strip(),
                coach_challenge__challenge=challenge,
                status="P",
            )
            .exclude(coach_challenge__coach=coach)
            .exists()
        ):
            message = _(
                text="user has an active invitation from other coach. must reject it before send a new",
                nemo=nemo,
            )
            message_type = "error"
        elif ChallengerInvitationChallenge.objects.filter(
            email=payload.email.strip(),
            coach_challenge__challenge=challenge,
            status="P",
            coach_challenge__coach=coach,
        ).exists():
            message = _(
                text="user is not registered. resend active invitation via email",
                nemo=nemo,
            )
            message_type = "info"
        else:
            message = _(
                text="user is not registered. invite them to the challenge via email",
                nemo=nemo,
            )
            message_type = "info"

        return ChallengerProfileResponse(
            challenger=None,
            message_type=message_type,
            message=message,
            email=payload.email.strip(),
        )

    @route.post(
        path="verify_challenger_by_email_new_v2",
        operation_id="verify_challenger_by_email_new_v2",
        response={200: ChallengerProfileResponse, 409: ResponseError},
    )
    def verify_challenger_by_email_new_v2(self, payload: VerifyChallengerInput):
        coach = self.context.request.auth
        nemo = coach.user_profile.get_content_language.nemo
        challenge_id = payload.challenge_id

        # verify challenge exist and is_active register challenger
        try:
            challenge = Challenge.objects.get(id=payload.challenge_id)

            if not challenge.active:
                return 409, ResponseError(
                    detail=[
                        DetailError(
                            loc=["verify_challenger_by_email_new_v2"],
                            msg=_(
                                text="challenge_inactive",
                                nemo=nemo,
                            ),
                        )
                    ],
                    description="Bad Request",
                )

            if not challenge.is_active_register_challenger:
                return 409, ResponseError(
                    detail=[
                        DetailError(
                            loc=["verify_challenger_by_email_new_v2"],
                            msg=_(
                                text="challenge_not_active_register_challenger",
                                nemo=nemo,
                            ),
                        )
                    ],
                    description="Bad Request",
                )

        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["verify_challenger_by_email_new_v2"],
                        msg=_(
                            text="challenge_not_exist",
                            nemo=nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        # verify coach is registered in challenge
        try:
            coach_challenge = CoachChallenge.objects.get(
                challenge=challenge, coach=coach
            )
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["coach_challenge"],
                        msg=_(
                            text="coach is not registered in challenge",
                            nemo=nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        # coach_payment = CoachPayment.objects.filter(coach=coach_challenge, status='A')
        # if not coach_payment:
        #     message = _(text="coach_has_not_paid_the_challenge", nemo=nemo)
        #     return ChallengerProfileResponse(
        #         challenger=None,
        #         message_type='error',
        #         message=message,
        #         email=payload.email.strip()
        #     )

        code = ''
        challenger = Challenger.objects.filter(
            profile__user__email=payload.email.strip()
        ).annotate(
            coach_language_nemo=Value(nemo)
        ).first()
        if challenger:
            if not challenger.user_profile or not challenger.user_profile.country_id:
                return ChallengerProfileResponse(
                    challenger=challenger,
                    message_type="info",
                    message=_(
                        text="user is not registered. invite them to the challenge via email",
                        nemo=nemo,
                    ),
                    email=payload.email,
                    challenge_id=challenge_id,
                )

            # verify challenger is not registered in challenge with coach
            if ChallengerChallenge.objects.filter(
                challenger=challenger, coach=coach_challenge
            ).exists():
                message = _(
                    text="user already participating in this challenge with you",
                    nemo=nemo,
                )
                message_type = "error"
            # verify challenger is not registered in challenge with another coach
            elif (
                ChallengerChallenge.objects.filter(
                    challenger=challenger, coach__challenge=challenge
                )
                .exclude(coach=coach_challenge)
                .exists()
            ):
                message = _(
                    text="user is already participating in the challenge with another coach",
                    nemo=nemo,
                )
                message_type = "error"
            # verify challenger not has a active invitation with same coach
            elif ChallengerInvitationChallenge.objects.filter(
                (Q(challenger=challenger) | Q(email=challenger.user_profile.user.email))
                & Q(coach_challenge__challenge=challenge)
                & Q(status="P")
                & Q(coach_challenge__coach=coach)
            ).exists():
                message = _(
                    text="user already has an active invitation from you",
                    nemo=nemo,
                )
                message_type = "error"
            # verify challenger not has a active invitation
            elif (
                ChallengerInvitationChallenge.objects.filter(
                    (
                        Q(challenger=challenger)
                        | Q(email=challenger.user_profile.user.email)
                    )
                    & Q(coach_challenge__challenge=challenge)
                    & Q(status="P")
                )
                .exclude(coach_challenge__coach=coach)
                .exists()
            ):
                message = _(
                    text="user has an active invitation from other coach. must reject it before send a new",
                    nemo=nemo,
                )
                message_type = "error"
            # verify challenger is not registered in another challenge in month
            elif ChallengerChallenge.objects.filter(
                challenger=challenger,
                coach__challenge__start__month=challenge.start.month,
            ).exists():
                message = _(
                    text="user is already participating in other challenge this month",
                    nemo=nemo,
                )
                message_type = "error"
            # verify challenger not previously registered with another coach
            elif (
                ChallengerChallenge.objects.filter(challenger=challenger)
                .exclude(coach__coach=coach)
                .exclude(coach__challenge=challenge)
                .exists()
            ):
                message = _(
                    text="this user has participated in previous challenges with another coach",
                    nemo=nemo,
                )
                message_type = "warning"
                code = 'invited_another_coach_other_challenge'
            else:
                message = _(
                    text="user is already registered. invite him so he can access the challenge",
                    nemo=nemo,
                )
                message_type = "info"

            # busco la region de el retador
            challenger_challenge_nickname = (
                challenger.user_profile.country.default_challenge_nickname
            )

            if challenge.nickname != challenger_challenge_nickname:
                # busco si existe un pago para el reto del area geografica a la cual pertenece el retador
                challenge_month = challenge.start.month
                challenge_year = challenge.start.year
                coach_challenge_by_date = CoachChallenge.objects.filter(
                    coach=coach,
                    challenge__start__month=challenge_month,
                    challenge__start__year=challenge_year,
                    challenge__nickname=challenger_challenge_nickname
                ).first()
                if coach_challenge_by_date:
                    message = _(text="can_be_invited_in_another_challenge", nemo=nemo)
                    return ChallengerProfileResponse(
                        challenger=challenger,
                        message_type="info",
                        message=message,
                        email=payload.email.strip(),
                        code="can_invited_another_challenge",
                        region=challenger_challenge_nickname,
                        challenge_name=coach_challenge_by_date.challenge.name,
                        challenge_main_id=coach_challenge_by_date.challenge.main_challenge.id,
                        challenge_id=coach_challenge_by_date.challenge.id,
                    )
                else:
                    message = _(text="cannot_be_invited_in_any_challenge", nemo=nemo)
                    challenge_to_pay = Challenge.objects.filter(
                        start__month=challenge_month,
                        start__year=challenge_year,
                        nickname=challenger_challenge_nickname,
                    ).first()

                    return ChallengerProfileResponse(
                        challenger=challenger,
                        message_type="info",
                        message=message,
                        email=payload.email.strip(),
                        code="pay_region",
                        region=challenger_challenge_nickname,
                        challenge_name=challenge_to_pay.name
                        if challenge_to_pay
                        else "",
                        challenge_main_id=challenge_to_pay.main_challenge.id,
                        challenge_id=challenge_to_pay.id,
                    )

            return ChallengerProfileResponse(
                challenger=challenger,
                message_type=message_type,
                message=message,
                code=code,
                email=None,
                challenge_id=challenge_id,
            )

        if coach.user_profile.user.email.lower() == payload.email.lower().strip():
            message = _(
                text="you can not invite yourself",
                nemo=nemo,
            )
            message_type = "error"
        elif Coach.objects.filter(
            Q(business_partner_email=payload.email.strip())
            | Q(profile__user__email=payload.email.strip())
        ).exists():
            message = _(
                text="not possible to invite this user since he is registered as a coach",
                nemo=nemo,
            )
            message_type = "error"
        elif (
            ChallengerInvitationChallenge.objects.filter(
                email=payload.email.strip(),
                coach_challenge__challenge=challenge,
                status="P",
            )
            .exclude(coach_challenge__coach=coach)
            .exists()
        ):
            message = _(
                text="user has an active invitation from other coach. must reject it before send a new",
                nemo=nemo,
            )
            message_type = "error"
        elif ChallengerInvitationChallenge.objects.filter(
            email=payload.email.strip(),
            coach_challenge__challenge=challenge,
            status="P",
            coach_challenge__coach=coach,
        ).exists():
            message = _(
                text="user is not registered. resend active invitation via email",
                nemo=nemo,
            )
            message_type = "info"
        else:
            message = _(
                text="user is not registered. invite them to the challenge via email",
                nemo=nemo,
            )
            message_type = "info"

        return ChallengerProfileResponse(
            challenger=None,
            message_type=message_type,
            message=message,
            email=payload.email.strip(),
            challenge_id=challenge_id,
        )

    @route.post(
        path="invite_challenger",
        operation_id="invite_challenger",
        response={200: InvitationChallengerResponse, 409: ResponseError},
        deprecated=True,
    )
    def invite_challenger(self, payload: InvitationChallengerInput):
        coach = self.context.request.auth

        # verify challenge exist and is_active register challenger
        try:
            challenge = Challenge.objects.get(
                id=payload.challenge_id, is_active_register_challenger=True, active=True
            )
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["challenge_id"],
                        msg=_(
                            text="challenge not exist or challenger register is inactive",
                            nemo=coach.user_profile.get_content_language.nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        # verify coach is registered in challenge
        try:
            coach_challenge = CoachChallenge.objects.get(
                challenge=challenge, coach=coach
            )
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["coach_challenge"],
                        msg=_(
                            text="coach is not registered in challenge",
                            nemo=coach.user_profile.get_content_language.nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        # verify challenger exist
        try:
            challenger = Challenger.objects.get(id=payload.challenger_id)
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["challenger"],
                        msg=_(
                            text="challenger is not registered",
                            nemo=coach.user_profile.get_content_language.nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        # verify challenger is not registered in challenge
        if ChallengerChallenge.objects.filter(
            challenger=challenger, coach__challenge=challenge
        ).exists():
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["challenger_id, challenge_id"],
                        msg=_(
                            text="challenger already registered in challenge",
                            nemo=coach.user_profile.get_content_language.nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        try:
            invitation = ChallengerInvitationChallenge.objects.get(
                coach_challenge=coach_challenge, challenger=challenger
            )
            invitation.is_active = True
            invitation.status = "P"
        except ObjectDoesNotExist:
            invitation = ChallengerInvitationChallenge()
            invitation.coach_challenge = coach_challenge
            invitation.challenger = challenger
            invitation.status = "P"
            invitation.review_status = "S"
        invitation.save()

        challenger_registration_token = challenger.user_profile.firebase_token
        if challenger_registration_token:
            msg_body = _(
                text="invited you to join to challenge",
                nemo=challenger.user_profile.get_content_language.nemo,
            )
            send_notification(
                registration_token=challenger_registration_token,
                title=_(
                    text="you have a new invitation",
                    nemo=challenger.user_profile.get_content_language.nemo,
                ),
                body=f"{coach.user_profile.user.first_name} {msg_body} {challenge.name}",
                object_id=str(invitation.pk),
                context="INVITATION",
            )
        return InvitationChallengerResponse()

    @route.post(
        path="invite_challenger_new",
        operation_id="invite_challenger_new",
        response={200: InvitationChallengerResponse, 409: ResponseError},
    )
    def invite_challenger_new(self, payload: InvitationChallengerNewInput):
        coach = self.context.request.auth

        # verify challenge exist and is_active register challenger
        try:
            challenge = Challenge.objects.get(
                id=payload.challenge_id, is_active_register_challenger=True, active=True
            )
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["challenge_id"],
                        msg=_(
                            text="challenge not exist or challenger register is inactive",
                            nemo=coach.user_profile.get_content_language.nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        # verify coach is registered in challenge
        try:
            coach_challenge = CoachChallenge.objects.get(
                challenge=challenge, coach=coach
            )
            # coach_nemo = coach_challenge.coach.user_profile.get_content_language
            # coach_token = coach_challenge.coach.user_profile.firebase_token
            # coach_name = coach_challenge.coach.user_profile.user.first_name
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["coach_challenge"],
                        msg=_(
                            text="coach is not registered in challenge",
                            nemo=coach.user_profile.get_content_language.nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        if not payload.challenger_id and not payload.email:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["coach_challenge"],
                        msg=_(
                            text="challenger_id or email are required fields",
                            nemo=coach.user_profile.get_content_language.nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        # verify challenger exist
        if payload.challenger_id:
            try:
                challenger = Challenger.objects.get(id=payload.challenger_id)
            except ObjectDoesNotExist:
                return 409, ResponseError(
                    detail=[
                        DetailError(
                            loc=["challenger"],
                            msg=_(
                                text="challenger is not registered",
                                nemo=coach.user_profile.get_content_language.nemo,
                            ),
                        )
                    ],
                    description="Bad Request",
                )

            # verify challenger is not registered in challenge
            if ChallengerChallenge.objects.filter(
                challenger=challenger, coach__challenge=challenge
            ).exists():
                return 409, ResponseError(
                    detail=[
                        DetailError(
                            loc=["challenger_id, challenge_id"],
                            msg=_(
                                text="challenger already registered in challenge",
                                nemo=coach.user_profile.get_content_language.nemo,
                            ),
                        )
                    ],
                    description="Bad Request",
                )

            try:
                invitation = ChallengerInvitationChallenge.objects.get(
                    coach_challenge=coach_challenge, challenger=challenger, status="P"
                )

                if invitation.number_invitations_sent > 1:
                    return 409, ResponseError(
                        detail=[
                            DetailError(
                                loc=["invite_challenger_new"],
                                msg=_(
                                    text="maximum_number_of_invitations_sent_exceeded",
                                    nemo=coach.user_profile.get_content_language.nemo,
                                ),
                            )
                        ],
                        description="Bad Request",
                    )

                invitation.number_invitations_sent += 1

            except ObjectDoesNotExist:
                invitation = ChallengerInvitationChallenge()
                invitation.coach_challenge = coach_challenge
                invitation.challenger = challenger
                invitation.status = "P"
                invitation.review_status = "S"
            invitation.email = challenger.user_profile.user.email
            invitation.save()
            challenger_registration_token = challenger.user_profile.firebase_token
            if challenger_registration_token:
                msg_body = _(
                    text="invited you to join to challenge",
                    nemo=challenger.user_profile.get_content_language.nemo,
                )
                send_notification(
                    registration_token=challenger_registration_token,
                    title=_(
                        text="you have a new invitation",
                        nemo=challenger.user_profile.get_content_language.nemo,
                    ),
                    body=f"{coach.user_profile.user.first_name} {msg_body} {challenge.name}",
                    object_id=str(invitation.pk),
                    context="INVITATION",
                )
            send_challenger_invitation_email(
                email=challenger.user_profile.user.email,
                invitation_id=invitation.id,
                coach_name=coach.user_profile.user.first_name,
                language_nemo=coach.user_profile.get_content_language.nemo,
            )
            return InvitationChallengerResponse()

        elif ChallengerChallenge.objects.filter(
            challenger__profile__user__email=payload.email.strip(),
            coach__challenge=challenge,
        ).exists():
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["challenger_id, challenge_id"],
                        msg=_(
                            text="challenger already registered in challenge",
                            nemo=coach.user_profile.get_content_language.nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )
        elif (
            ChallengerInvitationChallenge.objects.filter(
                coach_challenge__challenge=challenge,
                email=payload.email.strip(),
                status="P",
            )
            .exclude(coach_challenge=coach_challenge)
            .exists()
        ):
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["challenger_id, challenge_id"],
                        msg=_(
                            text="user already has an active invitation",
                            nemo=coach.user_profile.get_content_language.nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        try:
            invitation = ChallengerInvitationChallenge.objects.get(
                coach_challenge=coach_challenge, email=payload.email.strip(), status="P"
            )

            if invitation.number_invitations_sent > 1:
                return 409, ResponseError(
                    detail=[
                        DetailError(
                            loc=["invite_challenger_new"],
                            msg=_(
                                text="maximum_number_of_invitations_sent_exceeded",
                                nemo=coach.user_profile.get_content_language.nemo,
                            ),
                        )
                    ],
                    description="Bad Request",
                )

            invitation.number_invitations_sent += 1
            invitation.save()

        except ObjectDoesNotExist:
            invitation = ChallengerInvitationChallenge()
            invitation.coach_challenge = coach_challenge
            invitation.challenger = None
            invitation.status = "P"
            invitation.review_status = "S"
            invitation.email = payload.email.strip()
            invitation.save()

        send_challenger_invitation_email(
            email=payload.email.strip(),
            invitation_id=invitation.id,
            coach_name=coach.user_profile.user.first_name,
            language_nemo=coach.user_profile.get_content_language.nemo,
        )

        return InvitationChallengerResponse()

    @route.get(
        path="get_challengers_challenge",
        operation_id="get_challengers_challenge",
        response={200: GeneralChallengersChallengeResponse, 409: ResponseError},
    )
    def get_challengers_challenge(self, challenge_id: int):
        coach = self.context.request.auth
        try:
            challenge = Challenge.objects.get(id=challenge_id)
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[DetailError(loc=["challenge"], msg="challenge not exist")],
                description="Bad Request",
            )
        try:
            coach_challenge = CoachChallenge.objects.get(
                coach=coach, challenge=challenge, status=True
            )
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["coach"],
                        msg="coach not exist or not active for this challenge",
                    )
                ],
                description="Bad Request",
            )

        challengers = (
            ChallengerChallenge.objects.select_related("challenger")
            .filter(coach=coach_challenge)
            .annotate(
                first_name=F("challenger__profile__user__first_name"),
                email=F("challenger__profile__user__email"),
                country_name=F("challenger__profile__country__name"),
            )
        )

        challengers_actives_usernames = challengers.values_list(
            "challenger__profile__user__username"
        )

        total_challengers = len(challengers)
        completed_challengers = (
            ChallengerChallenge.objects.filter(Q(coach=coach_challenge))
            .exclude(
                Q(initial_front_photo__isnull=True)
                | Q(initial_side_photo__isnull=True)
                | Q(initial_back_photo__isnull=True)
                | Q(initial_video__isnull=True)
                | Q(final_front_photo__isnull=True)
                | Q(final_side_photo__isnull=True)
                | Q(final_back_photo__isnull=True)
                | Q(final_video__isnull=True)
                | Q(image__isnull=True)
                | Q(initial_front_photo="")
                | Q(initial_side_photo="")
                | Q(initial_back_photo="")
                | Q(initial_video="")
                | Q(final_front_photo="")
                | Q(final_side_photo="")
                | Q(final_back_photo="")
                | Q(final_video="")
                | Q(image="")
            )
            .count()
        )

        effective_challengers = (
            0
            if total_challengers == 0
            else round(completed_challengers * 100 / total_challengers, 2)
        )

        invitations = ChallengerInvitationChallenge.objects.exclude(status="A").filter(
            Q(coach_challenge__challenge_id=challenge_id),
            ~Q(email__in=challengers_actives_usernames),
            Q(coach_challenge__coach=coach),
        )

        pending = []
        for item in invitations:
            if item.email:
                email = item.email
            else:
                email = item.challenger.user_profile.user.username

            status = None
            if item.status in ("P"):
                status = "pending"

            if item.status in ("R", "E"):
                status = "rejected"

            challenger = get_challenger_by_email(email=email)
            account_created, profile, country = False, None, None
            if challenger:
                account_created = True
                profile = ProfileSchema.from_orm(challenger.user_profile)

            pending.append(
                ChallengeInvitationPending(
                    email=email,
                    invitation_date=item.created_date,
                    status=status,
                    account_created=account_created,
                    profile=profile,
                    number_invitations_sent=item.number_invitations_sent
                )
            )

        return GeneralChallengersChallengeResponse(
            challengers=list(challengers),
            total_challengers=total_challengers,
            completed_challengers=completed_challengers,
            effective_challengers=effective_challengers,
            pending=pending,
            is_active_register_challenger=challenge.is_active_register_challenger,
            start_upload_initial_files=challenge.start_upload_initial_files,
            end_upload_initial_files=challenge.end_upload_initial_files,
            start_upload_final_files=challenge.start_upload_final_files,
            end_upload_final_file=challenge.end_upload_final_files,
        )

    @route.post(
        path="upload_challenger_multimedia",
        operation_id="upload_challenger_multimedia",
        response={200: ChallengerChallengeResponse, 409: ResponseError},
    )
    def upload_challenger_multimedia(
        self,
        payload: UploadChallengerMultimediaInput = Form(...),
        initial_front_photo: UploadedFile = None,
        initial_side_photo: UploadedFile = None,
        initial_back_photo: UploadedFile = None,
        final_front_photo: UploadedFile = None,
        final_side_photo: UploadedFile = None,
        final_back_photo: UploadedFile = None,
        initial_video: UploadedFile = None,
        final_video: UploadedFile = None,
    ):
        coach = self.context.request.auth

        # verify challenger is not registered in challenge
        try:
            challenger_challenge = ChallengerChallenge.objects.get(
                id=payload.challenger_challenge_id, coach__coach=coach
            )
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["upload_challenger_multimedia"],
                        msg="Challenger Challenge not exist",
                    )
                ],
                description="Bad Request",
            )

        is_active_upload_initial_multimedia = (
            challenger_challenge.coach.challenge.is_active_upload_files
        )
        is_active_upload_final_multimedia = (
            challenger_challenge.coach.challenge.is_active_upload_final_files
        )

        if not (
            is_active_upload_initial_multimedia or is_active_upload_final_multimedia
        ):
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["upload_challenger_multimedia"],
                        msg="Upload files is inactive for this challenge",
                    )
                ],
                description="Bad Request",
            )

        any_file_changed = False
        initial_files_changed = False
        final_files_changed = False

        if initial_front_photo and is_active_upload_initial_multimedia:
            challenger_challenge.initial_front_photo = initial_front_photo
            any_file_changed = True
            initial_files_changed = True

        if initial_side_photo and is_active_upload_initial_multimedia:
            challenger_challenge.initial_side_photo = initial_side_photo
            any_file_changed = True
            initial_files_changed = True

        if initial_back_photo and is_active_upload_initial_multimedia:
            challenger_challenge.initial_back_photo = initial_back_photo
            any_file_changed = True
            initial_files_changed = True

        if final_front_photo and is_active_upload_final_multimedia:
            challenger_challenge.final_front_photo = final_front_photo
            any_file_changed = True
            final_files_changed = True

        if final_side_photo and is_active_upload_final_multimedia:
            challenger_challenge.final_side_photo = final_side_photo
            any_file_changed = True
            final_files_changed = True

        if final_back_photo and is_active_upload_final_multimedia:
            challenger_challenge.final_back_photo = final_back_photo
            any_file_changed = True
            final_files_changed = True

        if initial_video and is_active_upload_initial_multimedia:
            challenger_challenge.initial_video = initial_video
            any_file_changed = True
            initial_files_changed = True

        if final_video and is_active_upload_final_multimedia:
            challenger_challenge.final_video = final_video
            any_file_changed = True
            final_files_changed = True

        if any_file_changed:
            cond1 = challenger_challenge.initial_front_photo
            cond2 = challenger_challenge.initial_side_photo
            cond3 = challenger_challenge.initial_back_photo
            cond4 = challenger_challenge.final_front_photo
            cond5 = challenger_challenge.final_side_photo
            cond6 = challenger_challenge.final_back_photo
            cond7 = challenger_challenge.initial_video
            cond8 = challenger_challenge.final_video

            if cond1 and cond2 and cond3 and cond7 and initial_files_changed:
                challenger_challenge.uploaded_initial_photo_date = (
                    datetime.datetime.utcnow()
                )

            if cond4 and cond5 and cond6 and cond8 and final_files_changed:
                challenger_challenge.uploaded_final_photo_date = (
                    datetime.datetime.utcnow()
                )

            challenger_challenge.save()

            if cond1 and cond2 and cond3 and cond4 and cond5 and cond6:
                create_challenger_collage(challenger_challenge=challenger_challenge)

        return (
            ChallengerChallenge.objects.select_related("challenger")
            .filter(id=payload.challenger_challenge_id, coach__coach=coach)
            .annotate(
                first_name=F("challenger__profile__user__first_name"),
                email=F("challenger__profile__user__email"),
                country_name=F("challenger__profile__country__name"),
            )
            .first()
        )

    @route.get(
        path="get_partner_info",
        operation_id="get_partner_info",
        response={200: PartnerResponse, 409: ResponseError},
    )
    def get_partner_info(self):
        coach = self.context.request.auth
        return PartnerResponse(
            business_partner_email=coach.business_partner_email,
            couple_identifier=coach.user_profile.user.first_name,
            business_partner_name=coach.business_partner_name,
        )

    @route.post(
        path="update_partner_info",
        operation_id="update_partner_info",
        response={200: bool, 409: ResponseError},
    )
    def update_partner_info(self, payload: PartnerRegisterInput):
        coach = self.context.request.auth

        if not payload.business_partner_email or not payload.couple_identifier:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["update_partner_info"],
                        msg=_(
                            text="business partner email and couple identifier are fields required",
                            nemo=coach.user_profile.get_content_language.nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        if (
            coach.user_profile.user.email.strip().upper()
            == payload.business_partner_email.strip().upper()
        ):
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["update_partner_info"],
                        msg=_(
                            text="business partner email can't be same coach email",
                            nemo=coach.user_profile.get_content_language.nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        if (
            Coach.objects.filter(business_partner_email=payload.business_partner_email)
            .exclude(id=coach.id)
            .exists()
        ):
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["register_coach_info"],
                        msg=_(
                            text="email is associated with another coach. please try another.",
                            nemo=coach.user_profile.get_content_language.nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        if Coach.objects.filter(
            profile__user__email=payload.business_partner_email,
            business_partner_email__isnull=False,
        ).exists():
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["register_coach_info"],
                        msg=_(
                            text="email belongs to a coach with an spouse or legal partner. please try another.",
                            nemo=coach.user_profile.get_content_language.nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        partner_profile = UserProfile.objects.filter(
            user__email=payload.business_partner_email
        ).first()
        if partner_profile:
            if CoachChallenge.objects.filter(
                coach__profile__user__email=payload.business_partner_email
            ).exists():
                return 409, ResponseError(
                    detail=[
                        DetailError(
                            loc=["update_partner_info"],
                            msg=_(
                                text="there is a registered active coach with that email. please try another.",
                                nemo=coach.user_profile.get_content_language.nemo,
                            ),
                        )
                    ],
                    description="Bad Request",
                )

            if ChallengerChallenge.objects.filter(
                challenger__profile__user__email=payload.business_partner_email
            ).exists():
                return 409, ResponseError(
                    detail=[
                        DetailError(
                            loc=["update_partner_info"],
                            msg=_(
                                text="there is a registered challenger with that email. please try another.",
                                nemo=coach.user_profile.get_content_language.nemo,
                            ),
                        )
                    ],
                    description="Bad Request",
                )
            Coach.objects.filter(profile=partner_profile).delete()
            Challenger.objects.filter(profile=partner_profile).delete()
            partner_user = partner_profile.user
            partner_user.delete()

        try:
            # update coach
            coach.business_partner_email = payload.business_partner_email
            coach.save()
            user = coach.user_profile.user
            user.first_name = payload.couple_identifier
            user.save()
            return True

        except Exception:
            return 409, ResponseError(
                detail=[
                    DetailError(loc=["coach"], msg="An error occurred updating coach")
                ]
            )

    @route.post(
        path="delete_partner_info",
        operation_id="delete_partner_info",
        response={200: bool, 409: ResponseError},
    )
    def delete_partner_info(self):
        coach = self.context.request.auth
        try:
            coach.business_partner_email = None
            coach.business_partner_name = None
            coach.save()
        except Exception:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["coach"], msg="An error occurred deleting coach partner"
                    )
                ]
            )

        return True

    @route.post(
        path="verify_challenger_to_promote_by_email",
        operation_id="verify_challenger_to_promote_by_email",
        response={200: ChallengerProfileResponse, 409: ResponseError},
    )
    def verify_challenger_to_promote_by_email(
        self, payload: VerifyChallengerToPromoteInput
    ):
        coach = self.context.request.auth
        nemo = coach.user_profile.get_content_language.nemo
        coaches_challenge = CoachChallenge.objects.filter(coach=coach)
        if not coaches_challenge:
            return ChallengerProfileResponse(
                challenger=None,
                message_type="error",
                message=_(
                    text="coach is not active in challenge, can't promote challenger to coach",
                    nemo=nemo,
                ),
                email=None,
            )
        challenger = Challenger.objects.filter(
            profile__user__email=payload.email.strip()
        ).annotate(
            coach_language_nemo=Value(nemo)
        ).first()
        if challenger:
            # verify the challenger is registered in any challenge with coach
            if not ChallengerChallenge.objects.filter(
                challenger=challenger, coach_id__in=coaches_challenge.values_list("id")
            ).exists():
                return ChallengerProfileResponse(
                    challenger=None,
                    message_type="error",
                    message=_(
                        text="we can’t find this email as your challenger",
                        nemo=nemo,
                    ),
                    email=None,
                )
            elif ChallengerPromotedCoach.objects.filter(
                challenger=challenger, status="P"
            ).exists():
                return ChallengerProfileResponse(
                    challenger=None,
                    message_type="error",
                    message=_(
                        text="challenger already has an pending invitation for transform to coach",
                        nemo=nemo,
                    ),
                    email=None,
                )

            return ChallengerProfileResponse(
                challenger=challenger, message_type="info", message=None, email=None
            )

        return ChallengerProfileResponse(
            challenger=None,
            message_type="error",
            message=_(
                text="user not registered in wedo app as challenger",
                nemo=nemo,
            ),
            email=None,
        )

    @route.post(
        path="promote_challenger",
        operation_id="promote_challenger",
        response={200: PromotedChallengerResponse, 409: ResponseError},
    )
    def promote_challenger(self, payload: PromotedChallengerInput):
        coach = self.context.request.auth
        coaches_challenge = CoachChallenge.objects.filter(coach=coach)
        if not coaches_challenge:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["promote_challenger"],
                        msg=_(
                            text="coach is not active in challenge, can't promote challenger to coach",
                            nemo=coach.user_profile.get_content_language.nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        # verify challenger exist
        try:
            challenger = Challenger.objects.get(id=payload.challenger_id)
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["promote_challenger"],
                        msg=_(
                            text="challenger is not registered",
                            nemo=coach.user_profile.get_content_language.nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        if ChallengerPromotedCoach.objects.filter(
            challenger=challenger, status="P"
        ).exists():
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["promote_challenger"],
                        msg=_(
                            text="challenger already has an pending invitation for transform to coach",
                            nemo=coach.user_profile.get_content_language.nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        # verify challenger is registered with coach
        if not ChallengerChallenge.objects.filter(
            challenger=challenger, coach_id__in=coaches_challenge.values_list("id")
        ).exists():
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["promote_challenger"],
                        msg=_(
                            text="we can’t find this email as your challenger",
                            nemo=coach.user_profile.get_content_language.nemo,
                        ),
                    )
                ],
                description="Bad Request",
            )

        promotion = ChallengerPromotedCoach()
        promotion.promoter_coach = coach
        promotion.challenger = challenger
        promotion.status = "P"
        promotion.save()

        challenger_registration_token = challenger.user_profile.firebase_token
        if challenger_registration_token:
            msg_body = _(
                text="invited you to transform to coach",
                nemo=challenger.user_profile.get_content_language.nemo,
            )
            send_notification(
                registration_token=challenger_registration_token,
                title=_(
                    text="you have a new invitation",
                    nemo=challenger.user_profile.get_content_language.nemo,
                ),
                body=f"{coach.user_profile.user.first_name} {msg_body}",
                object_id=str(promotion.pk),
                context="TRANSFORM",
            )
        return PromotedChallengerResponse()

    # @route.post(
    #     path="resend_challenge_invitation",
    #     operation_id="resend_challenge_invitation",
    #     response={200: ChallengerProfileResponse, 409: ResponseError},
    # )
    # def resend_challenge_invitation(self, payload: VerifyChallengerInput):
    #
