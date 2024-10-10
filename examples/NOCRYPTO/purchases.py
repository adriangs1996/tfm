from typing import List

from django.db.models import F, Value
from ninja_extra import ControllerBase, api_controller
from ninja_extra.controllers import route
from wedo_core_service.models import (
    CoachPayment, MainChallenge, Challenge,
)
from wedo_core_service.services.auth import (
    CoachJWTAuth,
)

from api.schemas.view_models import (
    ResponseError, CoachPurchases, DetailError,
)
from api.services.payment import get_combo_months_for_purchase, get_coach_purchases_by_challenge
from api.services.custom_translate import get_translate_text as _


@api_controller('purchases', tags=['My Purchases'])
class PurchasesController(ControllerBase):

    @route.get(
        path='',
        operation_id='get_coach_purchases',
        response={200: List[CoachPurchases], 400: ResponseError},
        auth=CoachJWTAuth()
    )
    def get_coach_purchases(self):
        coach = self.context.request.auth
        language = coach.user_profile.get_content_language
        purchases = []
        try:
            main_challenges = MainChallenge.objects.prefetch_related(
                'mainchallengepaymentcombo_set'
            ).all().order_by('-start')
            for main_challenge in main_challenges:
                main_challenge_payment_combos = main_challenge.mainchallengepaymentcombo_set.all()
                challenges = main_challenge.challenge_set.all()
                for main_challenge_payment_combo in main_challenge_payment_combos:
                    coach_payments = CoachPayment.objects.filter(
                        coach__coach=coach,
                        coach__challenge__in=challenges,
                        amount=main_challenge_payment_combo.price
                    ).annotate(
                        purchase_date=F('payment_date'),
                        purchase_amount=F('amount'),
                        purchase_challenge=Value(_(text='all regions', nemo=language.nemo)),
                        purchase_quantity=Value(main_challenge_payment_combo.quantity_challenge_paid)
                    ).values(
                        'purchase_date', 'purchase_amount', 'purchase_challenge', 'purchase_quantity'
                    ).distinct()
                    for coach_payment in coach_payments:
                        purchases.append(
                            CoachPurchases(
                                date=str(coach_payment.get('purchase_date')),
                                amount=coach_payment.get('purchase_amount'),
                                challenge=coach_payment.get('purchase_challenge'),
                                quantity=coach_payment.get('purchase_quantity'),
                                months=get_combo_months_for_purchase(
                                    start_date=main_challenge.start,
                                    combo_quantity_challenge=coach_payment.get('purchase_quantity'),
                                    language=language
                                )
                            )
                        )
                for challenge in challenges:
                    coach_purchases = get_coach_purchases_by_challenge(challenge, coach, language)
                    for coach_purchase in coach_purchases:
                        purchases.append(coach_purchase)

            others_challenges = Challenge.objects.prefetch_related(
                'challengepaymenttype_set'
            ).filter(
                main_challenge__isnull=True
            ).order_by('-start')
            for challenge in others_challenges:
                coach_purchases = get_coach_purchases_by_challenge(challenge, coach, language)
                for coach_purchase in coach_purchases:
                    purchases.append(coach_purchase)

            if purchases:
                purchases = sorted(purchases, key=lambda x: x.date, reverse=True)
        except Exception as error:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['get_coach_purchases'],
                        msg=f"An error occurred getting coach purchases: ({error})"
                    )
                ]
            )

        return purchases
