from django.conf import settings
from django.db import models


class QueryAudit(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="query_audits",
    )
    query_text = models.TextField()
    row_count = models.PositiveIntegerField(default=0)
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        permissions = [
            ("run_sql_console", "Can run SQL console"),
            ("view_ops_dashboard", "Can view ops dashboard"),
        ]
        indexes = [
            models.Index(fields=["created_at"], name="query_audit_created_idx"),
            models.Index(fields=["success", "created_at"], name="query_audit_status_idx"),
            models.Index(fields=["user", "created_at"], name="query_audit_user_idx"),
        ]

    def __str__(self):
        username = self.user.username if self.user else "anonymous"
        return f"{username} - {'success' if self.success else 'failure'}"
