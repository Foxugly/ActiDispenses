from typing import cast

from cryptography.fernet import Fernet
from django.conf import settings


def _get_cipher() -> Fernet:
    return Fernet(settings.ORACLE_CREDENTIAL_KEY.encode())


def encrypt_value(value: str) -> str:
    cipher = _get_cipher()
    return cast(str, cipher.encrypt(value.encode()).decode())


def decrypt_value(value: str) -> str:
    cipher = _get_cipher()
    return cast(str, cipher.decrypt(value.encode()).decode())
