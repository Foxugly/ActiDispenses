from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("oracle_accounts", "0003_unique_current_per_user"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="oraclecredential",
            index=models.Index(fields=["user", "current"], name="oracle_cred_current_idx"),
        ),
        migrations.AddIndex(
            model_name="oraclecredential",
            index=models.Index(fields=["user", "enabled"], name="oracle_cred_enabled_idx"),
        ),
        migrations.AddIndex(
            model_name="oraclecredential",
            index=models.Index(fields=["updated_at"], name="oracle_cred_updated_idx"),
        ),
    ]
