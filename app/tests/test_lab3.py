import time
import urllib.parse

import pytest
from werkzeug.security import generate_password_hash

from app import app as flask_app
from models import User, db


TEST_USER = "admin"
TEST_PASS = "Zalanet_514"


@pytest.fixture(scope="module")
def app():
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })
    # убедимся что пользователь есть в базе
    with flask_app.app_context():
        user = User.query.filter_by(login=TEST_USER).first()
        if not user:
            user = User(login=TEST_USER, password_hash=generate_password_hash(TEST_PASS))
            db.session.add(user)
            db.session.commit()
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, username=TEST_USER, password=TEST_PASS, remember=None, next_param=None, follow=True):
    url = "/login"
    if next_param:
        url = f"{url}?next={urllib.parse.quote(next_param)}"
    data = {"username": username, "password": password}
    if remember:
        # HTML form uses value="y" for checkbox
        data["remember"] = "y"
    return client.post(url, data=data, follow_redirects=follow)


def _text(resp):
    return resp.get_data(as_text=True)


def test_visits_counter_increments_for_single_client(client):
    rv1 = client.get("/visits")
    assert rv1.status_code == 200
    assert "Вы посетили эту страницу 1" in _text(rv1)
    rv2 = client.get("/visits")
    assert "Вы посетили эту страницу 2" in _text(rv2)


def test_visits_counter_is_isolated_between_clients():
    c1 = flask_app.test_client()
    c2 = flask_app.test_client()

    r1 = c1.get("/visits")
    r2 = c2.get("/visits")

    # оба должны начать с 1 независимо
    assert "Вы посетили эту страницу 1" in r1.get_data(as_text=True)
    assert "Вы посетили эту страницу 1" in r2.get_data(as_text=True)

    # второй клиент увеличивает независимо
    c2.get("/visits")
    r1_after = c1.get("/visits")
    assert "Вы посетили эту страницу 2" in r1_after.get_data(as_text=True)


def test_successful_login_redirects_to_index_and_shows_flash(client):
    rv = login(client, follow=True)
    assert rv.status_code == 200
    assert "Вход выполнен успешно." in _text(rv)


def test_failed_login_shows_error_and_returns_401(client):
    rv = client.post("/login", data={"username": "bad", "password": "bad"}, follow_redirects=False)
    # при ошибке код 401 (как в вашем коде)
    assert rv.status_code == 401
    # при follow_redirects=True сообщение видно в теле
    rv2 = client.post("/login", data={"username": "bad", "password": "bad"}, follow_redirects=True)
    assert "Неверный логин или пароль." in _text(rv2)


def test_authenticated_user_can_access_secret_page(client):
    login(client)
    rv = client.get("/secret")
    assert rv.status_code == 200
    assert "<h1" in _text(rv) or "secret" in _text(rv).lower()


def test_anonymous_user_redirected_to_login_with_message(client):
    rv = client.get("/secret", follow_redirects=True)
    # должен попасть на страницу логина и увидеть сообщение о необходимости входа
    assert "Для доступа к запрашиваемой странице необходимо войти в систему." in _text(rv)
    # и отображается форма входа
    assert "<form" in _text(rv) and ("Логин" in _text(rv) or "Пароль" in _text(rv))


def test_after_authentication_user_redirected_back_to_secret(client):
    # сначала запросим /secret чтобы получить редирект на логин с next
    resp = client.get("/secret", follow_redirects=False)
    assert resp.status_code in (302, 303)
    location = resp.headers.get("Location", "")
    assert "/login" in location
    parsed = urllib.parse.urlparse(location)
    q = urllib.parse.parse_qs(parsed.query)
    next_value = q.get("next", ["/secret"])[0]
    # выполняем вход и передаём next
    rv = login(client, next_param=next_value, follow=True)
    # не должно быть формы логина в ответе после редиректа
    assert "<form" not in _text(rv)
    # и доступ к секрету открыт
    secret_resp = client.get("/secret")
    assert secret_resp.status_code == 200


def test_remember_me_sets_remember_token_cookie(client):
    # логин с remember, не follow, чтобы увидеть заголовки Set-Cookie
    url = "/login"
    data = {"username": TEST_USER, "password": TEST_PASS, "remember": "y"}
    resp = client.post(url, data=data, follow_redirects=False)
    # собираем Set-Cookie заголовки
    if hasattr(resp.headers, "get_all"):
        cookies = resp.headers.get_all("Set-Cookie")
    elif hasattr(resp.headers, "getlist"):
        cookies = resp.headers.getlist("Set-Cookie")
    else:
        cookies = [resp.headers.get("Set-Cookie", "")]
    # убедимся, что один из cookie содержит remember_token
    assert any("remember_token=" in c for c in cookies)
    # и что у этого cookie есть Expires или Max-Age
    assert any(("remember_token=" in c and ("Expires=" in c or "Max-Age=" in c)) for c in cookies)


def test_navbar_shows_secret_link_only_when_authenticated(client):
    # анонимный пользователь не видит ссылку /secret
    rv = client.get("/")
    assert 'href="/secret"' not in _text(rv)

    # после логина ссылка должна появиться
    login(client)
    rv2 = client.get("/")
    assert 'href="/secret"' in _text(rv2)


def test_logout_revokes_access_to_secret(client):
    login(client)
    # доступ есть
    r = client.get("/secret")
    assert r.status_code == 200
    # выйдем
    lo = client.get("/logout", follow_redirects=True)
    assert "Вы вышли из системы." in _text(lo)
    # теперь доступ запрещён — редирект на логин
    r2 = client.get("/secret", follow_redirects=False)
    assert r2.status_code in (302, 303)
    assert "/login" in r2.headers.get("Location", "")
