from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F, Q
from ninja_extra import (
    ControllerBase, api_controller, route
)
from wedo_core_service.models import (
    CoachChallenge, Challenge, PortalCoach, Component, PortalCoachSection, TrainingSubModule, ComponentTraining
)
from api.schemas.view_models import (
    ResponseError, DetailError, PortalCoachResponse, SectionResponse, FullComponentResponse, FullCalendarResponse,
    ResourceResponse, VideoResponse, ChatResponse, FullComponentTrainingResponse, VideoTrainingResponse,
    ResourceTrainingResponse, TrainingSubModuleResponse, TrainingModuleResponse, TrainingResponse, ImageDayResponse,
)
from api.services.calendar_events import get_calendar_event_list


@api_controller('portal_coach', tags=['Portal Coach'])
class PortalCoachController(ControllerBase):
    """
    Group functionalities to manage portal coach for coach
    """
    @route.get(
        path='get_portal_coach/{challenge_id}/',
        operation_id='get_portal_coach',
        response={200: PortalCoachResponse, 409: ResponseError}
    )
    def get_portal_coach(self, challenge_id: int):
        coach = self.context.request.auth

        try:
            coach_challenge = CoachChallenge.objects.get(
                challenge_id=challenge_id,
                coach=coach,
                status=True
            )
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['get portal coach'],
                        msg="Coach is not active for this challenge"
                    )
                ],
                description='Bad Request'
            )

        try:
            challenge = Challenge.objects.get(
                id=challenge_id
            )
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['get portal coach'],
                        msg="Challenge no exist"
                    )
                ],
                description='Bad Request'
            )

        language = coach_challenge.get_content_language

        try:
            portal_coach = PortalCoach.objects.get(
                challenge=challenge,
                language=language,
                is_active=True
            )
        except ObjectDoesNotExist:
            try:
                portal_coach = PortalCoach.objects.get(
                    challenge=challenge,
                    default=True,
                    is_active=True
                )
            except ObjectDoesNotExist:
                portal_coach = None

        if not portal_coach:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['get portal coach'],
                        msg="Portal Coach no exist or inactive"
                    )
                ],
                description='Bad Request'
            )

        portal_coach_sections = PortalCoachSection.objects.select_related(
            'section'
        ).filter(
            portal_coach=portal_coach,
            is_active=True
        ).annotate(
            name=F('section__name'),
            icon_code=F('section__icon_code')
        ).order_by('order')

        sections_responses = []
        for portal_coach_section in portal_coach_sections:
            components = Component.objects.filter(
                Q(section=portal_coach_section.section) &
                Q(is_active=True) &
                Q(
                    Q(is_visible_from_position__order__lte=coach.position.order) |
                    Q(is_visible_from_position__isnull=True)
                )
            ).order_by('order')
            component_responses = []
            for component in components:
                if component.content_type.model.upper() == 'CALENDAR':
                    events, original_events = get_calendar_event_list(component.content_object)
                    component_responses.append(
                        FullComponentResponse(
                            calendar=FullCalendarResponse(
                                show_list=component.content_object.show_list,
                                events=events,
                                original_events=list(original_events)
                            )
                        )
                    )
                elif component.content_type.model.upper() == 'RESOURCE':
                    component_responses.append(
                        FullComponentResponse(
                            resource=ResourceResponse.from_orm(component.content_object)
                        )
                    )
                elif component.content_type.model.upper() == 'VIDEO':
                    component_responses.append(
                        FullComponentResponse(
                            video=VideoResponse.from_orm(component.content_object)
                        )
                    )
                elif component.content_type.model.upper() == 'CHAT':
                    component_responses.append(
                        FullComponentResponse(
                            chat=ChatResponse.from_orm(component.content_object)
                        )
                    )
                elif component.content_type.model.upper() == 'IMAGEDAY':
                    component_responses.append(
                        FullComponentResponse(
                            image_day=ImageDayResponse.from_orm(component.content_object)
                        )
                    )
            if len(component_responses) > 0:
                sections_responses.append(
                    SectionResponse(
                        name=portal_coach_section.section.name,
                        order=portal_coach_section.order,
                        is_active=portal_coach_section.is_active,
                        icon_code=portal_coach_section.section.icon_code,
                        components=component_responses
                    )
                )

        training_submodules = TrainingSubModule.objects.prefetch_related(
            'training_module', 'training_module__training'
        ).filter(
            training_module__training__challenge=challenge,
            training_module__training__language=language,
            training_module__training__is_active=True
        ).order_by('training_module__training__order')

        if not training_submodules:
            training_submodules = TrainingSubModule.objects.prefetch_related(
                'training_module', 'training_module__training'
            ).filter(
                training_module__training__challenge=challenge,
                training_module__training__default=True,
                training_module__training__is_active=True
            ).order_by('training_module__training__order')

        training_responses = []
        training_module_responses = []
        training_submodule_responses = []

        current_training = None
        current_training_module = None
        count = 0
        total_submodules = len(training_submodules)
        for training_submodule in training_submodules:
            if current_training_module is None:
                current_training_module = training_submodule.training_module

            if current_training_module != training_submodule.training_module:
                training_module_responses.append(
                    TrainingModuleResponse(
                        title=current_training_module.title,
                        order=current_training_module.order,
                        is_active=current_training_module.is_active,
                        training_submodules=training_submodule_responses
                    )
                )
                training_submodule_responses = []
                current_training_module = training_submodule.training_module

            if current_training is None:
                current_training = current_training_module.training

            if current_training != current_training_module.training:
                training_responses.append(
                    TrainingResponse(
                        name=current_training.name,
                        author=current_training.author,
                        is_active=current_training.is_active,
                        order=current_training.order,
                        training_modules=training_module_responses
                    )
                )
                training_module_responses = []
                current_training = current_training_module.training

            components_training = ComponentTraining.objects.filter(
                training_submodule=training_submodule,
                is_active=True
            ).order_by('order')
            component_training_responses = []
            for component_training in components_training:
                if component_training.content_type.model.upper() == 'RESOURCETRAINING':
                    component_training_responses.append(
                        FullComponentTrainingResponse(
                            resource=ResourceTrainingResponse.from_orm(component_training.content_object)
                        )
                    )
                elif component_training.content_type.model.upper() == 'VIDEOTRAINING':
                    component_training_responses.append(
                        FullComponentTrainingResponse(
                            video=VideoTrainingResponse.from_orm(component_training.content_object)
                        )
                    )
            training_submodule_responses.append(
                TrainingSubModuleResponse(
                    title=training_submodule.title,
                    order=training_submodule.order,
                    is_active=training_submodule.is_active,
                    training_components=component_training_responses
                )
            )

            count += 1
            if count >= total_submodules:
                training_module_responses.append(
                    TrainingModuleResponse(
                        title=current_training_module.title,
                        order=current_training_module.order,
                        is_active=current_training_module.is_active,
                        training_submodules=training_submodule_responses
                    )
                )

                training_responses.append(
                    TrainingResponse(
                        name=current_training.name,
                        author=current_training.author,
                        is_active=current_training.is_active,
                        order=current_training.order,
                        training_modules=training_module_responses
                    )
                )

        return PortalCoachResponse(
            challenge=portal_coach.challenge_id,
            language=portal_coach.language,
            is_active=portal_coach.is_active,
            sections=sections_responses,
            trainings=training_responses
        )
