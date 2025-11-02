import random
from flask import Flask, request, abort, render_template, redirect, url_for, make_response, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import timedelta, datetime
import werkzeug
from functools import lru_cache
from faker import Faker
import re
from app.models import db, User as DBUser, Role
from app.users import users_bp
from pathlib import Path
import os


fake = Faker()


app = Flask(__name__)
application = app

from pathlib import Path
import os

# гарантируем существование instance folder и правильный абсолютный путь к файлу БД
os.makedirs(app.instance_path, exist_ok=True)   # создаст app/instance если нужно

db_file = Path(app.instance_path) / 'app.db'
# для логов и отладки — покажем путь в лог gunicorn
app.logger.info(f"Using sqlite DB at: {db_file.resolve()} (exists: {db_file.exists()})")

# используем абсолютный путь в URI
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_file.resolve()}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# (опционально) если хочешь отключить проверку same-thread (необязательно для gunicorn workers)
# app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"connect_args": {"check_same_thread": False}}


db.init_app(app)

app.register_blueprint(users_bp)

images_ids = ['7d4e9175-95ea-4c5f-8be5-92a6b708bb3c',
              '2d2ab7df-cdbc-48a8-a936-35bba702def5',
              '6e12f3de-d5fd-4ebb-855b-8cbc485278b7',
              'afc2cfe7-5cac-4b80-9b9a-d5c65ef0c728',
              'cab5b7f2-774e-4884-a200-0c0180fa777f']




# 1 лаба




def generate_comments(replies=True):
    comments = []
    for _ in range(random.randint(1, 3)):
        comment = { 'author': fake.name(), 'text': fake.text() }
        if replies:
            comment['replies'] = generate_comments(replies=False)
        comments.append(comment)
    return comments

def generate_post(i):
    return {
        'title': 'Заголовок поста',
        'text': fake.paragraph(nb_sentences=100),
        'author': fake.name(),
        'date': fake.date_time_between(start_date='-2y', end_date='now'),
        'image_id': f'{images_ids[i]}.jpg',
        'comments': generate_comments()
    }

