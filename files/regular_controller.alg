
import datetime
from typing import List, Optional
from django.db import transaction

from django.db.models import Max, Value
from django.db.models.functions import Coalesce
from ninja import Schema, UploadedFile
from api.services import component as component_service
from wedo_core_service.models import (
    ChallengeCalendar,
    ChallengeCalendarEvent,
    ChallengeCalendarEventContent,
    ChallengeComponent,
    ChallengeGroup,
    ChallengeImage,
    ChallengeImageContent,
    ChallengeImageRecipe,
    ChallengeImageRecipeContent,
    ChallengeLink,
    ChallengeLinkContent,
    ChallengeResource,
    ChallengeResourceContent,
    ChallengeVideo,
    ChallengeVideoContent,
    ChallengeWorkoutVideo,
    ChallengeWorkoutVideoContent,
    VimeoToken, ChallengeVideoRecipe, ChallengeVideoRecipeContent, ChallengeCourseVideo, ChallengeCourseVideoContent,
    ChallengeCourseResource, ChallengeCourseResourceContent,
)


class ComponentMetadata(Schema):
    is_active: bool
    is_visible_from_position_id: Optional[int] = None
    visible_by: str = "ALL"
    order: Optional[int] = None


class EventContent(Schema):
    id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    language_id: Optional[int] = None
    default = False


class EventData(Schema):
    id: Optional[int] = None
    date: Optional[datetime.date] = None
    hour: Optional[datetime.time] = None
    is_visible_from_position_id: Optional[int] = None
    visible_by: str = "ALL"
    event_content: Optional[List[EventContent]] = None


class ResourceData(Schema):
    id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    cover: Optional[UploadedFile] = None
    file: Optional[UploadedFile] = None
    link: Optional[str] = None
    language_id: Optional[int] = None
    default: bool = False
    is_downloadable: bool = False


class ImageData(Schema):
    id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    language_id: Optional[int] = None
    default: bool = False
    file: Optional[UploadedFile] = None
    link: Optional[str] = None
    is_downloadable: bool = False


class VideoData(Schema):
    id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    language_id: Optional[int] = None
    default: bool = False
    link: Optional[str] = None
    file: Optional[UploadedFile] = None
    type: Optional[str] = None
    vimeo_token: Optional[str] = None
    is_downloadable: bool = False


class WorkoutData(Schema):
    id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    language_id: Optional[int] = None
    default: bool = False
    link: Optional[str] = None
    file: Optional[UploadedFile] = None
    type: Optional[str] = None
    vimeo_token: Optional[str] = None


class CourseVideoData(Schema):
    id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    language_id: Optional[int] = None
    default: bool = False
    link: Optional[str] = None
    file: Optional[UploadedFile] = None
    type: Optional[str] = None
    vimeo_token: Optional[str] = None


class CourseResourceData(Schema):
    id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    language_id: Optional[int] = None
    default: bool = False
    link: Optional[str] = None
    file: Optional[UploadedFile] = None


class VideoRecipeData(Schema):
    id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    language_id: Optional[int] = None
    default: bool = False
    link: Optional[str] = None
    file: Optional[UploadedFile] = None
    type: Optional[str] = None
    vimeo_token: Optional[str] = None
    preparation: Optional[str] = None
    ingredients: Optional[str] = None
    nutritional_information: Optional[str] = None


class ImageRecipeData(Schema):
    id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    language_id: Optional[int] = None
    default: bool = False
    image: Optional[UploadedFile] = None
    preparation: Optional[str] = None
    ingredients: Optional[str] = None
    nutritional_information: Optional[str] = None


class LinkData(Schema):
    language_id: int
    id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    link: Optional[str] = None
    default: bool = False
    cover: Optional[UploadedFile] = None


class ComponentContent(Schema):
    events: Optional[List[EventData]] = None
    resources: Optional[List[ResourceData]] = None
    images: Optional[List[ImageData]] = None
    videos: Optional[List[VideoData]] = None
    workouts: Optional[List[WorkoutData]] = None
    course_videos: Optional[List[CourseVideoData]] = None
    course_resources: Optional[List[CourseResourceData]] = None
    video_recipes: Optional[List[VideoRecipeData]] = None
    image_recipes: Optional[List[ImageRecipeData]] = None
    link: Optional[List[LinkData]] = None


