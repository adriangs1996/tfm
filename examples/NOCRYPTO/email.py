import requests
from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext as _
from django.template.loader import get_template


def send_email(email, payload):
    url = f'{settings.EMAIL_HOST}/email/api/v1/email/send_email_many_recipients'
    response = None
    session = requests.Session()
    for _unused in range(5):
        print(f"sending email to {email}")
        try:
            response = session.post(url=url, json=payload, timeout=10)
        except Exception as e:
            print(f"failed to send email to {email} with error {e}")
            continue
        if response.status_code == 200:
            break
        else:
            print(f"failed to send email to {email} with status code {response.status_code}")
    session.close()
    return response


def send_challenger_invitation_email(email, invitation_id, coach_name, language_nemo):
    translation.activate(language_nemo)
    template = "emails/invitation_email.html"
    context = {
        "ms_host": settings.MS_HOST,
        "invitation_id": invitation_id,
        "message": f'{coach_name} {_("has invited you to join WeDoTransformations personal transformation challenge")}',
        "download_message": _("download the app to join"),
        "language_nemo": language_nemo
    }
    payload = {
        "title": _("you have a new invitation"),
        "to_email": email,
        "body_html": get_template(template).render(context)
    }
    response = send_email(email, payload)
    translation.deactivate()
    if response and response.status_code == 200:
        return True
    return False
