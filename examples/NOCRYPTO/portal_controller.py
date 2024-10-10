from django.db.models import (
    Q, F
)
from ninja_extra import (
    ControllerBase, api_controller, route
)
from wedo_core_service.models import (
    CoachChallenge, Challenge, ChallengerInvitationChallenge, ChallengerChallenge, MainChallenge,
    ChallengeGroupContent, Challenger, Coach, ChallengerPromotedCoach, UserCompletedComponent, ChallengeComponent,
    ChallengeGroup, UserPriorityGroup
)
from wedo_core_service.repository.coach_black_list import is_id_herbalife_in_black_list
from wedo_core_service.services.auth import ProfileJWTAuth
from wedo_core_service.utils import get_url_without_parameters

from api.schemas.view_models import (
    ResponseError, DetailError, ChallengeHomeResponseV2, CoachChallengersResponseV2, EnrolledRegionV2,
    DashboardResponseV2, ChallengerProfilePhotoResponseV2, ChallengesResponseV2, OpenChallengeResponseV2,
    ActiveChallengeChatContentResponseV2, ActiveChallengeChatResponseV2, ChallengeGroupContentResponseV2,
    UserCompletedComponentInputV2, UserCompletedComponentResponseV2, UserPriorityGroupInputV2,
    UserPriorityGroupResponseV2,
)
from api.services.challenge_group import get_challenge_group_detail
from api.services.challenge_home import (
    get_active_challenges, get_past_challenges, get_next_challenge, get_pending_actions, get_main_challenge_groups,
    can_show_buy_button, get_active_invitations
)
from api.services.chat import get_challenge_chats
from api.services.highlight import get_all_highlights
from api.services.shape_up import get_light_shape_up_info


