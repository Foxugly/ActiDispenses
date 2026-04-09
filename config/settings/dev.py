from . import base

for name in dir(base):
    if name.isupper():
        globals()[name] = getattr(base, name)

DEBUG = base.env.bool("DJANGO_DEBUG", True)
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
