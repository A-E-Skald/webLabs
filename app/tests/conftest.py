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


# для тестов 4 лабы - тесты влезают в бд и изменют ее, потому копирую бд в app_back и потом восстаналиваю обратно

import shutil
from pathlib import Path
import pytest

# пути относительно этого файла: ../instance/app.db
INSTANCE_DB = Path(__file__).resolve().parents[1] / 'instance' / 'app.db'
BACKUP_DB = INSTANCE_DB.parent / 'app_back.db'

@pytest.fixture(scope='session', autouse=True)
def backup_and_restore_instance_db():
    """
    Автобэкап instance/app.db -> instance/app_back.db перед тестами
    и восстановление после всех тестов.
    Выполняется автоматически для всей сессии pytest.
    """
    # backup
    if INSTANCE_DB.exists():
        shutil.copy2(INSTANCE_DB, BACKUP_DB)
    else:
        # если исходной БД нет — создаём пустой файл-бэкап,
        # чтобы при restore не получить FileNotFoundError
        BACKUP_DB.parent.mkdir(parents=True, exist_ok=True)
        BACKUP_DB.write_bytes(b'')

    try:
        yield
    finally:
        # перед восстановлением попробуем корректно закрыть возможные
        # открытые соединения SQLAlchemy, чтобы не было блокировки файла.
        try:
            # импорт локальный чтобы избежать проблем при раннем импорте
            from app.models import db
            # закрыть сессии и отключить движок
            db.session.remove()
            db.engine.dispose()
        except Exception:
            # если не получилось — продолжаем всё равно пытаться восстановить файл
            pass

        # restore (копируем бэкап обратно в instance/app.db)
        if BACKUP_DB.exists():
            shutil.copy2(BACKUP_DB, INSTANCE_DB)
            # опционально удаляем бэкап
            try:
                BACKUP_DB.unlink()
            except Exception:
                pass