@lru_cache
def posts_list():
    return sorted([generate_post(i) for i in range(5)], key=lambda p: p['date'], reverse=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/posts')
def posts():
    return render_template('posts.html', title='Посты', posts=posts_list())

@app.route('/posts/<int:index>')
def post(index):
    posts = posts_list()
    if index < 0 or index >= len(posts):
        abort(404)
    p = posts[index]
    return render_template('post.html', title=p['title'], post=p)

@app.route('/about')
def about():
    return render_template('about.html', title='Об авторе')


@app.route('/posts/<int:index>')
def show_post(index):
    posts = posts_list()
    try:
        p = posts[index]
    except IndexError:
        abort(404)
    return render_template('post.html', title=p['title'], post=p)




# 2 лаба




# вывод параметров url
@app.route('/show/url')
def show_url_params():
    params = request.args.to_dict(flat=False)  # сохраняем все значения
    return render_template('show_params.html', title='Параметры URL', items=params)

# отображение хедера
@app.route('/show/headers')
def show_headers():
    # request.headers — объект, приводим к dict
    headers = dict(request.headers)
    return render_template('show_params.html', title='Заголовки запроса', items=headers)

# сookie: устанавливаем, если нет; удаляем, если есть
COOKIE_NAME = 'lab2_cookie'
@app.route('/show/cookies')
def show_cookies():
    cookies = request.cookies
    resp = make_response(render_template('show_params.html', title='Cookie', items=dict(cookies)))
    if COOKIE_NAME in cookies:
        # удалить cookie
        resp.set_cookie(COOKIE_NAME, '', max_age=0)
        # для явности добавить флаг, чтобы в шаблоне показать, что удалено
        resp.set_data(render_template('show_params.html', title='Cookie', items=dict(cookies), message='Cookie удалено'))
    else:
        # установить cookie
        resp.set_cookie(COOKIE_NAME, '1', max_age=60*60*24*30)  # месяц
        resp.set_data(render_template('show_params.html', title='Cookie', items=dict(cookies), message='Cookie установлено'))
    return resp

# параметры формы: отображаем то, что пришло в POST
@app.route('/show/form', methods=['GET','POST'])
def show_form_params():
    if request.method == 'POST':
        form = request.form.to_dict(flat=False)
        return render_template('show_params.html', title='Параметры формы', items=form)
    return render_template('form_submit.html')  # простая форма для тестов

# валидация и форматирование номера телефона
ALLOWED_CHARS_RE = re.compile(r'^[0-9+\-\.\s()]+$')

def format_to_8(digits: str) -> str:
    # берем только цифры, плюсы скобки дэши не считаем
    # приводим к 11 цифрам с ведущей 8: если 10 цифр — добавляем 8 вперед; если 11 и начинается с 7/8 — делаем ведущую 8
    if len(digits) == 10:
        digits = '8' + digits
    elif len(digits) == 11:
        if digits[0] in ('7', '8'):
            digits = '8' + digits[1:]
        else:
            # прочие 11-значные — оставим как есть, но всё равно форматируем, заменяя первый символ на 8
            digits = '8' + digits[1:]
    else:
        # не должно попадать сюда при корректной проверке
        pass
    # формат: 8-XXX-XXX-XX-XX
    return f"8-{digits[1:4]}-{digits[4:7]}-{digits[7:9]}-{digits[9:11]}"

@app.route('/phone', methods=['GET','POST'])
def phone_check():
    error = None
    invalid_type = None  # 'count' или 'chars'
    formatted = None
    value = ''
    if request.method == 'POST':
        value = request.form.get('phone', '')
        # проверяем на недопустимые символы
        if not ALLOWED_CHARS_RE.match(value):
            invalid_type = 'chars'
            error = 'Недопустимый ввод. В номере телефона встречаются недопустимые символы.'
        else:
            # оставляем только цифры
            digits = ''.join(re.findall(r'\d', value))
            # проверяем количество цифр
            starts_with_plus7 = value.strip().startswith('+7')
            starts_with_8 = value.strip().startswith('8')
            if starts_with_plus7 or starts_with_8:
                expected_counts = (11,)
            else:
                expected_counts = (10,11)  # допустим 11 если они ввели с кодом, но требование: "в остальных случаях – 10 цифр" 
                # однако текст задания: "номер должен содержать 11 цифр если он начинается с «+7» или «8», в остальных случаях – 10 цифр"
                # здесь строго проверяем:
                if not (len(digits) in (10,11)):
                    invalid_type = 'count'
                    error = 'Недопустимый ввод. Неверное количество цифр.'
                # but we still need to enforce strict rule below
            # строгое правило:
            if starts_with_plus7 or starts_with_8:
                if len(digits) != 11:
                    invalid_type = 'count'
                    error = 'Недопустимый ввод. Неверное количество цифр.'
            else:
                if len(digits) != 10:
                    invalid_type = 'count'
                    error = 'Недопустимый ввод. Неверное количество цифр.'

            if invalid_type is None:
                # форматируем
                formatted = format_to_8(digits)
    return render_template('phone.html', phone=value, error=error, invalid_type=invalid_type, formatted=formatted)




# лаба 3 и 4




app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY','replace-this-secret-for-prod')
# срок для remember me
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=7)

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Для доступа к запрашиваемой странице необходимо войти в систему.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    # user_id приходит как строка — в БД id integer
    try:
        return DBUser.query.get(int(user_id))
    except Exception:
        return None

# Страница счётчика посещений
@app.route('/visits')
def visits():
    # session — глобальный объект Flask для хранения данных по пользователю (cookie-backed)
    session.setdefault('visits', 0)
    session['visits'] = session.get('visits', 0) + 1
    return render_template('visits.html', visits=session['visits'])

# Страница входа
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        remember = bool(request.form.get('remember'))
        user = DBUser.query.filter_by(login=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            flash('Вход выполнен успешно.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Неверный логин или пароль.', 'danger')
            return render_template('login.html'), 401
    return render_template('login.html')


# Выход
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))

# Секретная страница — доступна только авторизованным
@app.route('/secret')
@login_required
def secret():
    return render_template('secret.html')










if __name__ == "__main__":
    app.run(debug=True)

