
import re

login_re = re.compile(r'^[A-Za-z0-9]{5,}$')  # только латинские и цифры, не менее 5

# набор разрешённых спецсимволов для пароля (строго перечислены в ТЗ)
allowed_symbols = r'~!\?@#\$%\^&\*_\-\+\(\)\[\]\{\}><\/\\\|"' + r"'\.,:"

# password rules:
def validate_password(pw: str):
    errors = []
    if len(pw) < 8:
        errors.append('Длина менее 8 символов')
    if len(pw) > 128:
        errors.append('Длина более 128 символов')
    if ' ' in pw:
        errors.append('Пароль не должен содержать пробелов')
    if not any(c.isdigit() for c in pw):
        errors.append('Должна быть хотя бы одна цифра')
    if not any(c.islower() for c in pw):
        errors.append('Должна быть хотя бы одна строчная буква')
    if not any(c.isupper() for c in pw):
        errors.append('Должна быть хотя бы одна заглавная буква')
    # разрешённые буквы — латинские или кириллические
    for ch in pw:
        if ch.isalpha():
            # проверка на кириллицу или латиницу — обе допустимы
            continue
        elif ch.isdigit():
            continue
        elif ch in allowed_symbols:
            continue
        else:
            errors.append(f"Недопустимый символ: {ch}")
            break
    return errors  # пустой список = ОК

def validate_user_input(form, require_password=True, require_login=True):
    errors = {}
    # проверка логина только если require_login=True
    if require_login:
        login = form.get('login','').strip()
        if not login:
            errors['login'] = 'Поле не может быть пустым'
        elif not login_re.match(login):
            errors['login'] = 'Логин должен содержать только латинские буквы/цифры и быть >=5 символов'

    if require_password:
        pw = form.get('password','')
        if not pw:
            errors['password'] = 'Поле не может быть пустым'
        else:
            pw_errs = validate_password(pw)
            if pw_errs:
                errors['password'] = '; '.join(pw_errs)

    # фамилия/имя обязательны по ТЗ в обеих формах
    if not form.get('last_name','').strip():
        errors['last_name'] = 'Поле не может быть пустым'
    if not form.get('first_name','').strip():
        errors['first_name'] = 'Поле не может быть пустым'

    return errors


