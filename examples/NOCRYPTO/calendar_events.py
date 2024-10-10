import datetime
from copy import copy
from wedo_core_service.models import CalendarEvent
from api.schemas.view_models import CalendarEventResponse


def get_calendar_event_list(calendar):
    events = CalendarEvent.objects.filter(
        calendar=calendar
    ).order_by('date')
    event_list = []
    for event in events:
        if event.mark_all_days_range:
            event_ = copy(event)
            for i in range(0, (event.date_end-event.date).days + 1):
                event_.date = event.date + datetime.timedelta(i)
                event_list.append(CalendarEventResponse.from_orm(event_))
        elif event.date_end:
            event_ = copy(event)
            event_.date = event.date_end
            event_.hour = event.hour_end
            event_list.append(CalendarEventResponse.from_orm(event))
            event_list.append(CalendarEventResponse.from_orm(event_))
        else:
            event_list.append(event)
    event_list.sort(key=lambda x: x.date, reverse=False)
    return event_list, events
