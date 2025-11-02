
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Role
from validators import validate_user_input, validate_password

users_bp = Blueprint('users', __name__, template_folder='templates')

@users_bp.route('/users')
def users_list():
    users = User.query.order_by(User.id).all()
    return render_template('users.html', users=users)

@users_bp.route('/user/<int:user_id>')
def user_view(user_id):
    u = User.query.get_or_404(user_id)
    return render_template('user_view.html', user=u)

@users_bp.route('/user/create', methods=['GET','POST'])
@login_required
def user_create():
    roles = Role.query.all()
    if request.method == 'POST':
        data = request.form
        errors = validate_user_input(data, require_password=True)
        if errors:
            # вернуть форму с ошибками и заполненными полями
            return render_template('user_form.html', errors=errors, form=data, roles=roles)
        # создание пользователя
        new_user = User(
            login = data['login'],
            password_hash = generate_password_hash(data['password']),
            last_name = data.get('last_name') or None,
            first_name = data.get('first_name') or None,
            patronymic = data.get('patronymic') or None,
            role_id = int(data['role']) if data.get('role') else None
        )
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Пользователь успешно создан.', 'success')
            return redirect(url_for('users.users_list'))
        except Exception as e:
            db.session.rollback()
            flash('Ошибка при сохранении в БД: ' + str(e), 'danger')
            return render_template('user_form.html', errors={'db': 'Ошибка сохранения'}, form=data, roles=roles)
    return render_template('user_form.html', roles=roles, form={})

@users_bp.route('/user/<int:user_id>/edit', methods=['GET','POST'])
@login_required
def user_edit(user_id):
    u = User.query.get_or_404(user_id)
    roles = Role.query.all()
    if request.method == 'POST':
        data = request.form
        errors = validate_user_input(data, require_password=False, require_login=False)
        if errors:
            return render_template('user_form.html', errors=errors, form=data, roles=roles, edit=True, user=u)
        # обновляем поля (без логина и пароля)
        u.last_name = data.get('last_name') or None
        u.first_name = data.get('first_name') or None
        u.patronymic = data.get('patronymic') or None
        u.role_id = int(data['role']) if data.get('role') else None
        try:
            db.session.commit()
            flash('Данные пользователя обновлены.', 'success')
            return redirect(url_for('users.users_list'))
        except Exception as e:
            db.session.rollback()
            flash('Ошибка при обновлении: ' + str(e), 'danger')
            return render_template('user_form.html', errors={'db': 'Ошибка сохранения'}, form=data, roles=roles, edit=True, user=u)
    # GET
    form = {
        'last_name': u.last_name or '',
        'first_name': u.first_name or '',
        'patronymic': u.patronymic or '',
        'role': str(u.role_id) if u.role_id else ''
    }
    return render_template('user_form.html', roles=roles, form=form, edit=True, user=u)

@users_bp.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
def user_delete(user_id):
    u = User.query.get_or_404(user_id)
    try:
        db.session.delete(u)
        db.session.commit()
        flash('Пользователь удалён.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Ошибка при удалении: ' + str(e), 'danger')
    return redirect(url_for('users.users_list'))

@users_bp.route('/change_password', methods=['GET','POST'])
@login_required
def change_password():
    errors = {}
    if request.method == 'POST':
        old = request.form.get('old_password','')
        new = request.form.get('new_password','')
        new2 = request.form.get('new_password2','')
        if not check_password_hash(current_user.password_hash, old):
            errors['old_password'] = 'Старый пароль введён неверно.'
        pw_errors = validate_password(new)
        if pw_errors:
            errors['new_password'] = '; '.join(pw_errors)
        if new != new2:
            errors['new_password2'] = 'Пароли не совпадают.'
        if errors:
            for v in errors.values():
                flash(v, 'danger')
            return render_template('change_password.html', errors=errors)
        # всё ок
        current_user.password_hash = generate_password_hash(new)
        db.session.commit()
        flash('Пароль успешно изменён.', 'success')
        return redirect(url_for('users.users_list'))
    return render_template('change_password.html', errors={})


