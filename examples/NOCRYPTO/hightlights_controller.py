import datetime
from typing import List

from django.db.models import Q, OuterRef, Exists
from ninja_extra import api_controller, ControllerBase, route
from wedo_core_service.models import (
    Coach, Challenger, HighlightImageContent, HighlightComponent, UserViewedHighlightComponent,
)
from wedo_core_service.services.auth import ProfileJWTAuth

from api.schemas.view_models import (
    ResponseError, DetailError, HighlightContentResponse, HighlightComponentResponseSchema,
    UserViewedHighlightComponentResponseV2, UserViewedHighlightComponentInputV2,
)
from api.services.highlight import get_all_highlights


@api_controller("highlight", tags=["Highlight"])
class HighlightController(ControllerBase):
    """
    Group functionalities to Highlight model
    """

    @route.get(
        path="all",
        operation_id="all",
        response={200: List[HighlightContentResponse], 409: ResponseError},
        auth=ProfileJWTAuth()
    )
    def all(self):
        user_profile = self.context.request.auth
        language = user_profile.get_content_language
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

        return get_all_highlights(content_object=content_object, language=language)

    @route.get(
        path="content/{highlight_id}",
        operation_id="content",
        response={200: List[HighlightComponentResponseSchema], 409: ResponseError},
        auth=ProfileJWTAuth()
    )
    def content(self, highlight_id):
        user_profile = self.context.request.auth
        user = user_profile.user
        content_object = user_profile.content_object

        if not content_object or (
                not isinstance(content_object, Coach) and not isinstance(content_object, Challenger)
        ):
            return 401, ResponseError(
                detail=[
                    DetailError(
                        loc=['highlight_content'],
                        msg="Unauthorized"
                    )
                ],
                description='Unauthorized'
            )

        language = user_profile.get_content_language
        now = datetime.datetime.utcnow()

        components = []
        query = Q(highlight_id=highlight_id) & \
                Q(highlight__is_active=True) & \
                Q(start__lte=now) & \
                Q(end__gt=now) & \
                Q(is_active=True)

        if isinstance(content_object, Coach):
            position = content_object.position
            query &= Q(highlight__visible_by__in=['ALL', 'COACH'])
            query &= (
                    Q(highlight__is_visible_from_position__order__lte=position.order) |
                    Q(highlight__is_visible_from_position__isnull=True)
            )
            query &= (
                    Q(is_visible_from_position__order__lte=position.order) |
                    Q(is_visible_from_position__isnull=True)
            )
            query &= Q(visible_by__in=['ALL', 'COACH'])

        if isinstance(content_object, Challenger):
            query &= Q(highlight__visible_by__in=['ALL', 'CHALLENGER'])
            query &= Q(highlight__is_visible_from_position__isnull=True)
            query &= Q(is_visible_from_position__isnull=True)
            query &= Q(visible_by__in=['ALL', 'CHALLENGER'])

        exists_subquery = UserViewedHighlightComponent.objects.filter(
            user=user,
            highlight_component_id=OuterRef('id'),
            viewed=True
        )

        result = HighlightComponent.objects.prefetch_related(
            'userviewedhighlightcomponent_set'
        ).filter(
            query
        ).annotate(
            viewed=Exists(
                exists_subquery
            )
        ).order_by('order')

        for item in result:

            if item.content_type.model.upper() == 'HIGHLIGHTIMAGE':
                image = HighlightImageContent.objects.select_related(
                    'highlight_image'
                ).filter(
                    Q(highlight_image=item.content_object) &
                    (
                        Q(language=language) |
                        Q(default=True)
                    )
                ).order_by('default').first()

                if image:
                    components.append(HighlightComponentResponseSchema(highlight_component=item, image=image))

        return components

    @route.post(
        path="/viewed_highlight_component/",
        operation_id="set_viewed_highlight_component",
        response={200: UserViewedHighlightComponentResponseV2, 409: ResponseError},
        auth=ProfileJWTAuth()
    )
    def set_viewed_highlight_component(self, payload: UserViewedHighlightComponentInputV2):
        try:
            user_profile = self.context.request.auth
            try:
                highlight_component = HighlightComponent.objects.get(id=payload.highlight_component_id)
            except HighlightComponent.DoesNotExist:
                return 409, ResponseError(
                    detail=[
                        DetailError(
                            loc=["set_viewed_highlight_component"],
                            msg="highlight component not exist",
                        )
                    ],
                    description="Bad Request",
                )
            try:
                user_viewed_highlight_component = UserViewedHighlightComponent.objects.get(
                    user=user_profile.user, highlight_component=highlight_component
                )
            except UserViewedHighlightComponent.DoesNotExist:
                user_viewed_highlight_component = UserViewedHighlightComponent()
                user_viewed_highlight_component.user = user_profile.user
                user_viewed_highlight_component.highlight_component = highlight_component

            user_viewed_highlight_component.viewed = payload.viewed
            user_viewed_highlight_component.save()

            return user_viewed_highlight_component
        except Exception as error:
            return 409, ResponseError(
                detail=[
                    DetailError(
                        loc=['set_viewed_highlight_component'],
                        msg=f"An error occurred set_viewed_highlight_component: ({error})"
                    )
                ]
            )
