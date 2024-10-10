from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password

def authenticate_user(username, password):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return False

    return check_password(password, user.password)
def save_user(username, password):
    hashed_password = make_password(password)
    user = User(username=username, password=hashed_password)
    user.save()
    return user