def sync_component_content(component_parent, content_set_attr, components_present):
    for obj in getattr(component_parent, content_set_attr).all():
        if obj.id not in components_present:
            obj.delete()


class GenerateComponentCommand(Schema):
    challenge_group_id: int
    component_type: str
    object_id: int
    metadata: ComponentMetadata
    id: Optional[int] = None
    contents: Optional[ComponentContent] = None
    accepts_progress: Optional[bool] = None

    def handle(self):
        with transaction.atomic():
            if not self._exists_challenge_group():
                raise ValueError("Challenge group not found")
            component = self._component()
            if component is None:
                raise ValueError("Component not found")
            component.save()

            if self.component_type == "challenge_calendar":
                component.content_object = self._calendar_component(component)
            elif self.component_type == "challenge_resource":
                component.content_object = self._resource_component(component)
            elif self.component_type == "challenge_image":
                component.content_object = self._image_component(component)
            elif self.component_type == "challenge_video":
                component.content_object = self._video_component(component)
            elif self.component_type == "challenge_workout_video":
                component.content_object = self._workout_component(component)
            elif self.component_type == "challenge_course_video":
                component.content_object = self._course_video_component(component)
            elif self.component_type == "challenge_course_resource":
                component.content_object = self._course_resource_component(component)
            elif self.component_type == "challenge_video_recipe":
                component.content_object = self._video_recipe_component(component)
            elif self.component_type == "challenge_image_recipe":
                component.content_object = self._image_recipe_component(component)
            elif self.component_type == "link":
                component.content_object = self._link_component(component)
            else:
                raise ValueError("Component type is not valid")
            component.save()

        return component

    def _link_component(self, component: ChallengeComponent):
        link = (
                ChallengeLink.objects.filter(challenge_component=component).first()
                or ChallengeLink.objects.create()
        )
        if self.contents is not None and self.contents.link is not None:
            link_ids = [link_data.id if link_data.id is not None else -1 for link_data in self.contents.link]
            sync_component_content(link, "challengelinkcontent_set", link_ids)
            for link_data in self.contents.link:
                if link_data.id is not None:
                    try:
                        link_content = ChallengeLinkContent.objects.get(id=link_data.id)
                        link_content.title = link_data.title or link_content.title
                        link_content.description = link_data.description
                        link_content.language_id = (  # type: ignore
                                link_data.language_id or link_content.language_id  # type: ignore
                        )
                        link_content.default = (
                            link_data.default
                            if link_data.default is not None
                            else link_content.default
                        )
                        link_content.link = link_data.link or link_content.link
                        link_content.save()
                    except ChallengeLinkContent.DoesNotExist:
                        raise ValueError("Link content not found")
                else:
                    link_content = ChallengeLinkContent.objects.create(
                        challenge_link=link,
                        title=link_data.title,
                        description=link_data.description,
                        language_id=link_data.language_id,
                        default=link_data.default or False,
                        link=link_data.link,
                        cover=link_data.cover,
                    )
        return link

    def _resource_component(self, component: ChallengeComponent):
        resource = (
                ChallengeResource.objects.filter(challenge_component=component).first()
                or ChallengeResource.objects.create()
        )
        if self.contents is not None and self.contents.resources is not None:
            resource_content_ids = [resource_data.id if resource_data.id is not None else -1 for resource_data in
                                    self.contents.resources]
            sync_component_content(resource, "challengeresourcecontent_set", resource_content_ids)
            for resource_data in self.contents.resources:
                if any(r.is_downloadable for r in self.contents.resources):
                    resource.is_downloadable = True
                if resource_data.id is not None:
                    try:
                        resource_content = ChallengeResourceContent.objects.get(
                            id=resource_data.id
                        )
                        resource_content.title = (
                                resource_data.title or resource_content.title
                        )
                        resource_content.description = resource_data.description
                        resource_content.language_id = (  # type: ignore
                                resource_data.language_id or resource_content.language_id  # type: ignore
                        )
                        resource_content.default = (
                            resource_data.default
                            if resource_data.default is not None
                            else resource_content.default
                        )
                        resource_content.link = (
                                resource_data.link or resource_content.link
                        )
                        if resource_data.link is not None:
                            resource_content.file = None
                        resource_content.save()
                    except ChallengeImageContent.DoesNotExist:
                        raise ValueError("Image content not found")
                else:
                    resource_content = ChallengeResourceContent.objects.create(
                        challenge_resource=resource,
                        title=resource_data.title,
                        description=resource_data.description,
                        language_id=resource_data.language_id,
                        default=resource_data.default or False,
                        link=resource_data.link,
                    )
        return resource

    def _image_component(self, component: ChallengeComponent):
        image = (
                ChallengeImage.objects.filter(challenge_component=component).first()
                or ChallengeImage.objects.create()
        )
        if self.contents is not None and self.contents.images is not None:
            image_ids = [image_data.id if image_data.id is not None else -1 for image_data in self.contents.images]
            sync_component_content(image, "challengeimagecontent_set", image_ids)
            for image_data in self.contents.images:
                if any(i.is_downloadable for i in self.contents.images):
                    image.is_downloadable = True
                if image_data.id is not None:
                    try:
                        image_content = ChallengeImageContent.objects.get(
                            id=image_data.id
                        )
                        image_content.title = image_data.title or image_content.title
                        image_content.description = image_data.description
                        image_content.language_id = (  # type: ignore
                                image_data.language_id or image_content.language_id  # type: ignore
                        )
                        image_content.default = (
                            image_data.default
                            if image_data.default is not None
                            else image_content.default
                        )
                        image_content.link = image_data.link or image_content.link
                        if image_data.link is not None:
                            image_content.file = None
                        image_content.save()
                    except ChallengeImageContent.DoesNotExist:
                        raise ValueError("Image content not found")
                else:
                    image_content = ChallengeImageContent.objects.create(
                        challenge_image=image,
                        title=image_data.title,
                        description=image_data.description,
                        language_id=image_data.language_id,
                        default=image_data.default or False,
                        link=image_data.link,
                    )
        return image

    def _image_recipe_component(self, component: ChallengeComponent):
        image = (
                ChallengeImageRecipe.objects.filter(challenge_component=component).first()
                or ChallengeImageRecipe.objects.create()
        )

        if self.contents is not None and self.contents.image_recipes is not None:
            image_recipe_ids = [image_data.id if image_data.id is not None else -1 for image_data in
                                self.contents.image_recipes]
            sync_component_content(image, "challengeimagerecipecontent_set", image_recipe_ids)
            for image_data in self.contents.image_recipes:
                if image_data.id is not None:
                    try:
                        image_content = ChallengeImageRecipeContent.objects.get(
                            id=image_data.id
                        )
                        image_content.title = image_data.title or image_content.title
                        image_content.description = image_data.description
                        image_content.language_id = (  # type: ignore
                                image_data.language_id or image_content.language_id  # type: ignore
                        )
                        image_content.default = (
                            image_data.default
                            if image_data.default is not None
                            else image_content.default
                        )
                        image_content.ingredients = image_data.ingredients
                        image_content.nutritional_information = image_data.nutritional_information
                        image_content.preparation = image_data.preparation
                        image_content.save()

                    except ChallengeImageContent.DoesNotExist:
                        raise ValueError("Image content not found")
                else:
                    image_content = ChallengeImageRecipeContent.objects.create(
                        challenge_image_recipe=image,
                        title=image_data.title,
                        description=image_data.description,
                        language_id=image_data.language_id,
                        default=image_data.default or False,
                        ingredients=image_data.ingredients,
                        nutritional_information=image_data.nutritional_information,
                        preparation=image_data.preparation,
                    )
        return image

    def _video_recipe_component(self, component: ChallengeComponent):
        video = (
                ChallengeVideoRecipe.objects.filter(challenge_component=component).first()
                or ChallengeVideoRecipe.objects.create()
        )

        if self.contents is not None and self.contents.video_recipes is not None:
            video_recipe_ids = [video_data.id if video_data.id is not None else -1 for video_data in
                                self.contents.video_recipes]
            sync_component_content(video, "challengevideorecipecontent_set", video_recipe_ids)
            for video_data in self.contents.video_recipes:
                if video_data.id is not None:
                    try:
                        video_content = ChallengeVideoRecipeContent.objects.get(
                            id=video_data.id
                        )
                        video_content.title = video_data.title or video_content.title
                        video_content.description = video_data.description
                        video_content.language_id = (  # type: ignore
                                video_data.language_id or video_content.language_id  # type: ignore
                        )
                        video_content.default = (
                            video_data.default
                            if video_data.default is not None
                            else video_content.default
                        )
                        video_content.link = video_data.link or video_content.link
                        if video_data.link is not None:
                            video_content.file = None
                        video_content.type = video_data.type or video_content.type
                        if video_data.vimeo_token:
                            video_content.vimeo_token = VimeoToken.objects.filter(token=video_data.vimeo_token).first()

                        video_content.ingredients = video_data.ingredients
                        video_content.nutritional_information = video_data.nutritional_information
                        video_content.preparation = video_data.preparation
                        video_content.save()

                    except ChallengeVideoRecipeContent.DoesNotExist:
                        raise ValueError("Video content not found")
                else:
                    vimeo_token = None
                    if video_data.vimeo_token:
                        vimeo_token = VimeoToken.objects.filter(token=video_data.vimeo_token).first()

                    video_content = ChallengeVideoRecipeContent.objects.create(
                        challenge_video_recipe=video,
                        title=video_data.title,
                        description=video_data.description,
                        link=video_data.link,
                        type=video_data.type,
                        language_id=video_data.language_id,
                        default=video_data.default or False,
                        ingredients=video_data.ingredients,
                        nutritional_information=video_data.nutritional_information,
                        preparation=video_data.preparation,
                        vimeo_token=vimeo_token
                    )

        return video

    def _course_resource_component(self, component: ChallengeComponent):
        resource = (
                ChallengeCourseResource.objects.filter(challenge_component=component).first()
                or ChallengeCourseResource.objects.create()
        )

        if self.contents is not None and self.contents.course_resources is not None:
            resource_ids = [resource_data.id if resource_data.id is not None else -1 for resource_data in
                            self.contents.course_resources]
            sync_component_content(resource, "challengecourseresourcecontent_set", resource_ids)
            for resource_data in self.contents.course_resources:
                if resource_data.id is not None:
                    try:
                        resource_content = ChallengeCourseResourceContent.objects.get(
                            id=resource_data.id
                        )
                        resource_content.title = resource_data.title or resource_content.title
                        resource_content.description = resource_data.description
                        resource_content.language_id = (  # type: ignore
                                image_data.language_id or resource_content.language_id  # type: ignore
                        )
                        resource_content.default = (
                            resource_data.default
                            if resource_data.default is not None
                            else resource_content.default
                        )
                        resource_content.link = resource_data.link or resource_content.link
                        if resource_data.link is not None:
                            resource_content.file = None
                        resource_content.save()

                    except ChallengeImageContent.DoesNotExist:
                        raise ValueError("Image content not found")
                else:
                    resource_content = ChallengeCourseResourceContent.objects.create(
                        challenge_video=resource,
                        title=resource_data.title,
                        description=resource_data.description,
                        language_id=resource_data.language_id,
                        default=resource_data.default or False,
                        link=resource_data.link,
                    )
        return resource

    def _course_video_component(self, component: ChallengeComponent):
        video = (
                ChallengeCourseVideo.objects.filter(challenge_component=component).first()
                or ChallengeCourseVideo.objects.create()
        )

        if self.contents is not None and self.contents.course_videos is not None:
            video_ids = [video_data.id if video_data.id is not None else -1 for video_data in
                         self.contents.course_videos]
            sync_component_content(video, "challengecoursevideocontent_set", video_ids)
            for video_data in self.contents.course_videos:
                if video_data.id is not None:
                    try:
                        video_content = ChallengeCourseVideoContent.objects.get(
                            id=video_data.id
                        )
                        video_content.title = video_data.title or video_content.title
                        video_content.description = video_data.description
                        video_content.language_id = (  # type: ignore
                                image_data.language_id or video_content.language_id  # type: ignore
                        )
                        video_content.default = (
                            video_data.default
                            if video_data.default is not None
                            else video_content.default
                        )
                        video_content.link = video_data.link or video_content.link
                        if video_data.link is not None:
                            video_content.file = None
                        video_content.type = video_data.type or video_content.type
                        if video_data.vimeo_token:
                            video_content.vimeo_token = VimeoToken.objects.filter(token=video_data.vimeo_token).first()

                        video_content.save()

                    except ChallengeImageContent.DoesNotExist:
                        raise ValueError("Image content not found")
                else:
                    vimeo_token = None
                    if video_data.vimeo_token:
                        vimeo_token = VimeoToken.objects.filter(token=video_data.vimeo_token).first()

                    video_content = ChallengeCourseVideoContent.objects.create(
                        challenge_video=video,
                        title=video_data.title,
                        description=video_data.description,
                        language_id=video_data.language_id,
                        default=video_data.default or False,
                        link=video_data.link,
                        type=video_data.type,
                        vimeo_token=vimeo_token
                    )

        return video

    def _workout_component(self, component: ChallengeComponent):
        video = (
                ChallengeWorkoutVideo.objects.filter(challenge_component=component).first()
                or ChallengeWorkoutVideo.objects.create()
        )
        if self.contents is not None and self.contents.workouts is not None:
            video_ids = [video_data.id if video_data.id is not None else -1 for video_data in self.contents.workouts]
            sync_component_content(video, "challengeworkoutvideocontent_set", video_ids)
            for video_data in self.contents.workouts:
                if video_data.id is not None:
                    try:
                        video_content = ChallengeWorkoutVideoContent.objects.get(
                            id=video_data.id, challenge_workout_video=video
                        )
                        video_content.title = video_data.title or video_content.title
                        video_content.description = video_data.description
                        video_content.language_id = (  # type: ignore
                                video_data.language_id or video_content.language_id  # type: ignore
                        )
                        video_content.default = (
                            video_data.default
                            if video_data.default is not None
                            else video_content.default
                        )
                        video_content.link = video_data.link or video_content.link
                        if video_data.link is not None:
                            video_content.file = None
                        video_content.type = video_data.type or video_content.type
                        if video_data.vimeo_token is not None:
                            video_content.vimeo_token = VimeoToken.objects.filter(token=video_data.vimeo_token).first()
                        video_content.save()
                    except ChallengeWorkoutVideoContent.DoesNotExist:
                        raise ValueError("Workout Video content not found")
                else:
                    vimeo_token = None
                    if video_data.vimeo_token is not None:
                        vimeo_token = VimeoToken.objects.filter(token=video_data.vimeo_token).first()

                    video_content = ChallengeWorkoutVideoContent.objects.create(
                        challenge_workout_video=video,
                        title=video_data.title,
                        description=video_data.description,
                        language_id=video_data.language_id,
                        default=video_data.default or False,
                        link=video_data.link,
                        type=video_data.type,
                        vimeo_token=vimeo_token
                    )

        return video

    def _video_component(self, component: ChallengeComponent):
        video = (
                ChallengeVideo.objects.filter(challenge_component=component).first()
                or ChallengeVideo.objects.create()
        )
        if self.contents is not None and self.contents.videos is not None:
            video_ids = [video_data.id if video_data.id is not None else -1 for video_data in self.contents.videos]
            sync_component_content(video, "challengevideocontent_set", video_ids)
            for video_data in self.contents.videos:
                if any(v.is_downloadable for v in self.contents.videos):
                    video.is_downloadable = True
                if video_data.id is not None:
                    try:
                        video_content = ChallengeVideoContent.objects.get(
                            id=video_data.id, challenge_video=video
                        )
                        video_content.title = video_data.title or video_content.title
                        video_content.description = video_data.description
                        video_content.language_id = (  # type: ignore
                                video_data.language_id or video_content.language_id  # type: ignore
                        )
                        video_content.default = (
                            video_data.default
                            if video_data.default is not None
                            else video_content.default
                        )
                        video_content.link = video_data.link or video_content.link
                        if video_data.link is not None:
                            video_content.file = None
                        video_content.type = video_data.type or video_content.type
                        if video_data.vimeo_token is not None:
                            video_content.vimeo_token = VimeoToken.objects.filter(token=video_data.vimeo_token).first()

                        video_content.save()
                    except ChallengeVideoContent.DoesNotExist:
                        raise ValueError("Video content not found")

                else:
                    vimeo_token = None
                    if video_data.vimeo_token is not None:
                        vimeo_token = VimeoToken.objects.filter(token=video_data.vimeo_token).first()

                    video_content = ChallengeVideoContent.objects.create(
                        challenge_video=video,
                        title=video_data.title,
                        description=video_data.description,
                        language_id=video_data.language_id,
                        default=video_data.default or False,
                        link=video_data.link,
                        type=video_data.type,
                        vimeo_token=vimeo_token
                    )

        return video

    def _calendar_component(self, component: ChallengeComponent):
        calendar = (
                ChallengeCalendar.objects.filter(challenge_component=component).first()
                or ChallengeCalendar.objects.create()
        )

        if self.contents is not None and self.contents.events is not None:
            event_ids = [event_data.id if event_data.id is not None else -1 for event_data in self.contents.events]
            sync_component_content(calendar, "challengecalendarevent_set", event_ids)
            for event_data in self.contents.events:
                if event_data.id is not None:
                    try:
                        event = ChallengeCalendarEvent.objects.get(id=event_data.id)
                        event.date = event_data.date or event.date
                        event.hour = event_data.hour or event.hour
                        event.is_visible_from_position_id = event_data.is_visible_from_position_id
                        event.visible_by = event_data.visible_by or event.visible_by
                        event.save()
                    except ChallengeCalendarEvent.DoesNotExist:
                        raise ValueError("Event not found")
                else:
                    event = ChallengeCalendarEvent.objects.create(
                        challenge_calendar=calendar,
                        date=event_data.date,
                        hour=event_data.hour,
                        is_visible_from_position_id=event_data.is_visible_from_position_id,
                        visible_by=event_data.visible_by,
                    )

                if event_data.event_content is not None:
                    event_content_ids = [event_content_data.id if event_content_data.id is not None else -1 for
                                         event_content_data in event_data.event_content]
                    sync_component_content(event, "challengecalendareventcontent_set", event_content_ids)
                    for event_content_data in event_data.event_content:
                        if event_content_data.id is not None:
                            try:
                                event_content = (
                                    ChallengeCalendarEventContent.objects.get(
                                        id=event_content_data.id
                                    )
                                )
                                event_content.title = (
                                        event_content_data.title or event_content.title
                                )
                                event_content.description = event_content_data.description
                                event_content.language_id = (  # type: ignore
                                        event_content_data.language_id
                                        or event_content.language_id  # type: ignore
                                )
                                event_content.default = (
                                    event_content_data.default
                                    if event_content_data.default is not None
                                    else event_content.default
                                )
                                event_content.save()
                            except ChallengeCalendarEventContent.DoesNotExist:
                                raise ValueError("Event content not found")
                        else:
                            ChallengeCalendarEventContent.objects.create(
                                challenge_calendar_event=event,
                                title=event_content_data.title,
                                description=event_content_data.description,
                                language_id=event_content_data.language_id,
                                default=event_content_data.default,
                            )
        return calendar

    def _exists_challenge_group(self):
        return ChallengeGroup.objects.filter(id=self.challenge_group_id).exists()

    def _component(self):
        component = None
        if self.id is None:
            component = ChallengeComponent(
                # I need to create the component first, then I can create the content.
                # Put the object_id as 999999999 but it will be updated when the content is created
                challenge_group_id=self.challenge_group_id, object_id=999999999
            )
            if self.metadata.order is None:
                component_max = ChallengeComponent.objects.filter(
                    challenge_group_id=self.challenge_group_id
                ).aggregate(max_order=Coalesce(Max("order"), Value(0)))["max_order"]
                component.order = component_max + 1
            else:
                component_service.forward_order_challenge_components(self.challenge_group_id, self.metadata.order)
                component.order = self.metadata.order
            component.is_active = self.metadata.is_active or True
            component.is_visible_from_position_id = (  # type: ignore
                self.metadata.is_visible_from_position_id
            )
            component.visible_by = self.metadata.visible_by if self.metadata.visible_by is not None else component.visible_by
            component.accept_progress = self.accepts_progress if self.accepts_progress is not None else component.accept_progress
        else:
            try:
                component = ChallengeComponent.objects.get(
                    id=self.id, challenge_group_id=self.challenge_group_id
                )
                component.visible_by = self.metadata.visible_by if self.metadata.visible_by is not None else component.visible_by
                component.order = self.metadata.order or component.order
                component.is_active = (
                    self.metadata.is_active
                    if self.metadata.is_active is not None
                    else component.is_active
                )

                component.is_visible_from_position_id = (
                    self.metadata.is_visible_from_position_id
                    if component.visible_by in ['COACH']
                    else None
                )

                component.accept_progress = self.accepts_progress if self.accepts_progress is not None else component.accept_progress
            except ChallengeComponent.DoesNotExist:
                pass
        return component
