from . import base

for name in dir(base):
    if name.isupper():
        globals()[name] = getattr(base, name)

DEBUG = False
SECURE_HSTS_SECONDS = base.env.int("DJANGO_SECURE_HSTS_SECONDS", default=3600)
SECURE_HSTS_INCLUDE_SUBDOMAINS = base.env.bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
SECURE_HSTS_PRELOAD = base.env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=False)
SECURE_SSL_REDIRECT = base.env.bool("DJANGO_SECURE_SSL_REDIRECT", default=False)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SAMESITE = base.env("DJANGO_SESSION_COOKIE_SAMESITE", default="Lax")
CSRF_COOKIE_SAMESITE = base.env("DJANGO_CSRF_COOKIE_SAMESITE", default="Lax")
SECURE_REFERRER_POLICY = base.env("DJANGO_SECURE_REFERRER_POLICY", default="same-origin")
SECURE_CROSS_ORIGIN_OPENER_POLICY = base.env("DJANGO_SECURE_CROSS_ORIGIN_OPENER_POLICY", default="same-origin")
