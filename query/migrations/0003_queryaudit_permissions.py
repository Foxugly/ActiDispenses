from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("query", "0002_queryaudit_indexes"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="queryaudit",
            options={
                "ordering": ["-created_at", "-id"],
                "permissions": [
                    ("run_sql_console", "Can run SQL console"),
                    ("view_ops_dashboard", "Can view ops dashboard"),
                ],
            },
        ),
    ]
