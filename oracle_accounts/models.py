from django.conf import settings
from django.db import models, transaction

from .crypto import decrypt_value, encrypt_value


class OracleCredential(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="oracle_credentials",
    )
    label = models.CharField(max_length=100, default="Oracle", blank=True)
    host = models.CharField(max_length=255)
    port = models.PositiveIntegerField(default=1521)
    service_name = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    password_encrypted = models.TextField()
    enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    current = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(current=True),
                name="unique_current_oracle_credential_per_user",
            )
        ]
        indexes = [
            models.Index(fields=["user", "current"], name="oracle_cred_current_idx"),
            models.Index(fields=["user", "enabled"], name="oracle_cred_enabled_idx"),
            models.Index(fields=["updated_at"], name="oracle_cred_updated_idx"),
        ]

    def __str__(self):
        return f"{self.user} - {self.label}"

    def set_password(self, raw_password: str):
        self.password_encrypted = encrypt_value(raw_password)

    def get_password(self) -> str:
        return decrypt_value(self.password_encrypted)

    def makedsn(self):
        return f"{self.host}:{self.port}/{self.service_name}"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.current:
                type(self).objects.filter(user=self.user, current=True).exclude(pk=self.pk).update(current=False)
            super().save(*args, **kwargs)
