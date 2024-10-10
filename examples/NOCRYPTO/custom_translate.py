from django.utils import translation
from django.utils.translation import gettext as _


def get_translate_text(text, nemo):
    translation.activate(nemo)
    msg = _(text)
    translation.deactivate()
    return msg
