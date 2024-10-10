import requests


def verify_is_coach(url_base, email):
    url = f'{url_base}/coach/is_valid_coach/{email}'

    response = requests.get(url)

    if not response.status_code == 200:
        return False

    return True if response.text == 'true' else False


def verify_active_coach(url_base, email, month, year):
    url = f'{url_base}/coach/is_active_coach/{email}/{month}/{year}'

    response = requests.get(url)

    if not response.status_code == 200:
        return False

    return True if response.text == 'true' else False
