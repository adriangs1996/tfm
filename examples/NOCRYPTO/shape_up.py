import datetime

from django.db.models import (
    Q, F, Exists, OuterRef, Count, Subquery, Value, ExpressionWrapper, BooleanField,
)
from wedo_core_service.models import (
    ShapeUpEvent, ShapeUpUserPriorityZone, ShapeUpGeneralConfig, City, Coach, ShapeUpCoachAuthorizedCity,
    ShapeUpOrganizerCoachRequest,
)

from api.schemas.view_models import (
    ShapeUpDeepInfoResponse, ShapeUpCountriesFilterResponse, ShapeUpCitiesFilterResponse, ShapeUpLightInfoResponse,
    ShapeUpMyEventsResponse,
)
from api.services.custom_translate import get_translate_text as _


def get_country_name_from_city_by_lang(nemo, city):
    if nemo.startswith('es'):
        return city.country.name_es
    if nemo.startswith('fr'):
        return city.country.name_fr
    if nemo.startswith('pt'):
        return city.country.name_pt
    if nemo.startswith('it'):
        return city.country.name_it
    return city.country.name


def get_country_name_by_lang(nemo, country):
    if nemo.startswith('es'):
        return country.name_es
    if nemo.startswith('fr'):
        return country.name_fr
    if nemo.startswith('pt'):
        return country.name_pt
    if nemo.startswith('it'):
        return country.name_it
    return country.name


def get_user_filters(content_object, current_datetime, language):
    user = content_object.user_profile.user
    user_country = content_object.user_profile.country
    nemo = language.nemo
    cities_selected = []
    countries_filter = []
    city_selected_subquery = ShapeUpUserPriorityZone.objects.filter(
        user=user, active=True, country__isnull=True, city_id=OuterRef('id')
    )
    city_events_count = ShapeUpEvent.objects.filter(
        city_id=OuterRef('id'), start_time__gte=current_datetime, active=True
    ).values('city_id').annotate(count=Count('city_id')).values("count")

    all_cities = ShapeUpUserPriorityZone.objects.filter(user=user, active=True, all_city=True).exists()

    all_user_country_cities = ShapeUpUserPriorityZone.objects.filter(
        user=user, active=True, country=user_country
    ).exists()
    if all_cities:
        cities_selected.append(_(text='all cities', nemo=nemo))
    if all_user_country_cities:
        cities_selected.append(f'{_(text="all", nemo=nemo)} {user_country.name}')
    any_filter_selected = all_cities or all_user_country_cities

    all_future_events = ShapeUpEvent.objects.filter(Q(start_time__gte=current_datetime) & Q(active=True)).count()

    countries_filter.append(
        ShapeUpCountriesFilterResponse(
            name=None,
            cities=[
                ShapeUpCitiesFilterResponse(
                    country_id=None,
                    city_id=None,
                    all_cities=True,
                    name=_(text='all cities', nemo=nemo),
                    total_future_events=all_future_events,
                    selected=all_cities
                )
            ]
        )
    )

    user_cities = City.objects.prefetch_related(
        'shapeupuserpriorityzone_set'
    ).filter(
        country=user_country
    ).annotate(
        selected=Exists(city_selected_subquery),
        events=Subquery(city_events_count)
    )

    cities = []
    total_country_events = 0
    for user_city in user_cities:
        if user_city.selected:
            any_filter_selected = True
            cities_selected.append(user_city.name)
        cities.append(
            ShapeUpCitiesFilterResponse(
                country_id=None,
                city_id=user_city.id,
                all_cities=False,
                name=user_city.name,
                total_future_events=user_city.events if user_city.events else 0,
                selected=user_city.selected
            )
        )
        total_country_events += user_city.events if user_city.events else 0

    cities.insert(
        0,
        ShapeUpCitiesFilterResponse(
            country_id=user_country.id,
            city_id=None,
            all_cities=False,
            name=f'{_(text="all", nemo=nemo)} {user_country.name}',
            total_future_events=total_country_events,
            selected=all_user_country_cities
        )
    )

    countries_filter.append(
        ShapeUpCountriesFilterResponse(
            name=F'{_(text="cities", nemo=nemo)} {get_country_name_by_lang(nemo=nemo, country=user_country)}',
            cities=cities
        )
    )

    other_cities = City.objects.prefetch_related(
        'shapeupuserpriorityzone_set'
    ).filter(
        ~Q(country=user_country)
    ).annotate(
        selected=Exists(city_selected_subquery),
        events=Subquery(city_events_count)
    )

    cities = []
    for user_city in other_cities:
        if user_city.selected:
            any_filter_selected = True
            cities_selected.append(user_city.name)
        cities.append(
            ShapeUpCitiesFilterResponse(
                country_id=None,
                city_id=user_city.id,
                all_cities=False,
                name=f'{user_city.name}, {get_country_name_from_city_by_lang(nemo=nemo, city=user_city)}',
                total_future_events=user_city.events if user_city.events else 0,
                selected=user_city.selected
            )
        )

    countries_filter.append(
        ShapeUpCountriesFilterResponse(
            name=_(text='cities others countries', nemo=nemo),
            cities=cities
        )
    )

    return countries_filter, any_filter_selected, ','.join(cities_selected)


