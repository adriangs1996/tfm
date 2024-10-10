import random

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F
from ninja_extra import (
    ControllerBase,
    api_controller,
    route,
)
from wedo_core_service.models import (
    ChallengeVotingRoundJury,
    ChallengerVotingRoundPanel,
    ChallengeVotingRoundPanel,
    ChallengeWinner,
    ChallengerChallenge,
    ChallengeRoundVotingResult,
    CoachChallenge,
)
from wedo_core_service.utils import convert_date_to_timezone

from api.schemas.view_models import (
    ResponseError,
    DetailError,
    VotingRoundChallengerInput,
    VotingRoundChallengerResponse,
    RegisterVotingRoundChallengerInput,
    RegisterVotingRoundChallengerResponse,
)
from api.services.custom_translate import get_translate_text as _


@api_controller('voting', tags=['Voting'])
class VotingController(ControllerBase):
    """
    Group functionalities to voting process
    """
    @route.post(
        path='get_challenger_for_voting',
        operation_id='get_challenger_for_voting',
        response={200: VotingRoundChallengerResponse, 409: ResponseError}
    )
    def get_challenger_for_voting(self, payload: VotingRoundChallengerInput):
        coach = self.context.request.auth
        nemo = coach.user_profile.get_content_language.nemo
        try:
            challenge_voting_round_panel = ChallengeVotingRoundPanel.objects.get(
                id=payload.challenge_voting_round_panel
            )
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['get_challenger_for_voting'],
                        msg="Challenge Voting Round Panel not exist"
                    )
                ],
                description='Bad Request'
            )

        try:
            challenge_voting_round_jury = ChallengeVotingRoundJury.objects.get(
                jury_id=payload.jury,
                challenge_voting_round_panel=challenge_voting_round_panel
            )
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['get_challenger_for_voting'],
                        msg="Challenge Voting Round Jury not exist"
                    )
                ],
                description='Bad Request'
            )

        total_challengers = ChallengerVotingRoundPanel.objects.filter(
            challenge_voting_round_panel=challenge_voting_round_panel
        ).count()

        challengers_pending_vote = ChallengerChallenge.objects.select_related(
            'challenger'
        ).filter(
            coach__challenge=challenge_voting_round_panel.challenge_voting_round.challenge,
            challengervotingroundpanel__challenge_voting_round_panel=challenge_voting_round_panel
        ).annotate(
            first_name=F('challenger__profile__user__first_name'),
            challenger_voting_round_panel_id=F('challengervotingroundpanel__id')
        )

        if not challenge_voting_round_panel.challenge_voting_round.is_final:
            challengers_pending_vote = challengers_pending_vote.exclude(
                challengervotingroundpanel__challengeroundvotingresult__challenger_voting_round_jury=challenge_voting_round_jury
            )
        else:
            pending_votes = ChallengeRoundVotingResult.objects.filter(
                challenger_voting_round_jury=challenge_voting_round_jury,
                is_valid=False
            ).count()

            if pending_votes == 0:
                challengers_pending_vote = challengers_pending_vote.exclude(
                    challengervotingroundpanel__challengeroundvotingresult__challenger_voting_round_jury=challenge_voting_round_jury
                )

        list_challenger_to_evaluate = []
        if len(challengers_pending_vote.all()) > 0:
            if challenge_voting_round_panel.challenge_voting_round.is_final:
                challenger_pending_vote_ids = challengers_pending_vote.values('challenger_id').distinct()
                challenger_winners = ChallengeWinner.objects.filter(
                    is_valid=True,
                    challenger__challenger__id__in=challenger_pending_vote_ids
                ).order_by(
                    "-challenger__coach__challenge__start"
                ).all()
                for challenger_pending_vote in challengers_pending_vote:

                    try:
                        points = ChallengeRoundVotingResult.objects.get(
                            challenger_voting_round_panel=challenger_pending_vote.challenger_voting_round_panel_id,
                            challenger_voting_round_jury=challenge_voting_round_jury
                        )
                    except ChallengeRoundVotingResult.DoesNotExist:
                        points = None

                    list_challenger_to_evaluate.append({
                        "challenger_pending_vote": challenger_pending_vote,
                        "challenger_previous_winner": list(challenger_winners.filter(
                            challenger__challenger__id=challenger_pending_vote.challenger.id
                        )),
                        "points": points.points if points else None
                    })
            else:
                next_challenger = challengers_pending_vote[random.randint(0, challengers_pending_vote.__len__() - 1)]
                challenger_winners = ChallengeWinner.objects.filter(
                    is_valid=True,
                    challenger__challenger__id=next_challenger.challenger_id
                ).order_by(
                    "-challenger__coach__challenge__start"
                ).all()
                list_challenger_to_evaluate.append({
                    "challenger_pending_vote": next_challenger,
                    "challenger_previous_winner": list(challenger_winners),
                    "points": None
                })

        total_pending_vote = len(challengers_pending_vote)

        round_number = challenge_voting_round_panel.challenge_voting_round.order
        challenge_month = _(
            text=convert_date_to_timezone(
                date=challenge_voting_round_panel.challenge_voting_round.challenge.start,
                output_format='%B'
            ).lower(),
            nemo=nemo
        )
        if round_number == 1:
            round_number_text = _(text="1st round", nemo=nemo)
        elif round_number == 2:
            round_number_text = _(text="2nd round", nemo=nemo)
        else:
            round_number_text = _(text="final round", nemo=nemo)

        return VotingRoundChallengerResponse(
            jury_id=payload.jury,
            challenge_voting_round_panel_id=payload.challenge_voting_round_panel,
            total_challengers=total_challengers,
            total_pending_vote=total_pending_vote,
            current_voting_number=total_challengers - total_pending_vote + 1 if total_pending_vote > 0 else total_challengers,
            is_voting_completed=not total_pending_vote > 0,
            round_number=round_number,
            is_final_round=challenge_voting_round_panel.challenge_voting_round.is_final,
            list_challenger_to_evaluate=list_challenger_to_evaluate,
            round_text=_(text="challenge_voting_round_text", nemo=nemo).format(
                round_number_text=round_number_text, challenge_month=challenge_month
            )
        )

    @route.post(
        path='register_vote',
        operation_id='register_vote',
        response={200: RegisterVotingRoundChallengerResponse, 409: ResponseError}
    )
    def register_vote(self, payload: RegisterVotingRoundChallengerInput):

        jury_id = payload.jury_id
        jury_votes = payload.jury_vote

        try:
            jury = CoachChallenge.objects.get(id=jury_id)
            for jury_vote in jury_votes:
                challenger_voting_round_panel = ChallengerVotingRoundPanel.objects.get(
                    id=jury_vote.challenger_voting_round_panel_id
                )

                challenge_voting_round_jury = ChallengeVotingRoundJury.objects.get(
                    challenge_voting_round_panel=challenger_voting_round_panel.challenge_voting_round_panel,
                    jury=jury
                )

                try:
                    challenge_round_voting_result = ChallengeRoundVotingResult.objects.get(
                        challenger_voting_round_panel=challenger_voting_round_panel,
                        challenger_voting_round_jury=challenge_voting_round_jury
                    )
                except ObjectDoesNotExist:
                    challenge_round_voting_result = ChallengeRoundVotingResult()

                challenge_round_voting_result.challenger_voting_round_jury = challenge_voting_round_jury
                challenge_round_voting_result.challenger_voting_round_panel = challenger_voting_round_panel
                challenge_round_voting_result.is_valid = False
                challenge_round_voting_result.points = jury_vote.points
                challenge_round_voting_result.save()

        except Exception:

            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['register_vote'],
                        msg="Anh error occurred when register voting"
                    )
                ],
                description='Bad Request'
            )

        total_pending_vote = ChallengerVotingRoundPanel.objects.filter(
            challenge_voting_round_panel__id=payload.challenge_voting_round_panel_id
        ).exclude(
            challengeroundvotingresult__in=ChallengeRoundVotingResult.objects.filter(
                challenger_voting_round_panel__challenge_voting_round_panel__id=payload.challenge_voting_round_panel_id,
                challenger_voting_round_jury__jury=jury
            )
        ).count()

        is_voting_completed = False
        if total_pending_vote == 0:
            ChallengeRoundVotingResult.objects.filter(
                challenger_voting_round_jury__jury=jury,
                challenger_voting_round_jury__challenge_voting_round_panel__id=payload.challenge_voting_round_panel_id
            ).update(
                is_valid=True
            )
            is_voting_completed = True

        return RegisterVotingRoundChallengerResponse(
            is_voting_completed=is_voting_completed
        )