@api_controller('portal', tags=['Portal'])
class PortalController(ControllerBase):
    """
    Group functionalities to manage challenge home for coach
    """
    @route.get(
        path='/dashboard/',
        operation_id='get_coach_dashboard',
        response={200: DashboardResponseV2, 409: ResponseError},
        auth=ProfileJWTAuth()
    )
    def get_coach_dashboard(self):
        try:
            user_profile = self.context.request.auth
            content_object = user_profile.content_object
            if not content_object or (
                not isinstance(content_object, Coach) and not isinstance(content_object, Challenger)
            ):
                return 401, ResponseError(
                    detail=[
                        DetailError(
                            loc=['get_dashboard'],
                            msg="Unauthorized"
                        )
                    ],
                    description='Unauthorized'
                )
            language = user_profile.get_content_language
            if isinstance(content_object, Coach):
                coach = content_object
                coach_challenges = CoachChallenge.objects.filter(coach=coach, challenge__main_challenge__isnull=False)
                main_challenge_ids = coach_challenges.values_list('challenge__main_challenge_id').distinct()
                challenge_ids = coach_challenges.values_list('challenge_id').distinct()
                coach_challenge_ids = coach_challenges.values('id').distinct()
                pending_actions = get_pending_actions(
                    coach_challenge_ids=coach_challenge_ids, challenge_ids=challenge_ids, language=language
                )
                is_in_black_list = is_id_herbalife_in_black_list(content_object.id_herbalife)
                next_challenges = [] if is_in_black_list else get_next_challenge(
                    main_challenge_ids=main_challenge_ids, language=language, user_type='COACH'
                )
                pending_invitation_to_transform_coach = None

            else:
                challenger = content_object
                challenger_challenges = ChallengerChallenge.objects.filter(
                    challenger=challenger, coach__challenge__main_challenge__isnull=False
                )
                main_challenge_ids = challenger_challenges.values_list('coach__challenge__main_challenge_id').distinct()
                challenge_ids = challenger_challenges.values_list('coach__challenge_id').distinct()
                pending_actions = []
                next_challenges = get_next_challenge(
                    main_challenge_ids=main_challenge_ids, language=language, user_type='CHALLENGER'
                )
                pending_invitation_to_transform_coach = ChallengerPromotedCoach.objects.filter(
                    challenger=challenger, status='P'
                ).first()

            return DashboardResponseV2(
                pending_actions=pending_actions,
                next_challenges=next_challenges,
                past_challenges=get_past_challenges(challenge_ids=challenge_ids, language=language),
                active_challenges=get_active_challenges(
                    challenge_ids=challenge_ids, language=language, active_type='CURRENT'
                ),
                next_active_challenges=get_active_challenges(
                    challenge_ids=challenge_ids, language=language, active_type='NEXT'
                ),
                active_invitations=get_active_invitations(content_object=content_object, language=language),
                pending_invitation_to_transform_coach=pending_invitation_to_transform_coach,
                highlights=get_all_highlights(content_object=content_object, language=language),
                shape_up_info=get_light_shape_up_info(content_object=content_object, language=language)
            )

        except Exception as error:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['get_dashboard'],
                        msg=f"An error occurred getting dashboard info: ({error})"
                    )
                ]
            )

    @route.get(
        path='/challenges/',
        operation_id='get_challenges',
        response={200: ChallengesResponseV2, 409: ResponseError},
        auth=ProfileJWTAuth()
    )
    def get_challenges(self):
        try:
            user_profile = self.context.request.auth
            content_object = user_profile.content_object
            if not content_object or (
                not isinstance(content_object, Coach) and not isinstance(content_object, Challenger)
            ):
                return 401, ResponseError(
                    detail=[
                        DetailError(
                            loc=['get_dashboard'],
                            msg="Unauthorized"
                        )
                    ],
                    description='Unauthorized'
                )
            language = user_profile.get_content_language
            if isinstance(content_object, Coach):
                coach_challenges = CoachChallenge.objects.filter(
                    coach=content_object, challenge__main_challenge__isnull=False
                )
                main_challenge_ids = coach_challenges.values_list('challenge__main_challenge_id').distinct()
                challenge_ids = coach_challenges.values_list('challenge_id').distinct()
                is_in_black_list = is_id_herbalife_in_black_list(content_object.id_herbalife)
                next_challenges = [] if is_in_black_list else get_next_challenge(
                    main_challenge_ids=main_challenge_ids, language=language, user_type='COACH'
                )

            else:
                challenger_challenges = ChallengerChallenge.objects.filter(
                    challenger=content_object, coach__challenge__main_challenge__isnull=False
                )
                main_challenge_ids = challenger_challenges.values_list('coach__challenge__main_challenge_id').distinct()
                challenge_ids = challenger_challenges.values_list('coach__challenge_id').distinct()
                next_challenges = get_next_challenge(
                    main_challenge_ids=main_challenge_ids, language=language, user_type='CHALLENGER'
                )

            return ChallengesResponseV2(
                open_challenges=OpenChallengeResponseV2(
                    next_challenges=next_challenges,
                    active_challenges=get_active_challenges(
                        challenge_ids=challenge_ids, language=language, active_type='CURRENT'
                    ),
                    next_active_challenges=get_active_challenges(
                        challenge_ids=challenge_ids, language=language, active_type='NEXT'
                    ),
                    allow_buy_challenge=can_show_buy_button(content_object=content_object),
                ),
                past_challenges=get_past_challenges(challenge_ids=challenge_ids, language=language)
            )

        except Exception as error:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['get_challenges'],
                        msg=f"An error occurred getting challenges info: ({error})"
                    )
                ]
            )

    @route.get(
        path='/preview/{main_challenge_id}',
        operation_id='get_challenge_preview',
        response={200: ChallengeHomeResponseV2, 409: ResponseError},
        auth=ProfileJWTAuth()
    )
    def get_challenge_preview(self, main_challenge_id: int):
        try:
            user_profile = self.context.request.auth
            content_object = user_profile.content_object
            if not content_object or (
                    not isinstance(content_object, Coach) and not isinstance(content_object, Challenger)
            ):
                return 401, ResponseError(
                    detail=[
                        DetailError(
                            loc=['get_dashboard'],
                            msg="Unauthorized"
                        )
                    ],
                    description='Unauthorized'
                )

            try:
                main_challenge = MainChallenge.objects.get(id=main_challenge_id)
            except MainChallenge.DoesNotExist:
                return 409, ResponseError(
                    detail=[
                        DetailError(
                            loc=['get_challenge_preview'],
                            msg="MainChallenge no exist"
                        )
                    ],
                    description='Bad Request'
                )

            try:
                challenge = Challenge.objects.get(
                    main_challenge=main_challenge,
                    nickname=user_profile.country.default_challenge_nickname
                )
            except Challenge.DoesNotExist:
                return 409, ResponseError(
                    detail=[
                        DetailError(
                            loc=['get_challenge_preview'],
                            msg="Challenge no exist"
                        )
                    ],
                    description='Bad Request'
                )

            language = user_profile.get_content_language
            groups_list_response = get_main_challenge_groups(
                challenge=challenge, content_object=content_object, language=language
            )

            main_challenge_response = get_next_challenge(
                main_challenge_ids=list([]),
                language=language,
                user_type='COACH',
                main_challenge_id=main_challenge_id
            )

            return ChallengeHomeResponseV2(
                pending_actions=[],
                enrolled_region=None,
                challengers=None,
                challenge=None,
                main_challenge=main_challenge_response[0] if main_challenge_response else None,
                challenge_groups_content=groups_list_response,
                coach_challenge=None,
                challenger_challenge=None
            )

        except Exception as error:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['get_challenge_preview'],
                        msg=f"An error occurred getting challenge preview info: ({error})"
                    )
                ]
            )

    @route.get(
        path='/home/{challenge_id}',
        operation_id='get_challenge_home',
        response={200: ChallengeHomeResponseV2, 409: ResponseError},
        auth=ProfileJWTAuth()
    )
    def get_challenge_home(self, challenge_id: int):
        try:
            user_profile = self.context.request.auth
            content_object = user_profile.content_object
            if not content_object or (
                    not isinstance(content_object, Coach) and not isinstance(content_object, Challenger)
            ):
                return 401, ResponseError(
                    detail=[
                        DetailError(
                            loc=['get_dashboard'],
                            msg="Unauthorized"
                        )
                    ],
                    description='Unauthorized'
                )

            try:
                challenge = Challenge.objects.get(id=challenge_id)
            except Challenge.DoesNotExist:
                return 409, ResponseError(
                    detail=[
                        DetailError(
                            loc=['get_challenge_home'],
                            msg="Challenge no exist"
                        )
                    ],
                    description='Bad Request'
                )

            language = user_profile.get_content_language
            pending_actions = []
            enrolled_region, coach_challenge, challengers, challenger_challenge_ = None, None, None, None
            if isinstance(content_object, Coach):
                try:
                    coach_challenge = CoachChallenge.objects.get(
                        challenge=challenge, coach=content_object, status=True
                    )
                except CoachChallenge.DoesNotExist:
                    return 409, ResponseError(
                        detail=[
                            DetailError(
                                loc=['get_challenge_home'],
                                msg="CoachChallenge no exist"
                            )
                        ],
                        description='Bad Request'
                    )

                pending_actions = get_pending_actions(
                    coach_challenge_ids=list([coach_challenge.id]),
                    challenge_ids=list([challenge.id]),
                    language=language
                )

                challenge_config = coach_challenge.challenge.challengeconfig_set.filter(
                    Q(language=language) | Q(default=True)
                ).order_by('default').first()
                if challenge_config:
                    enrolled_region = EnrolledRegionV2(
                        name=challenge_config.region_name,
                        challenge_id=coach_challenge.challenge.id
                    )

                challengers_challenge = ChallengerChallenge.objects.select_related('challenger').filter(
                    coach=coach_challenge, status=True
                ).annotate(
                    challenger_name=F('challenger__profile__user__first_name')
                )
                challengers = None
                if challengers_challenge:
                    challenger_profile_photos = []
                    for challenger_challenge in challengers_challenge:
                        profile = challenger_challenge.challenger.user_profile
                        profile_photo = (
                            get_url_without_parameters(profile.profile_photo.url) if profile.profile_photo else None
                        )
                        if profile_photo:
                            challenger_profile_photos.append(
                                ChallengerProfilePhotoResponseV2(
                                    first_name=challenger_challenge.challenger_name, profile_photo=profile_photo
                                )
                            )
                    challengers = CoachChallengersResponseV2(
                        enrolled=challengers_challenge.count(),
                        guested=ChallengerInvitationChallenge.objects.filter(
                            coach_challenge=coach_challenge,
                            status='P'
                        ).count(),
                        challenger_profile_photos=challenger_profile_photos[:2] if challenger_profile_photos else None
                    )
            else:
                try:
                    challenger_challenge_ = ChallengerChallenge.objects.get(
                        coach__challenge=challenge, challenger=content_object, status=True
                    )
                except ChallengerChallenge.DoesNotExist:
                    return 409, ResponseError(
                        detail=[
                            DetailError(
                                loc=['get_challenge_home'],
                                msg="ChallengerChallenge no exist"
                            )
                        ],
                        description='Bad Request'
                    )

            return ChallengeHomeResponseV2(
                pending_actions=pending_actions,
                enrolled_region=enrolled_region,
                challengers=challengers,
                challenge=get_active_challenges(challenge_ids=list([challenge.id]), language=language)[0],
                main_challenge=None,
                challenge_groups_content=get_main_challenge_groups(
                    challenge=challenge, content_object=content_object, language=language
                ),
                coach_challenge=coach_challenge,
                challenger_challenge=challenger_challenge_
            )

        except Exception as error:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['get_challenge_home'],
                        msg=f"An error occurred getting challenge home info: ({error})"
                    )
                ]
            )

    @route.get(
        path='/chats/',
        operation_id='get_coach_chats',
        response={200: ActiveChallengeChatResponseV2, 409: ResponseError},
        auth=ProfileJWTAuth()
    )
    def get_coach_chats(self):
        try:
            user_profile = self.context.request.auth
            content_object = user_profile.content_object
            if not content_object or (
                    not isinstance(content_object, Coach) and not isinstance(content_object, Challenger)
            ):
                return 401, ResponseError(
                    detail=[
                        DetailError(
                            loc=['get_dashboard'],
                            msg="Unauthorized"
                        )
                    ],
                    description='Unauthorized'
                )

            language = user_profile.get_content_language
            if isinstance(content_object, Coach):
                coach_challenges = CoachChallenge.objects.filter(
                    coach=content_object, challenge__main_challenge__isnull=False
                )
                challenge_ids = coach_challenges.values_list('challenge_id').distinct()
            else:
                challenger_challenges = ChallengerChallenge.objects.filter(
                    challenger=content_object, coach__challenge__main_challenge__isnull=False
                )
                challenge_ids = challenger_challenges.values_list('coach__challenge_id').distinct()

            active_challenges = get_active_challenges(challenge_ids=challenge_ids, language=language)
            active_challenge_chats = []
            for active_challenge in active_challenges:
                active_challenge_chats.append(
                    ActiveChallengeChatContentResponseV2(
                        active_challenge=active_challenge,
                        challenge_chats=get_challenge_chats(
                            challenge=active_challenge.challenge, content_object=content_object, language=language
                        )
                    )
                )

            if active_challenge_chats:
                active_challenge_chats = sorted(
                    active_challenge_chats,
                    key=lambda x: x.active_challenge.challenge.start
                )

            return ActiveChallengeChatResponseV2(active_challenge_with_chat=active_challenge_chats)

        except Exception as error:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['get_coach_chats'],
                        msg=f"An error occurred getting chats info: ({error})"
                    )
                ]
            )

    @route.get(
        path='/group_details/{challenge_group_id}',
        operation_id='get_group_details',
        response={200: ChallengeGroupContentResponseV2, 409: ResponseError},
        auth=ProfileJWTAuth()
    )
    def get_group_details(self, challenge_group_id):
        try:
            user_profile = self.context.request.auth
            content_object = user_profile.content_object
            if not content_object or (
                    not isinstance(content_object, Coach) and not isinstance(content_object, Challenger)
            ):
                return 401, ResponseError(
                    detail=[
                        DetailError(
                            loc=['get_dashboard'],
                            msg="Unauthorized"
                        )
                    ],
                    description='Unauthorized'
                )

            language = user_profile.get_content_language
            query_filter = Q(
                challenge_group__id=challenge_group_id) & Q(
                challenge_group__is_active=True) & (
                    Q(language=language) | Q(default=True)
                )
            if isinstance(content_object, Coach):
                query_filter &= (
                    Q(challenge_group__is_visible_from_position__isnull=True) |
                    Q(challenge_group__is_visible_from_position__order__lte=content_object.position.order)
                ) & Q(challenge_group__visible_by__in=['ALL', 'COACH'])
            else:
                query_filter &= Q(challenge_group__visible_by__in=['ALL', 'CHALLENGER'])

            challenge_group_content = ChallengeGroupContent.objects.select_related(
                'challenge_group'
            ).filter(
                query_filter
            ).order_by('default').first()

            return get_challenge_group_detail(
                challenge_group_content=challenge_group_content,
                content_object=content_object,
                language=language,
                is_first_group_search=True,
                is_subgroup_level=True
            )

        except Exception as error:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['get_group_details'],
                        msg=f"An error occurred getting group details info: ({error})"
                    )
                ]
            )

    @route.post(
        path="/completed_component/",
        operation_id="set_completed_component",
        response={200: UserCompletedComponentResponseV2, 409: ResponseError},
        auth=ProfileJWTAuth()
    )
    def set_completed_component(self, payload: UserCompletedComponentInputV2):
        try:
            user_profile = self.context.request.auth
            try:
                challenge_component = ChallengeComponent.objects.get(id=payload.challenge_component_id)
            except ChallengeComponent.DoesNotExist:
                return 409, ResponseError(
                    detail=[
                        DetailError(
                            loc=["set_completed_component"],
                            msg="component not exist",
                        )
                    ],
                    description="Bad Request",
                )
            try:
                user_completed_component = UserCompletedComponent.objects.get(
                    user=user_profile.user, challenge_component=challenge_component
                )
            except UserCompletedComponent.DoesNotExist:
                user_completed_component = UserCompletedComponent()
                user_completed_component.user = user_profile.user
                user_completed_component.challenge_component = challenge_component

            user_completed_component.completed = payload.completed
            user_completed_component.save()

            return user_completed_component
        except Exception as error:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['get_dashboard'],
                        msg=f"An error occurred set set_completed_component: ({error})"
                    )
                ]
            )

    @route.post(
        path="/priority_group/",
        operation_id="set_priority_group",
        response={200: UserPriorityGroupResponseV2, 409: ResponseError},
        auth=ProfileJWTAuth()
    )
    def set_priority_group(self, payload: UserPriorityGroupInputV2):
        try:
            user_profile = self.context.request.auth
            try:
                challenge_group = ChallengeGroup.objects.get(id=payload.challenge_group_id)
            except ChallengeGroup.DoesNotExist:
                return 409, ResponseError(
                    detail=[
                        DetailError(
                            loc=["set_priority_group"],
                            msg="challenge_group not exist",
                        )
                    ],
                    description="Bad Request",
                )

            UserPriorityGroup.objects.filter(
                challenge_group__parent=challenge_group.parent,
                user=user_profile.user
            ).update(active=False)

            try:
                user_priority_group = UserPriorityGroup.objects.get(
                    challenge_group=challenge_group,
                    user=user_profile.user
                )
            except UserPriorityGroup.DoesNotExist:
                user_priority_group = UserPriorityGroup()
                user_priority_group.user = user_profile.user
                user_priority_group.challenge_group = challenge_group

            user_priority_group.active = payload.active
            user_priority_group.save()

            return user_priority_group
        except Exception as error:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['set_priority_group'],
                        msg=f"An error occurred set set_priority_group: ({error})"
                    )
                ]
            )
