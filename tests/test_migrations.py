from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class MigrationSmokeTests(TransactionTestCase):
    reset_sequences = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.executor = MigrationExecutor(connection)
        cls.latest_targets = cls.executor.loader.graph.leaf_nodes()

    @classmethod
    def tearDownClass(cls):
        cls.executor.loader.build_graph()
        cls.executor.migrate(cls.latest_targets)
        super().tearDownClass()

    def migrate_to(self, targets):
        self.executor.loader.build_graph()
        self.executor.migrate(targets)
        return self.executor.loader.project_state(targets).apps

    def test_query_index_migration_preserves_existing_data(self):
        old_apps = self.migrate_to([("query", "0001_initial")])
        QueryAudit = old_apps.get_model("query", "QueryAudit")
        audit = QueryAudit.objects.create(query_text="SELECT 1", row_count=1, success=True, error_message="")

        new_apps = self.migrate_to([("query", "0002_queryaudit_indexes")])
        QueryAuditNew = new_apps.get_model("query", "QueryAudit")

        self.assertTrue(QueryAuditNew.objects.filter(pk=audit.pk, query_text="SELECT 1").exists())

    def test_oracle_index_migration_preserves_existing_data(self):
        old_apps = self.migrate_to([("oracle_accounts", "0003_unique_current_per_user")])
        User = old_apps.get_model("auth", "User")
        OracleCredential = old_apps.get_model("oracle_accounts", "OracleCredential")
        user = User.objects.create(username="migration-user")
        credential = OracleCredential.objects.create(
            user=user,
            label="Main",
            host="db.local",
            port=1521,
            service_name="ORCL",
            username="scott",
            password_encrypted="encrypted",
            enabled=True,
            current=True,
        )

        new_apps = self.migrate_to([("oracle_accounts", "0004_oraclecredential_indexes")])
        OracleCredentialNew = new_apps.get_model("oracle_accounts", "OracleCredential")

        self.assertTrue(OracleCredentialNew.objects.filter(pk=credential.pk, current=True).exists())
