import pytest
from flask import template_rendered
from contextlib import contextmanager
from app import app

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
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client




# ТЕСТЫ ВТОРОЙ ЛАБЫ




# url params отображаются
def test_url_params(client):
    resp = client.get('/show/url?a=1&b=two')
    assert resp.status_code == 200
    data = resp.get_data(as_text=True)
    assert 'a' in data and '1' in data
    assert 'b' in data and 'two' in data

# заголовки отображаются
def test_headers_display(client):
    resp = client.get('/show/headers', headers={'X-Test-Header': 'xyz'})
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert 'X-Test-Header' in text
    assert 'xyz' in text

# сookie устанавливается если нет
def test_cookie_set(client):
    resp = client.get('/show/cookies')
    assert resp.status_code == 200
    sc = resp.headers.get('Set-Cookie', '')
    assert 'lab2_cookie=' in sc
    # при установке должно быть значение (не пустое)
    assert 'lab2_cookie=1' in sc or 'lab2_cookie=1;' in sc

# сookie удаляется если есть
def test_cookie_delete(client):
    # сначала установим cookie в клиент
    client.set_cookie(key="lab2_cookie", value="1")
    resp = client.get('/show/cookies')
    assert resp.status_code == 200
    sc = resp.headers.get('Set-Cookie', '')
    # удаление в Flask делает Set-Cookie с пустым значением и Max-Age=0
    assert 'lab2_cookie=' in sc
    assert ('Max-Age=0' in sc) or ('expires=' in sc.lower())

# параметры формы POST отображаются
def test_form_params_display(client):
    resp = client.post('/show/form', data={'a':'val1','b':'val2'})
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert 'a' in text and 'val1' in text
    assert 'b' in text and 'val2' in text

# корректный номер +7(...) -> форматируется
def test_phone_plus7_format(client):
    resp = client.post('/phone', data={'phone': '+7 (123) 456-78-90'})
    text = resp.get_data(as_text=True)
    assert 'Отформатировано' in text
    assert '8-123-456-78-90' in text

# корректный номер 8(...) -> форматируется
def test_phone_start8_format(client):
    resp = client.post('/phone', data={'phone': '8(123)4567590'})
    text = resp.get_data(as_text=True)
    assert '8-123-456-75-90' in text

# корректный 10-значный номер -> добавляется 8 и форматируется
def test_phone_10_digits(client):
    resp = client.post('/phone', data={'phone': '1234567890'})
    text = resp.get_data(as_text=True)
    assert '8-123-456-78-90' in text

# допустим формат с точками
def test_phone_with_dots(client):
    resp = client.post('/phone', data={'phone': '123.456.75.90'})
    text = resp.get_data(as_text=True)
    assert '8-123-456-75-90' in text

# недопустимые символы -> соответствующее сообщение
def test_phone_invalid_chars(client):
    resp = client.post('/phone', data={'phone': '123ABC456'})
    text = resp.get_data(as_text=True)
    assert 'Недопустимый ввод. В номере телефона встречаются недопустимые символы.' in text
    # поле должно быть подсвечено (is-invalid)
    assert 'is-invalid' in text

# неверное количество цифр для +7
def test_phone_plus7_wrong_count(client):
    resp = client.post('/phone', data={'phone': '+7 12345'})
    text = resp.get_data(as_text=True)
    assert 'Недопустимый ввод. Неверное количество цифр.' in text

# неверное количество цифр для 8
def test_phone_8_wrong_count(client):
    resp = client.post('/phone', data={'phone': '8 12345'})
    text = resp.get_data(as_text=True)
    assert 'Недопустимый ввод. Неверное количество цифр.' in text

# неверное количество цифр для случая без +7/8
def test_phone_no_code_wrong_count(client):
    resp = client.post('/phone', data={'phone': '12345'})
    text = resp.get_data(as_text=True)
    assert 'Недопустимый ввод. Неверное количество цифр.' in text

# поле пустое -> неверное количество цифр
def test_phone_empty(client):
    resp = client.post('/phone', data={'phone': ''})
    text = resp.get_data(as_text=True)
    assert 'Недопустимый ввод. Неверное количество цифр.' in text or 'В номере телефона' in text

# проверка, что для валидного номера НЕ показывается is-invalid и показывается успех
def test_phone_valid_no_invalid_marker(client):
    resp = client.post('/phone', data={'phone': '+7 912 345 67 89'})
    text = resp.get_data(as_text=True)
    assert 'is-invalid' not in text
    assert 'Отформатировано' in text

# случай 11 цифр, не начинающихся с +7/8 — отклоняется 
def test_phone_11_digits_wrong_prefix(client):
    resp = client.post('/phone', data={'phone': '91234567890'})  # 11 цифр but doesn't start with 8 or +7
    text = resp.get_data(as_text=True)
    # по строгим условиям — если не начинается с +7/8, должен быть 10 цифр
    assert 'Недопустимый ввод. Неверное количество цифр.' in text
