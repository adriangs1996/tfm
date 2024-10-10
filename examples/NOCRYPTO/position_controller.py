from typing import List

from django.core.exceptions import ObjectDoesNotExist
from ninja.constants import NOT_SET
from ninja_extra import ControllerBase, api_controller, route
from wedo_core_service.models import Position

from api.schemas.view_models import ResponseError, PositionResponse, DetailError


@api_controller('position', tags=['Position'], auth=NOT_SET)
class PositionController(ControllerBase):
    """
    Group functionalities to position model
    """
    @route.get(
        path='get_positions',
        response={200: List[PositionResponse]},
        operation_id='get_positions',
        auth=None
    )
    def list_positions(self):
        """
        Get list of positions.
        """
        return Position.objects.all()

    @route.get(
        path='get_position/{position_id}',
        response={200: PositionResponse, 409: ResponseError},
        operation_id='get_position',
        auth=None
    )
    def get_position(self, position_id: int):
        """
        Get position.
        """
        try:
            return Position.objects.get(id=position_id)
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(loc=['position_id'], msg='Not Found')
                ],
                description='Position not found',
                code=409
            )

    @route.get(
        path='get_position_by_mnemonic/{mnemonic}',
        response={200: PositionResponse, 409: ResponseError},
        operation_id='get_position_by_mnemonic',
        auth=None
    )
    def get_position_by_mnemonic(self, mnemonic: str):
        """
        Get position.
        """
        try:
            return Position.objects.get(mnemonic=mnemonic)
        except ObjectDoesNotExist:
            return 409, ResponseError(
                detail=[
                    DetailError(loc=['mnemonic'], msg='Not Found')
                ],
                description='Position not found',
                code="404"
            )
