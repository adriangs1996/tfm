from dateutil.relativedelta import relativedelta
from django.db.models import F, Value
from wedo_core_service.models import Challenge, CoachPayment

from api.schemas.view_models import CoachPurchasesMonths, CoachPurchases
from api.services.custom_translate import get_translate_text as _


def get_combo_months_for_purchase(start_date, combo_quantity_challenge, language):
    months = []
    for i in range(1, combo_quantity_challenge + 1, 1):
        started = False
        if i == 1:
            new_date = start_date
        else:
            new_date = start_date + relativedelta(months=i-1)

        if (
                combo_quantity_challenge == 1 or
                Challenge.objects.filter(start__month=new_date.month, start__year=new_date.year).exists()
        ):
            started = True

        months.append(
            CoachPurchasesMonths(
                month=_(text=new_date.strftime('%B').lower(), nemo=language.nemo).capitalize(),
                started=started
            )
        )

    return months


def get_coach_purchases_by_challenge(challenge, coach, language):
    purchases = []
    payment_types = challenge.challengepaymenttype_set.all()
    for payment_type in payment_types:
        challenge_payment_combos = payment_type.challengepaymentcombo_set.all()
        for challenge_payment_combo in challenge_payment_combos:
            coach_payments = CoachPayment.objects.select_related(
                'coach', 'coach__challenge', 'coach__coach'
            ).filter(
                coach__coach=coach,
                coach__challenge=challenge,
                amount=challenge_payment_combo.price
            ).annotate(
                purchase_date=F('payment_date'),
                purchase_amount=F('amount'),
                purchase_challenge=F('coach__challenge__name'),
                purchase_quantity=Value(challenge_payment_combo.quantity_challenge_paid)
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
                            start_date=challenge.start,
                            combo_quantity_challenge=coach_payment.get('purchase_quantity'),
                            language=language
                        )
                    )
                )
    return purchases
