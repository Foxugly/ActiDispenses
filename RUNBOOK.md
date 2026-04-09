# Runbook

Guide court d'exploitation locale et de diagnostic pour ActiDispenses.

## Demarrage rapide

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py runserver
```

## Variables critiques

- `DJANGO_SECRET_KEY`
- `ORACLE_CREDENTIAL_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `ORACLE_CLIENT_LIB_DIR`
- `ORACLE_CALL_TIMEOUT_MS`
- `QUERY_PREVIEW_MAX_ROWS`
- `MONITORING_CACHE_TTL_SECONDS`

## Verification de base

```powershell
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe manage.py diagnose_app
```

Pages utiles :

- `/healthz/`
- `/healthz/?oracle=1`
- `/ops/`
- `/query/audit/`

## Tests

Suite complete :

```powershell
.venv\Scripts\python.exe manage.py test
.venv\Scripts\python.exe -m pytest -vv
```

Qualite locale :

```powershell
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m mypy .
.venv\Scripts\python.exe -m coverage run -m pytest -vv
.venv\Scripts\python.exe -m coverage report --fail-under=85
```

## Oracle

Si Oracle exige le mode thick :

```env
ORACLE_CLIENT_LIB_DIR=C:\Oracle\instantclient_23_9
```

Si une erreur `DPY-3015` apparait, verifie d'abord :

1. que `ORACLE_CLIENT_LIB_DIR` pointe vers un Instant Client valide
2. que l'application n'est pas retombee en mode thin a cause d'une valeur vide

## Maintenance

Purge des audits SQL anciens :

```powershell
.venv\Scripts\python.exe manage.py purge_query_audits --days 90
```

## Incidents frequents

`403` sur les outils techniques :

- verifier que l'utilisateur est bien `staff`

`503_db` :

- verifier le credential Oracle courant
- verifier le host, le port et le service Oracle
- lancer `/healthz/?oracle=1`

`ModuleNotFoundError` au lancement :

- verifier `DJANGO_SETTINGS_MODULE=config.settings`
- verifier le dossier de travail PyCharm
