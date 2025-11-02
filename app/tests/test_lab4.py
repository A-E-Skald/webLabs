import tempfile
import os
import pytest
from werkzeug.security import generate_password_hash
from flask import url_for

# импорт приложения и моделей
from app import app as flask_app
from models import db, User, Role
from validators import validate_password







@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp(prefix="test_db_", suffix=".sqlite")
    os.close(db_fd)

    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with flask_app.app_context():
        # Не вызывать init_app, если SQLAlchemy уже зарегистрирован в приложении.
        if 'sqlalchemy' not in flask_app.extensions:
            db.init_app(flask_app)

        # Гарантируем чистую БД для тестов
        db.drop_all()
        db.create_all()

        # seed roles и admin
        r_admin = Role(name='admin', description='Администраторы')
        r_user = Role(name='user', description='Обычные пользователи')
        db.session.add_all([r_admin, r_user])
        db.session.commit()

        admin = User(
            login='admin',
            password_hash=generate_password_hash('Zalanet_514'),
            last_name='Adminov',
            first_name='Admin',
            patronymic='A.',
            role_id=r_admin.id
        )
        db.session.add(admin)
        db.session.commit()

    client = flask_app.test_client()

    yield client

    # teardown
    try:
        os.remove(db_path)
    except Exception:
        pass


def login(client, username='admin', password='Zalanet_514'):
    return client.post('/login', data={
        'username': username,
        'password': password
    }, follow_redirects=True)

def test_index_anonymous_shows_view_only(client):
    rv = client.get('/users')
    data = rv.get_data(as_text=True)
    assert rv.status_code == 200
    # кнопка Просмотр должна быть доступна всем
    assert 'Просмотр' in data
    # кнопки создания/редактирования/удаления не должны отображаться анониму
    assert 'Создание пользователя' not in data
    assert 'Редактировать' not in data
    assert 'Удалить' not in data

def test_login_and_index_shows_actions_for_authenticated(client):
    rv = login(client)
    data = rv.get_data(as_text=True)
    assert 'Вход выполнен успешно.' in data
    # теперь на странице пользователей должны быть кнопки редактирования/удаления и создание
    rv2 = client.get('/users')
    data2 = rv2.get_data(as_text=True)
    assert 'Создание пользователя' in data2
    assert 'Редактировать' in data2
    assert 'Удалить' in data2

def test_view_user_page_available_to_anonymous(client):
    # есть пользователь с id=1 созданный в фикстуре
    rv = client.get('/user/1')
    assert rv.status_code == 200
    text = rv.get_data(as_text=True)
    assert 'Пользователь #1' in text
    assert 'admin' in text  # логин отображается

def test_create_user_requires_auth(client):
    rv = client.get('/user/create', follow_redirects=False)
    # редирект на страницу логина
    assert rv.status_code in (302, 301)
    assert '/login' in rv.headers.get('Location','')

def test_create_user_validation_and_success(client):
    login(client)
    # отправим плохие данные (короткий логин)
    bad = client.post('/user/create', data={
        'login': 'a1',
        'password': 'short',
        'last_name': '',
        'first_name': '',
        'patronymic': '',
        'role': ''
    }, follow_redirects=True)
    txt = bad.get_data(as_text=True)
    # должны быть сообщения об ошибках по логину/паролю/имени/фамилии
    assert 'Логин' in txt or 'Логин должен' in txt or 'Поле не может быть пустым' in txt
    # теперь корректные данные
    good = client.post('/user/create', data={
        'login': 'user01',
        'password': 'StrongPass1',
        'last_name': 'Ivanov',
        'first_name': 'Ivan',
        'patronymic': 'I.',
        'role': ''
    }, follow_redirects=True)
    good_txt = good.get_data(as_text=True)
    assert 'Пользователь успешно создан.' in good_txt
    # пользователь появился в БД
    with flask_app.app_context():
        u = User.query.filter_by(login='user01').first()
        assert u is not None
        assert u.last_name == 'Ivanov'

