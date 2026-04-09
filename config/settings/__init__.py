import os
from importlib import import_module

ENVIRONMENT_MODULES = {
    "prod": "config.settings.prod",
    "test": "config.settings.test",
}

environment = os.environ.get("DJANGO_ENV", "").lower()
settings_module = import_module(ENVIRONMENT_MODULES.get(environment, "config.settings.dev"))

for name in dir(settings_module):
    if name.isupper():
        globals()[name] = getattr(settings_module, name)
