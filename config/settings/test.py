from . import base

for name in dir(base):
    if name.isupper():
        globals()[name] = getattr(base, name)

DEBUG = False
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