def test_edit_user_requires_auth_and_updates(client):
    login(client)
    # создаём тестового юзера для редактирования
    with flask_app.app_context():
        u = User(login='toedit', password_hash=generate_password_hash('Pp1pppppp'), last_name='Old', first_name='Name')
        db.session.add(u); db.session.commit()
        uid = u.id
    # GET формы
    rv = client.get(f'/user/{uid}/edit')
    assert rv.status_code == 200
    assert 'Редактирование пользователя' in rv.get_data(as_text=True)
    # POST изменений (логин/пароль недоступны в форме редактирования)
    rv2 = client.post(f'/user/{uid}/edit', data={
        'last_name': 'NewLast',
        'first_name': 'NewFirst',
        'patronymic': 'NewPatr',
        'role': ''
    }, follow_redirects=True)
    assert 'Данные пользователя обновлены.' in rv2.get_data(as_text=True)
    with flask_app.app_context():
        u2 = User.query.get(uid)
        assert u2.last_name == 'NewLast'
        assert u2.first_name == 'NewFirst'

def test_delete_user_flow(client):
    login(client)
    with flask_app.app_context():
        u = User(login='todelete', password_hash=generate_password_hash('Aa1111111'), last_name='Del', first_name='Me')
        db.session.add(u); db.session.commit()
        uid = u.id
    # удаление
    rv = client.post(f'/user/{uid}/delete', follow_redirects=True)
    assert 'Пользователь удалён.' in rv.get_data(as_text=True)
    with flask_app.app_context():
        assert User.query.get(uid) is None

def test_change_password_errors_and_success(client):
    # используем admin из фикстуры
    login(client)
    # неверный старый пароль
    rv = client.post('/change_password', data={
        'old_password': 'wrong',
        'new_password': 'Newpass1',
        'new_password2': 'Newpass1'
    }, follow_redirects=True)
    assert 'Старый пароль введён неверно.' in rv.get_data(as_text=True) or 'danger' in rv.get_data(as_text=True)
    # новый пароль не удовлетворяет требованиям (короткий)
    rv2 = client.post('/change_password', data={
        'old_password': 'Zalanet_514',
        'new_password': 'short',
        'new_password2': 'short'
    }, follow_redirects=True)
    assert 'Длина менее 8 символов' in rv2.get_data(as_text=True) or 'Пароль не должен содержать пробелов' in rv2.get_data(as_text=True)
    # успешная смена пароля
    rv3 = client.post('/change_password', data={
        'old_password': 'Zalanet_514',
        'new_password': 'NewStrong1',
        'new_password2': 'NewStrong1'
    }, follow_redirects=True)
    txt = rv3.get_data(as_text=True)
    assert 'Пароль успешно изменён.' in txt
    # теперь разлогинимся и попробуем войти с новым паролем
    client.get('/logout', follow_redirects=True)
    rv_login = client.post('/login', data={'username': 'admin', 'password': 'NewStrong1'}, follow_redirects=True)
    assert 'Вход выполнен успешно.' in rv_login.get_data(as_text=True)

def test_password_validator_edge_cases():
    # слишком короткий
    assert 'Длина менее 8 символов' in validate_password('A1a$1')
    # пробел не допустим
    assert 'Пароль не должен содержать пробелов' in validate_password('Good Pass1')
    # отсутствует цифра
    assert 'Должна быть хотя бы одна цифра' in validate_password('NoDigitPassA')
    # отсутствие заглавной
    assert 'Должна быть хотя бы одна заглавная буква' in validate_password('noupper1')
    # отсутствие строчной
    assert 'Должна быть хотя бы одна строчная буква' in validate_password('NOLOWER1')
    # недопустимый символ
    res = validate_password('GoodPass1🙂')
    assert any('Недопустимый символ' in s for s in res)
