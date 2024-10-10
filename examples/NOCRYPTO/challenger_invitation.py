from typing import List

from django.core.exceptions import ObjectDoesNotExist
from ninja_extra import api_controller, ControllerBase, route
from wedo_core_service.models import ChallengerInvitationChallenge, ChallengerChallenge, Challenge
from wedo_core_service.repository.challenger import get_challenger_by_email

from api.schemas.view_models import ChallengeInvitationSummaryResponse, ResponseError, ChallengeInvitationPending, \
    ChallengerInvitedResponse, ProfileSchema, ChallengerChallengeActiveResponse, DetailError, InvitedHistorical


@api_controller("invitations", tags=["ChallengerInvitationChallenge"])
class ChallengerInvitationController(ControllerBase):
    """
    Group functionalities to ChallengerInvitationChallenge model
    """

    @route.get(
        path="invited",
        operation_id="invited",
        response={200: List[InvitedHistorical], 409: ResponseError}
    )
    def invited(self, challenge_id: int = None):
        coach = self.context.request.auth
        results = ChallengerInvitationChallenge.objects.filter(coach_challenge__coach=coach,
                                                               status='A').order_by('-created_date')

        challengers_info, ids = [], []
        for result in results:
            challenger = result.challenger
            if not challenger:
                challenger = get_challenger_by_email(email=result.email)

            if challenger and challenger.id not in ids:
                ids.append(challenger.id)
                is_invited, active_in_challenge = False, False
                number_invitations_sent = 0
                if challenge_id:
                    invitation = ChallengerInvitationChallenge.objects.filter(coach_challenge__coach_id=coach.id,
                                                                               coach_challenge__challenge_id=challenge_id,
                                                                               email=challenger.user_profile.user.username,
                                                                               status__in=['P', 'A']).first()
                    if invitation:
                        is_invited = True
                        number_invitations_sent = invitation.number_invitations_sent
                        active_in_challenge = True if invitation.status == 'A' else False

                challengers_info.append(InvitedHistorical(challenger=ChallengerInvitedResponse.from_orm(challenger),
                                                          is_invited=is_invited,
                                                          number_invitations_sent=number_invitations_sent,
                                                          active_in_challenge=active_in_challenge))

        return challengers_info

    @route.get(
        path="coach/summary/{challenge_id}/",
        operation_id="get_invitations_summary",
        response={200: ChallengeInvitationSummaryResponse, 409: ResponseError},
        deprecated=True
    )
    def get_invitations_summary(self, challenge_id):
        coach = self.context.request.auth

        try:
            challenge = Challenge.objects.get(id=challenge_id)
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[DetailError(loc=["challenge"], msg="Challenge not exist")],
                description="Bad Request",
            )

        invitations = ChallengerInvitationChallenge.objects.exclude(status='A').filter(
            coach_challenge__challenge_id=challenge_id,
            coach_challenge__coach=coach)

        challenger_challenge_list = ChallengerChallenge.objects.filter(coach__coach=coach,
                                                                       coach__challenge_id=challenge_id)
        actives = []
        for item in challenger_challenge_list:
            actives.append(ChallengerChallengeActiveResponse.from_orm(item))

        pending = []
        for item in invitations:
            if item.email:
                email = item.email
            else:
                email = item.challenger.user_profile.user.username

            status = None
            if item.status in ('P'):
                status = 'pending'

            if item.status in ('R', 'E'):
                status = 'rejected'

            challenger = get_challenger_by_email(email=email)
            account_created, profile = False, None
            if challenger:
                account_created = True
                profile = ProfileSchema.from_orm(challenger.user_profile)

            pending.append(ChallengeInvitationPending(email=email,
                                                      invitation_date=item.created_date,
                                                      status=status,
                                                      account_created=account_created,
                                                      profile=profile))

        return ChallengeInvitationSummaryResponse(actives=actives,
                                                  pending=pending,
                                                  is_active_register_challenger=challenge.is_active_register_coach)
