import pytest
from datetime import datetime, timedelta
from flask import template_rendered
from contextlib import contextmanager
from app.app import app as flask_app   # если app/app.py существует

@pytest.fixture
def app():
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    flask_app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=7)
    return flask_app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
@contextmanager
def captured_templates(app):
    recorded = []
    def record(sender, template, context, **extra):
        recorded.append((template, context))
    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)

@pytest.fixture
def posts_list():
    return [
        {
            'title': 'Заголовок поста',
            'text': 'Текст поста',
            'author': 'Иванов Иван Иванович',
            'date': datetime(2025, 3, 10),
            'image_id': '123.jpg',
            'comments': []
        }
    ]



# app/tests/conftest.py
import shutil
from pathlib import Path
import pytest

# project_root — предполагается: project/... , файл conftest.py в app/tests
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Жёстко: источник — project_root/instance/app.db
SOURCE_DB = PROJECT_ROOT / 'instance' / 'app.db'
# Резервная копия — project_root/app/app_back.db
BACKUP_DB = PROJECT_ROOT / 'app' / 'app_back.db'

@pytest.fixture(scope='session', autouse=True)
def backup_and_restore_instance_db():
    """
    1) Перед тестовой сессией: если instance/app.db существует -> копируем в app/app_back.db
       (если не существует — отмечаем, что бэкапа не делали).
    2) После тестов: если бэкап был сделан — копируем app/app_back.db обратно в instance/app.db.
    Бэкап НЕ удаляется автоматически.
    """
    # гарантируем папки
    BACKUP_DB.parent.mkdir(parents=True, exist_ok=True)
    SOURCE_DB.parent.mkdir(parents=True, exist_ok=True)

    did_backup = False
    try:
        if SOURCE_DB.exists():
            shutil.copy2(SOURCE_DB, BACKUP_DB)
            did_backup = True
            print(f"[conftest] Backup created: {BACKUP_DB} <- {SOURCE_DB}")
        else:
            # источник не найден — ничего не копируем, но оставляем бэкап нетронутым
            print(f"[conftest] Source DB not found: {SOURCE_DB}. No backup created.")
        yield
    finally:
        # попытка аккуратно закрыть SQLAlchemy, если он подключён (снимает lock на sqlite)
        try:
            from app.models import db as sa_db
            sa_db.session.remove()
            sa_db.engine.dispose()
        except Exception:
            pass

        # восстанавливаем только если ранее сделали бэкап
        if did_backup and BACKUP_DB.exists():
            try:
                shutil.copy2(BACKUP_DB, SOURCE_DB)
                print(f"[conftest] Restored: {SOURCE_DB} <- {BACKUP_DB}")
            except Exception as exc:
                print(f"[conftest] ERROR restoring DB: {exc}")
        else:
            if not did_backup:
                print("[conftest] No backup was created before tests; restore skipped.")
            else:
                print(f"[conftest] Backup file missing ({BACKUP_DB}); restore skipped.")
