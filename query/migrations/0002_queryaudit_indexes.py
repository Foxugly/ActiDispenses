from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("query", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="queryaudit",
            index=models.Index(fields=["created_at"], name="query_audit_created_idx"),
        ),
        migrations.AddIndex(
            model_name="queryaudit",
            index=models.Index(fields=["success", "created_at"], name="query_audit_status_idx"),
        ),
        migrations.AddIndex(
            model_name="queryaudit",
            index=models.Index(fields=["user", "created_at"], name="query_audit_user_idx"),
        ),
    ]
