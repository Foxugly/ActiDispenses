from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("oracle_accounts", "0002_alter_oraclecredential_user"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="oraclecredential",
            constraint=models.UniqueConstraint(
                condition=models.Q(current=True),
                fields=["user"],
                name="unique_current_oracle_credential_per_user",
            ),
        ),
    ]
