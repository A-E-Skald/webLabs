import pytest
from flask import template_rendered
from contextlib import contextmanager
from app import posts_list, app

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




# ТЕСТЫ ПЕРВОЙ ЛАБЫ




# проверяет, что главная страница рендерится с шаблоном index.html
def test_index_uses_index_template(client):
    with captured_templates(app) as templates:
        rv = client.get('/')
        assert rv.status_code == 200
        assert templates, "шаблон не отловлен"
        template, context = templates[0]
        assert template.name == 'index.html'

# проверяет, что страница /posts использует шаблон posts.html
def test_posts_uses_posts_template(client):
    with captured_templates(app) as templates:
        rv = client.get('/posts')
        assert rv.status_code == 200
        assert templates[0][0].name == 'posts.html'

# проверяет, что в контекст страницы постов передаётся список постов
def test_posts_context_contains_posts(client):
    with captured_templates(app) as templates:
        client.get('/posts')
        template, context = templates[0]
        assert 'posts' in context
        assert isinstance(context['posts'], list)
        assert len(context['posts']) >= 1

# проверяет, что на странице постов отображаются карточки постов
def test_posts_page_shows_cards_for_posts(client):
    rv = client.get('/posts')
    assert rv.status_code == 200
    html = rv.get_data(as_text=True)
    posts = posts_list()
    assert posts[0]['title'] in html

# проверяет, что страница одного поста использует шаблон post.html
def test_post_uses_post_template(client):
    with captured_templates(app) as templates:
        rv = client.get('/posts/0')
        assert rv.status_code == 200
        assert templates[0][0].name == 'post.html'
        _, context = templates[0]
        assert 'post' in context

# проверяет, что в шаблон одного поста передаются все нужные поля
def test_post_context_contains_post(client):
    with captured_templates(app) as templates:
        client.get('/posts/0')
        template, context = templates[0]
        post = context['post']
        assert 'title' in post and 'text' in post and 'author' in post and 'date' in post

# проверяет, что на странице поста видны заголовок, текст и имя автора
def test_post_page_contains_title_author_text(client):
    rv = client.get('/posts/0')
    html = rv.get_data(as_text=True)
    p = posts_list()[0]
    assert p['title'] in html
    assert p['text'][:20] in html
    assert p['author'] in html

# проверяет, что на странице поста есть изображение
def test_post_page_contains_image_src(client):
    rv = client.get('/posts/0')
    html = rv.get_data(as_text=True)
    p = posts_list()[0]
    assert f'images/{p["image_id"]}' in html

# проверяет наличие формы добавления комментария
def test_post_page_contains_comment_form(client):
    rv = client.get('/posts/0')
    html = rv.get_data(as_text=True)
    assert '<form' in html
    assert 'textarea' in html or 'input' in html
    assert 'Отправить' in html or 'submit' in html

# проверяет, что комментарии поста отображаются на странице
def test_comments_rendered_on_post_page(client):
    rv = client.get('/posts/0')
    html = rv.get_data(as_text=True)
    p = posts_list()[0]
    assert 'comments' in p
    if p['comments']:
        assert p['comments'][0]['author'] in html
        assert p['comments'][0]['text'][:10] in html

# проверяет, что ответы на комментарии тоже выводятся
def test_comment_replies_rendered(client):
    rv = client.get('/posts/0')
    html = rv.get_data(as_text=True)
    p = posts_list()[0]
    found_reply = False
    for c in p['comments']:
        for r in c.get('replies', []):
            if r['text'][:8] in html:
                found_reply = True
                break
    assert (not any(c.get('replies') for c in p['comments'])) or found_reply

# проверяет правильность формата даты на странице поста
def test_date_format_on_post_page(client):
    rv = client.get('/posts/0')
    html = rv.get_data(as_text=True)
    p = posts_list()[0]
    fmt = p['date'].strftime('%d.%m.%Y')
    assert fmt in html

# проверяет формат даты на странице со списком постов
def test_posts_page_dates_format(client):
    rv = client.get('/posts')
    html = rv.get_data(as_text=True)
    posts = posts_list()
    for p in posts:
        assert p['date'].strftime('%d.%m.%Y') in html

# проверяет, что при неверном индексе возвращается ошибка 404
def test_invalid_post_returns_404(client):
    n = len(posts_list())
    rv = client.get(f'/posts/{n}')
    assert rv.status_code == 404

# проверяет наличие ссылок на отдельные посты на странице /posts
def test_posts_page_has_links_to_posts(client):
    rv = client.get('/posts')
    html = rv.get_data(as_text=True)
    assert '/posts/0' in html

# проверяет, что количество постов в списке не равно нулю
def test_number_of_posts_consistent(client):
    rv = client.get('/posts')
    html = rv.get_data(as_text=True)
    assert len(posts_list()) >= 1



