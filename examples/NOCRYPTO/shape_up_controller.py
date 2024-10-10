from typing import List

from django.conf import settings
from ninja import (
    Form, UploadedFile,
)
from ninja_extra import (
    ControllerBase, api_controller, route
)
from wedo_core_service.models import (
    Challenger, Coach, ShapeUpOrganizerCoachRequest, ShapeUpCoachAuthorizedCity, ShapeUpEvent, ShapeUpUserPriorityZone
)
from wedo_core_service.services.auth import (
    ProfileJWTAuth, CoachJWTAuth,
)
from wedo_core_service.utils import convert_date_to_timezone

from api.schemas.view_models import (
    ResponseError, DetailError, ShapeUpEventResponse, ShapeUpDeepInfoResponse, ShapeUpAuthorizationRequest,
    ShapeUpAuthorizationResponse, ShapeUpCoachAuthorizedCityResponse, ShapeUpEventInput, ShapeUpEventBannerInput,
    ShapeUpCitiesFilterInput,
)
from api.services.notifications import send_slack_notification
from api.services.shape_up import (
    get_event, get_deep_shape_up_info, get_country_name_from_city_by_lang, get_general_config
)


@api_controller('shape_up', tags=['ShapeUp'])
class ShapeUpController(ControllerBase):
    """
    Group functionalities to manage ShapeUp
    """
    @route.get(
        path='/event/{event_id}',
        operation_id='get_shape_up_event',
        response={200: ShapeUpEventResponse, 409: ResponseError},
        auth=ProfileJWTAuth()
    )
    def get_shape_up_event(self, event_id: int):
        try:
            user_profile = self.context.request.auth
            content_obj = user_profile.content_object
            if not content_obj or (not isinstance(content_obj, Coach) and not isinstance(content_obj, Challenger)):
                return 401, ResponseError(
                    detail=[
                        DetailError(
                            loc=['get_shape_up_event'],
                            msg="Unauthorized"
                        )
                    ],
                    description='Unauthorized'
                )
            language = user_profile.get_content_language
            event = get_event(shape_up_event_id=event_id, content_object=content_obj, language=language)
            if event:
                return ShapeUpEventResponse.from_orm(event)

            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['get_shape_up_event'],
                        msg=f"Shape Up event not exist or was inactive"
                    )
                ]
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
        path='/event/',
        operation_id='get_shape_up_events',
        response={200: ShapeUpDeepInfoResponse, 409: ResponseError},
        auth=ProfileJWTAuth()
    )
    def get_shape_up_events(self):
        try:
            user_profile = self.context.request.auth
            content_obj = user_profile.content_object
            if not content_obj or (not isinstance(content_obj, Coach) and not isinstance(content_obj, Challenger)):
                return 401, ResponseError(
                    detail=[
                        DetailError(
                            loc=['get_shape_up_events'],
                            msg="Unauthorized"
                        )
                    ],
                    description='Unauthorized'
                )

            return get_deep_shape_up_info(
                content_object=content_obj,
                language=user_profile.get_content_language
            )

        except Exception as error:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['get_shape_up_events'],
                        msg=f"An error occurred getting shape up events info: ({error})"
                    )
                ]
            )

    @route.get(
        path='/event/authorized_cities/',
        operation_id='get_authorized_cities',
        response={200: List[ShapeUpCoachAuthorizedCityResponse], 409: ResponseError},
        auth=CoachJWTAuth()
    )
    def get_authorized_cities(self):
        try:
            coach = self.context.request.auth
            nemo = coach.user_profile.get_content_language.nemo
            response = []
            authorized_cities = ShapeUpCoachAuthorizedCity.objects.filter(
                coach=coach, active=True
            )
            for authorized_city in authorized_cities:
                country_name = get_country_name_from_city_by_lang(
                    city=authorized_city.city,
                    nemo=nemo
                )
                response.append(
                    ShapeUpCoachAuthorizedCityResponse(
                        city_id=authorized_city.city_id,
                        city_name=f'{authorized_city.city.name}, {country_name}'
                    )
                )
            return response

        except Exception as error:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['get_authorized_cities'],
                        msg=f"An error occurred getting authorized cities: ({error})"
                    )
                ]
            )

    @route.post(
        path='/authorization/',
        operation_id='send_authorization_request',
        response={200: ShapeUpAuthorizationResponse, 409: ResponseError},
        auth=CoachJWTAuth()
    )
    def send_authorization_request(self, payload: ShapeUpAuthorizationRequest):
        try:
            coach = self.context.request.auth
            profile = coach.user_profile

            if ShapeUpOrganizerCoachRequest.objects.filter(coach=coach, status='P').exists():
                return 409, ResponseError(
                    detail=[
                        DetailError(
                            loc=['send_authorization_request'],
                            msg="You already have a request in process"
                        )
                    ],
                    description='You already have a request in process'
                )

            if not payload.city or payload.city.strip() == "":
                return 409, ResponseError(
                    detail=[
                        DetailError(
                            loc=["send_authorization_request"],
                            msg="City is a required field"
                        )
                    ],
                    description="City is a required field"
                )

            organizer_request = ShapeUpOrganizerCoachRequest()
            organizer_request.city = payload.city.strip()
            organizer_request.coach = coach
            organizer_request.status = 'P'
            organizer_request.save()

            phone = (
                f"+{profile.phone_country_code}{profile.phone}" if profile.phone_country_code else f"{profile.phone}"
            )
            send_slack_notification(
                channel=settings.SLACK_AUTHORIZATION_REQUEST_CHANNEL,
                title=":rotating_light: New Authorization Request :rotating_light:",
                description=f"*By Coach:* {profile.user.first_name}",
                sections=[
                    f"*ID Herbalife:*\n{coach.id_herbalife}",
                    f"*Phone:*\n{phone if phone else ''}",
                    f"*City:*\n{payload.city.strip()}",
                    f"*Email:*\n{profile.user.email}"
                ]
            )

            return organizer_request

        except Exception as error:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['send_authorization_request'],
                        msg=f"An error occurred sending authorization request: ({error})"
                    )
                ]
            )

    @route.post(
        path="/event/",
        operation_id="create_shape_up_event",
        response={200: ShapeUpEventResponse, 409: ResponseError},
        auth=CoachJWTAuth()
    )
    def create_shape_up_event(self, payload: ShapeUpEventInput = Form(...), banner: UploadedFile = None):
        coach = self.context.request.auth
        language = coach.user_profile.get_content_language
        try:
            coach_authorized_city = ShapeUpCoachAuthorizedCity.objects.get(
                coach=coach, city_id=payload.city_id, active=True
            ).city
            if banner is None:
                general_config = get_general_config(language)
                banner = general_config.banner_template

            shape_up_event = ShapeUpEvent()
            shape_up_event.banner = banner
            shape_up_event.organizer_coach = coach
            shape_up_event.city = coach_authorized_city
            shape_up_event.start_time = convert_date_to_timezone(
                date=payload.start_time,
                from_tz=coach_authorized_city.time_zone,
                to_tz="UTC",
                output_format="%Y-%m-%d %H:%M:%S"
            )
            shape_up_event.end_time = convert_date_to_timezone(
                date=payload.end_time,
                from_tz=coach_authorized_city.time_zone,
                to_tz="UTC",
                output_format="%Y-%m-%d %H:%M:%S"
            )
            shape_up_event.title = payload.title
            shape_up_event.organizer_name = payload.organizer_name
            shape_up_event.address = payload.address
            shape_up_event.coach_price = payload.coach_price
            shape_up_event.guest_price = payload.guest_price
            shape_up_event.currency_acronym = payload.currency_acronym if payload.currency_acronym else "USD"
            shape_up_event.currency_symbol = payload.currency_symbol if payload.currency_symbol else "$"
            shape_up_event.about_event = payload.about_event
            shape_up_event.contact_email = payload.contact_email
            shape_up_event.contact_phone = payload.contact_phone
            shape_up_event.event_link = payload.event_link
            shape_up_event.active = True
            shape_up_event.save()
            shape_up_event.refresh_from_db()

            return ShapeUpEventResponse.from_orm(
                get_event(
                    shape_up_event_id=shape_up_event.id, content_object=coach, language=language
                )
            )

        except ShapeUpCoachAuthorizedCity.DoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["create_shape_up_event"],
                        msg="You not authorized to create event on this city",
                    )
                ],
                description="Bad Request",
            )

        except Exception as error:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['create_shape_up_event'],
                        msg=f"An error occurred creating shape up event: ({error})"
                    )
                ]
            )

    @route.put(
        path="/event/{event_id}",
        operation_id="update_shape_up_event",
        response={200: ShapeUpEventResponse, 409: ResponseError},
        auth=CoachJWTAuth()
    )
    def update_shape_up_event(self, event_id: int, payload: ShapeUpEventInput):
        coach = self.context.request.auth
        language = coach.user_profile.get_content_language
        try:
            shape_up_event = ShapeUpEvent.objects.get(id=event_id)
            coach_authorized_city = ShapeUpCoachAuthorizedCity.objects.get(
                coach=coach, city_id=payload.city_id, active=True
            ).city

            shape_up_event.city = coach_authorized_city
            shape_up_event.start_time = convert_date_to_timezone(
                date=payload.start_time,
                from_tz=coach_authorized_city.time_zone,
                to_tz="UTC",
                output_format="%Y-%m-%d %H:%M:%S"
            )
            shape_up_event.end_time = convert_date_to_timezone(
                date=payload.end_time,
                from_tz=coach_authorized_city.time_zone,
                to_tz="UTC",
                output_format="%Y-%m-%d %H:%M:%S"
            )
            shape_up_event.title = payload.title
            shape_up_event.organizer_name = payload.organizer_name
            shape_up_event.address = payload.address
            shape_up_event.coach_price = payload.coach_price
            shape_up_event.guest_price = payload.guest_price
            shape_up_event.currency_acronym = payload.currency_acronym if payload.currency_acronym else "USD"
            shape_up_event.currency_symbol = payload.currency_symbol if payload.currency_symbol else "$"
            shape_up_event.about_event = payload.about_event
            shape_up_event.contact_email = payload.contact_email
            shape_up_event.contact_phone = payload.contact_phone
            shape_up_event.event_link = payload.event_link
            shape_up_event.active = True
            shape_up_event.save()
            shape_up_event.refresh_from_db()

            return ShapeUpEventResponse.from_orm(
                get_event(
                    shape_up_event_id=shape_up_event.id, content_object=coach, language=language
                )
            )
        except ShapeUpEvent.DoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["update_shape_up_event"],
                        msg="Event not exist",
                    )
                ],
                description="Bad Request",
            )

        except ShapeUpCoachAuthorizedCity.DoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["update_shape_up_event"],
                        msg="You not authorized to create event on this city",
                    )
                ],
                description="Bad Request",
            )

        except Exception as error:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['update_shape_up_event'],
                        msg=f"An error occurred updating shape up event: ({error})"
                    )
                ]
            )

    @route.post(
        path="/event/banner/",
        operation_id="update_shape_up_event_banner",
        response={200: ShapeUpEventResponse, 409: ResponseError},
        auth=CoachJWTAuth()
    )
    def update_shape_up_event_banner(self, payload: ShapeUpEventBannerInput = Form(...), banner: UploadedFile = None):
        coach = self.context.request.auth
        language = coach.user_profile.get_content_language
        try:
            shape_up_event = ShapeUpEvent.objects.get(id=payload.event_id)
            if banner is None:
                general_config = get_general_config(language)
                banner = general_config.banner_template

            shape_up_event.banner = banner
            shape_up_event.save()
            shape_up_event.refresh_from_db()

            return ShapeUpEventResponse.from_orm(
                get_event(
                    shape_up_event_id=shape_up_event.id, content_object=coach, language=language
                )
            )
        except ShapeUpEvent.DoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=["update_shape_up_event_banner"],
                        msg="Event not exist",
                    )
                ],
                description="Bad Request",
            )

        except Exception as error:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['update_shape_up_event_banner'],
                        msg=f"An error occurred updating shape up event banner: ({error})"
                    )
                ]
            )

    @route.post(
        path="/priority_zone/",
        operation_id="update_shape_up_user_priority_zone",
        response={200: bool, 409: ResponseError},
        auth=ProfileJWTAuth()
    )
    def update_shape_up_user_priority_zone(self, payload: List[ShapeUpCitiesFilterInput]):
        user_profile = self.context.request.auth
        user = user_profile.user
        try:
            ShapeUpUserPriorityZone.objects.filter(user=user).update(active=False)
            for priority_zone in payload:
                if priority_zone.all_cities:
                    priority_zone, created = ShapeUpUserPriorityZone.objects.get_or_create(
                        user=user,
                        all_city=True,
                        country__isnull=True,
                        city__isnull=True
                    )
                else:
                    priority_zone, created = ShapeUpUserPriorityZone.objects.get_or_create(
                        user=user,
                        all_city=False,
                        country_id=priority_zone.country_id,
                        city_id=priority_zone.city_id
                    )
                priority_zone.active = True
                priority_zone.save()

            return True

        except Exception as error:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['update_shape_up_user_priority_zone'],
                        msg=f"An error occurred updating user priority zone: ({error})"
                    )
                ]
            )
