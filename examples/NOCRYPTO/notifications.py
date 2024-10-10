import requests
from django.conf import settings


def send_notification(registration_token: str, title: str, body: str, object_id: str, context: str):
    url = f'{settings.NOTIFICATIONS_HOST}/notifications/api/v1/notification/send_notification'
    payload = {
        "registration_token": registration_token,
        "title": title,
        "body": body,
        "object_id": object_id,
        "context": context
    }
    return requests.post(url=url, json=payload)


def send_slack_notification(channel: str, title: str, description: str, sections: [str]):
    url = f'{settings.NOTIFICATIONS_HOST}/notifications/api/v1/notification/send_slack_notification'
    payload = {
        "channel": channel,
        "title": title,
        "description": description,
        "sections": sections
    }
    return requests.post(url=url, json=payload)
