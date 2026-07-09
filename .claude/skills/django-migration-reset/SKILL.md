---
name: django-migration-reset
description: |
  Reset and simplify Django migration files for project apps. Use this skill whenever
  the user wants to reset migrations, rebuild migration files, squash/simplify/consolidate
  migration history, or clean up migration files. Triggers on phrases like "重置migration",
  "简化migration文件", "重建migration", "重新生成migration", "reset migrations",
  "squash migrations", "rebuild migrations", "清理migration文件", "合并migration文件".
  Also use when the user says "删除migration重新生成" or similar.
---

# Django Migration Reset

Delete all project app migration files and regenerate clean `0001_initial.py` files.
The database is NOT touched. The purpose is to produce minimal migrations that run
faster when setting up a fresh database.

## Workflow

### Step 1: Identify Project Apps

Read `application/settings.py` and extract `INSTALLED_APPS`. Project apps are those that:
- Live under the project root (`backend/<app_name>/`)
- Have a `migrations/` directory
- Are NOT Django built-ins (`django.contrib.*`)
- Are NOT third-party packages (`rest_framework`, `corsheaders`, `simpleui`, `daphne`, `captcha`,
  `channels`, `django_filters`, `drf_spectacular`, `django_apscheduler`, `django_extensions`,
  `django_comment_migrate`, anything under `pipeline.*`)

For this project, the project apps are typically:
`opsagent`, `opsflow`, `iam`, `integration`, `cmdb`, `itsm`, `monitor`, `job_platform`,
`portal`, `open_api`, `common`, `mock_service`, `agent_backend`

Always verify by reading `INSTALLED_APPS` in the settings file.

### Step 2: Confirm with User

Present a summary before deleting anything:

```
Summary:
- Project apps: <list>
- Migration files will be DELETED, then regenerated via makemigrations
- A backup will be saved to: backend/migrations_backup_<timestamp>/

Proceed? (y/n)
```

**NEVER proceed without explicit user confirmation.**

### Step 3: Backup Existing Migrations

```bash
cd backend
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="migrations_backup_${TIMESTAMP}"
mkdir -p "${BACKUP_DIR}"

for app in <project_apps_list>; do
    if [ -d "${app}/migrations" ]; then
        mkdir -p "${BACKUP_DIR}/${app}/migrations"
        cp -r "${app}/migrations/" "${BACKUP_DIR}/${app}/migrations/"
    fi
done

echo "Backup saved to: ${BACKUP_DIR}"
```

### Step 4: Delete Migration Files

Delete all migration files from project apps, **keeping `__init__.py`**:

```bash
cd backend
for app in <project_apps_list>; do
    if [ -d "${app}/migrations" ]; then
        find "${app}/migrations" -name "*.py" ! -name "__init__.py" -delete
        find "${app}/migrations" -name "*.pyc" -delete
        echo "Cleaned: ${app}/migrations/"
    fi
done
```

### Step 5: Regenerate Migrations

```bash
cd backend
python manage.py makemigrations
```

This auto-discovers all apps and generates fresh `0001_initial.py` in dependency order.

If cross-app dependency issues occur, generate `iam` first (custom user model), then the rest:

```bash
python manage.py makemigrations iam
python manage.py makemigrations opsagent opsflow integration cmdb itsm monitor \
    job_platform portal open_api common mock_service agent_backend
```

## What Gets Preserved

- `__init__.py` files in all `migrations/` directories
- Third-party app migrations
- Database — nothing is touched
- Backup directory: `backend/migrations_backup_<timestamp>/`

## Recovery

If something goes wrong, restore from backup:

```bash
cd backend
BACKUP="migrations_backup_<timestamp>"
for app in <project_apps_list>; do
    if [ -d "${app}/migrations" ]; then
        find "${app}/migrations" -name "*.py" ! -name "__init__.py" -delete
    fi
    if [ -d "${BACKUP}/${app}/migrations" ]; then
        cp "${BACKUP}/${app}/migrations/"*.py "${app}/migrations/"
    fi
done
```

## Important Notes

- The `iam` app defines the custom user model (`AUTH_USER_MODEL = "iam.IAMUsers"`).
  Other apps' migrations depend on it. Run `makemigrations iam` first if you see
  "swappable dependency" errors.
- The `itsm` app may have uncommitted migrations. Check `git status` — these will be
  deleted and their model changes must already exist in the code.
