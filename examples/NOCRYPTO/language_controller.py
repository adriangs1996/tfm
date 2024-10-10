from typing import List
from django.core.exceptions import ObjectDoesNotExist
from ninja_extra import (
    ControllerBase,
    api_controller,
    route
)
from wedo_core_service.models import (
    CoachChallenge,
    Challenge,
    ChallengeConfig,
)
from api.schemas.view_models import (
    ResponseError,
    DetailError,
    LanguageResponse, RegisterCoachChallengeLanguageInput,
)


@api_controller('language', tags=['Language'])
class LanguageController(ControllerBase):
    """
    Group functionalities to coach language model
    """

    @route.get(
        path='get_available_language_for_challenge',
        operation_id='get_available_language_for_challenge',
        response={200: List[LanguageResponse], 409: ResponseError}
    )
    def get_available_language_for_challenge(self, challenge_id: int):
        coach = self.context.request.auth
        try:
            challenge = Challenge.objects.get(id=challenge_id)
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['challenge'],
                        msg="challenge not exist"
                    )
                ],
                description='Bad Request'
            )
        try:
            CoachChallenge.objects.get(coach=coach, challenge=challenge, status=True)
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['coach'],
                        msg="coach not exist or not active for this challenge"
                    )
                ],
                description='Bad Request'
            )

        challenge_configs = ChallengeConfig.objects.select_related('language').filter(
            challenge=challenge
        )

        languages = []
        for challenge_config in challenge_configs:
            languages.append(
                LanguageResponse.from_orm(challenge_config.language)
            )
        return languages

    @route.post(
        path='update_coach_challenge_language',
        operation_id='update_coach_challenge_language',
        response={200: bool, 409: ResponseError}
    )
    def update_coach_challenge_language(self, payload: RegisterCoachChallengeLanguageInput):
        coach = self.context.request.auth

        try:
            coach_challenge = CoachChallenge.objects.get(challenge_id=payload.challenge_id, coach=coach)

        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['coach'],
                        msg="coach not exist or not active for this challenge"
                    )
                ],
                description='Bad Request'
            )

        try:
            coach_challenge.content_language_id = payload.language_id
            coach_challenge.save()
        except Exception:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['coach_challenge'],
                        msg="An error occurred while registering language for coach_challenge"
                    )
                ]
            )

        return True