def get_events(content_object, language, current_datetime):
    user = content_object.user_profile.user
    query_filters = Q(start_time__gte=current_datetime) & Q(active=True)
    if not ShapeUpUserPriorityZone.objects.filter(user=user, active=True, all_city=True).exists():
        query_filters &= (
            Q(
                city__in=Subquery(
                    ShapeUpUserPriorityZone.objects.filter(
                        user=user,
                        active=True,
                        city__isnull=False,
                        country__isnull=True
                    ).values_list('city_id', flat=True)
                )
            ) | Q(
                city__country__in=Subquery(
                    ShapeUpUserPriorityZone.objects.filter(
                        user=user,
                        active=True,
                        city__isnull=True,
                        country__isnull=False
                    ).values_list('country_id', flat=True)
                )
            )
        )

    if isinstance(content_object, Coach):
        expression = ExpressionWrapper(
            Q(organizer_coach=content_object),
            output_field=BooleanField()
        )
    else:
        expression = Value(False)

    events = ShapeUpEvent.objects.prefetch_related(
        'city', 'city__country'
    ).filter(
        query_filters
    ).annotate(
        city_name=F('city__name'),
        country_name_en=F('city__country__name'),
        country_name_es=F('city__country__name_es'),
        country_name_fr=F('city__country__name_fr'),
        country_name_it=F('city__country__name_it'),
        country_name_pt=F('city__country__name_pt'),
        nemo=Value(language.nemo),
        time_zone_info=F('city__time_zone_info'),
        can_edit_event=expression
    )

    return list(events)


def get_my_events(content_object, language, current_datetime):
    future_events = None
    past_events = None
    if isinstance(content_object, Coach):
        past_events = ShapeUpEvent.objects.prefetch_related(
            'city', 'city__country'
        ).filter(
            Q(start_time__lt=current_datetime) &
            Q(organizer_coach=content_object)
        ).annotate(
            city_name=F('city__name'),
            country_name_en=F('city__country__name'),
            country_name_es=F('city__country__name_es'),
            country_name_fr=F('city__country__name_fr'),
            country_name_it=F('city__country__name_it'),
            country_name_pt=F('city__country__name_pt'),
            nemo=Value(language.nemo),
            time_zone_info=F('city__time_zone_info'),
            can_edit_event=ExpressionWrapper(
                Q(organizer_coach=content_object),
                output_field=BooleanField()
            )
        )

        future_events = ShapeUpEvent.objects.prefetch_related(
            'city', 'city__country'
        ).filter(
            Q(start_time__gte=current_datetime) &
            Q(organizer_coach=content_object)
        ).annotate(
            city_name=F('city__name'),
            country_name_en=F('city__country__name'),
            country_name_es=F('city__country__name_es'),
            country_name_fr=F('city__country__name_fr'),
            country_name_it=F('city__country__name_it'),
            country_name_pt=F('city__country__name_pt'),
            nemo=Value(language.nemo),
            time_zone_info=F('city__time_zone_info'),
            can_edit_event=ExpressionWrapper(
                Q(organizer_coach=content_object),
                output_field=BooleanField()
            )
        )

    return ShapeUpMyEventsResponse(
        future=list(future_events) if future_events else None,
        past=list(past_events) if past_events else None
    )


def get_general_config(language):
    return ShapeUpGeneralConfig.objects.filter(Q(language=language) | Q(default=True)).order_by('default').first()


def get_deep_shape_up_info(content_object, language):
    current_datetime = datetime.datetime.utcnow()

    can_create_event = False
    can_request_create_event = False
    if isinstance(content_object, Coach):
        can_create_event = ShapeUpCoachAuthorizedCity.objects.filter(coach=content_object, active=True).exists()
        can_request_create_event = (
            content_object.position.order >= 80 and
            not ShapeUpOrganizerCoachRequest.objects.filter(coach=content_object, status='P').exists()
        )

    filters, any_filter_selected, cities_selected = get_user_filters(
        content_object=content_object, current_datetime=current_datetime, language=language
    )

    return ShapeUpDeepInfoResponse(
        events=get_events(
            content_object=content_object, language=language, current_datetime=current_datetime
        ),
        config=get_general_config(
            language=language
        ),
        cities_selected=cities_selected,
        any_filter_selected=any_filter_selected,
        filters=filters,
        can_create_event=can_create_event,
        can_request_create_event=can_request_create_event,
        my_events=get_my_events(
            content_object=content_object, language=language, current_datetime=current_datetime
        )
    )


def get_light_shape_up_info(content_object, language):
    current_datetime = datetime.datetime.utcnow()

    return ShapeUpLightInfoResponse(
        events=get_events(
            content_object=content_object,
            language=language,
            current_datetime=current_datetime
        ),
        config=get_general_config(
            language=language
        )
    )


def get_event(shape_up_event_id, content_object, language):
    if isinstance(content_object, Coach):
        expression = ExpressionWrapper(
            Q(organizer_coach=content_object),
            output_field=BooleanField()
        )
    else:
        expression = Value(False)

    return ShapeUpEvent.objects.prefetch_related(
        'city', 'city__country'
    ).filter(
        id=shape_up_event_id, active=True
    ).annotate(
        city_name=F('city__name'),
        country_name_en=F('city__country__name'),
        country_name_es=F('city__country__name_es'),
        country_name_fr=F('city__country__name_fr'),
        country_name_it=F('city__country__name_it'),
        country_name_pt=F('city__country__name_pt'),
        nemo=Value(language.nemo),
        time_zone_info=F('city__time_zone_info'),
        can_edit_event=expression
    ).first()
