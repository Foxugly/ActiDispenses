# ActiDispenses

Application Django pour consulter, diagnostiquer et auditer des traitements de dispenses lies a une base Oracle.

## Prerequis

- Python 3.12+ ou version compatible avec le projet
- Un environnement virtuel
- Oracle Instant Client si l'acces Oracle necessite le mode thick

## Installation

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Configuration

Creer un fichier `.env` a la racine en partant de `.env.example`.

Variables importantes :

- `DJANGO_SECRET_KEY`
- `ORACLE_CREDENTIAL_KEY`
- `APP_VERSION`
- `BUILD_DATE`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_LOG_LEVEL`
- `ORACLE_CLIENT_LIB_DIR`
- `ORACLE_CALL_TIMEOUT_MS`
- `QUERY_PREVIEW_MAX_ROWS`
- `QUERY_ALLOWED_TABLES`
- `QUERY_ALLOWED_SCHEMAS`
- `MONITORING_CACHE_TTL_SECONDS`
- `DJANGO_SESSION_COOKIE_SAMESITE`
- `DJANGO_CSRF_COOKIE_SAMESITE`
- `DJANGO_SECURE_REFERRER_POLICY`
- `DJANGO_SECURE_CROSS_ORIGIN_OPENER_POLICY`

Si Oracle exige le mode thick, renseigner `ORACLE_CLIENT_LIB_DIR` avec le chemin de l'Instant Client.
En production, `config.settings.prod` active aussi des options de durcissement pour les cookies, les headers et les proxies HTTPS.

## Lancement

```powershell
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py runserver
```

## Tests

Avec Django :

```powershell
.venv\Scripts\python.exe manage.py test
```

Avec pytest :

```powershell
.venv\Scripts\python.exe -m pytest -vv
```

Tests Oracle optionnels :

```powershell
$env:RUN_ORACLE_INTEGRATION_TESTS="1"
$env:ORACLE_TEST_HOST="db-host"
$env:ORACLE_TEST_PORT="1521"
$env:ORACLE_TEST_SERVICE_NAME="ORCL"
$env:ORACLE_TEST_USERNAME="scott"
$env:ORACLE_TEST_PASSWORD="secret"
.venv\Scripts\python.exe -m pytest -m integration_oracle -vv
```

Variables des tests Oracle reels :

- `RUN_ORACLE_INTEGRATION_TESTS=1`
- `ORACLE_TEST_HOST`
- `ORACLE_TEST_PORT`
- `ORACLE_TEST_SERVICE_NAME`
- `ORACLE_TEST_USERNAME`
- `ORACLE_TEST_PASSWORD`
- `ORACLE_TEST_SAMPLE_TABLE` optionnel, par defaut `DUAL`

Lint et couverture :

```powershell
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m mypy .
.venv\Scripts\python.exe -m coverage run -m pytest -vv
.venv\Scripts\python.exe -m coverage report --fail-under=85
.venv\Scripts\python.exe -m pre_commit install
```

## CI

Le workflow GitHub Actions est defini dans `.github/workflows/tests.yml`.
Il execute :

- `python manage.py test`
- `python -m pre_commit run --all-files`
- `python -m mypy .`
- `python -m coverage run -m pytest -vv`
- `python -m coverage report --fail-under=85`
- `python -m coverage xml`

En local, tu peux aussi activer les hooks :

- `python -m pre_commit install`

## Endpoints utiles

- `/dispenses/monitoring/`
- `/dispenses/search/`
- `/query/`
- `/query/audit/`
- `/healthz/`
- `/ops/`

## Notes

- La page `/query/` est reservee aux utilisateurs `staff` ou disposant de la permission `query.run_sql_console`.
- La page `/query/audit/` et `/ops/` acceptent aussi des permissions fines via `query.view_queryaudit` et `query.view_ops_dashboard`.
- La commande `python manage.py bootstrap_app_access` cree les groupes standards associes a ces permissions.
- Les requetes SQL y sont limitees a des lectures `SELECT` / `WITH` et a une whitelist configurable via `QUERY_ALLOWED_TABLES`.
- Les executions de la page SQL sont auditees dans le modele `QueryAudit`.
- La page `/query/audit/` dispose d'un detail par execution et d'un export CSV filtre.
- La page `/healthz/?oracle=1` permet un test Oracle explicite avec le credential courant.
- Les tests `integration_oracle` verifient une vraie connexion, `SELECT 1 FROM dual`, le gateway et la description de table.
- La commande `python manage.py diagnose_app` affiche un diagnostic local rapide.
- La commande `python manage.py purge_query_audits --days 90` permet de purger les anciens audits.
- La page `/ops/` regroupe les raccourcis, quelques compteurs d'usage et des indicateurs techniques reserves au staff ou aux utilisateurs autorises.
- Des pages `404` et `500` dediees existent maintenant pour garder le meme rendu global en cas d'erreur.

## Structure

- `dispenses/services/` contient les acces Oracle, le monitoring et les helpers SQL.
- `query/` concentre la page SQL staff et l'audit d'execution.
- `oracle_accounts/` gere les credentials Oracle utilisateur.
- `static/app/js/` contient maintenant le JS partage extrait des templates.

## Historique

Voir aussi `CHANGELOG.md`.
Pour l'exploitation quotidienne et le diagnostic rapide, voir aussi `RUNBOOK.md`.
