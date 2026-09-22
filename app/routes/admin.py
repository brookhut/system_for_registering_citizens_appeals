from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app.database import db_session
from app.models import (
    User, Source, District, Management, Plot, AppealType, Topic, Result, Appeal
)
from app.utils import superadmin_required

admin_bp = Blueprint('admin', __name__)

DICTIONARY_MODELS = {
    'sources': {'name': 'Источники поступления', 'model': Source},
    'districts': {'name': 'Округа', 'model': District},
    'managements': {'name': 'Управления', 'model': Management},
    'plots': {'name': 'Участки', 'model': Plot},
    'appeal_types': {'name': 'Типы обращений', 'model': AppealType},
    'topics': {'name': 'Тематики обращений', 'model': Topic},
    'results': {'name': 'Результаты рассмотрения', 'model': Result},
}


# --- USER MANAGEMENT ---

@admin_bp.route('/users')
@login_required
@superadmin_required
def users_list():
    users = db_session.query(User).order_by(User.id.asc()).all()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/users/create', methods=['POST'])
@login_required
@superadmin_required
def user_create():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    full_name = request.form.get('full_name', '').strip()
    role = request.form.get('role', 'registrator').strip()

    if not username or not password or not full_name:
        flash('Все поля (логин, пароль, ФИО) обязательны для заполнения.', 'danger')
        return redirect(url_for('admin.users_list'))

    if db_session.query(User).filter_by(username=username).first():
        flash(f'Пользователь с логином "{username}" уже существует.', 'danger')
        return redirect(url_for('admin.users_list'))

    if role not in ('registrator', 'superadmin'):
        role = 'registrator'

    new_user = User(
        username=username,
        full_name=full_name,
        role=role,
        is_builtin=False,
        is_active=True
    )
    new_user.set_password(password)

    db_session.add(new_user)
    db_session.commit()
    flash(f'Пользователь "{username}" ({full_name}) успешно создан с ролью {role}.', 'success')
    return redirect(url_for('admin.users_list'))


@admin_bp.route('/users/<int:user_id>/edit', methods=['POST'])
@login_required
@superadmin_required
def user_edit(user_id):
    user = db_session.get(User, user_id)
    if not user:
        abort(404)

    # Built-in superadmin protection:
    # "встроенная учетная запись superadmin логин и пароль хранятся в файле .env, данную учетную запись нельзя удалить, изменить, отключить."
    if user.is_builtin:
        flash('Встроенную учетную запись superadmin нельзя изменить через веб-интерфейс! Логин и пароль задаются в файле .env.', 'danger')
        return redirect(url_for('admin.users_list'))

    full_name = request.form.get('full_name', '').strip()
    password = request.form.get('password', '').strip()
    role = request.form.get('role', 'registrator').strip()

    if full_name:
        user.full_name = full_name
    if password:
        user.set_password(password)
    if role in ('registrator', 'superadmin'):
        user.role = role

    db_session.commit()
    flash(f'Данные пользователя "{user.username}" успешно обновлены.', 'success')
    return redirect(url_for('admin.users_list'))


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@superadmin_required
def user_toggle_status(user_id):
    user = db_session.get(User, user_id)
    if not user:
        abort(404)

    if user.is_builtin:
        flash('Встроенную учетную запись superadmin нельзя отключить!', 'danger')
        return redirect(url_for('admin.users_list'))

    user.is_active = not user.is_active
    db_session.commit()
    status_str = 'активирован' if user.is_active else 'отключен'
    flash(f'Пользователь "{user.username}" {status_str}.', 'info')
    return redirect(url_for('admin.users_list'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@superadmin_required
def user_delete(user_id):
    user = db_session.get(User, user_id)
    if not user:
        abort(404)

    if user.is_builtin:
        flash('Встроенную учетную запись superadmin нельзя удалить!', 'danger')
        return redirect(url_for('admin.users_list'))

    # Check if user has associated appeals
    if user.created_appeals or user.closed_appeals:
        # Prevent hard delete to preserve audit history, offer deactivation
        user.is_active = False
        db_session.commit()
        flash(f'У пользователя "{user.username}" есть привязанные обращения. Он был отключен, чтобы сохранить историю аудита.', 'warning')
        return redirect(url_for('admin.users_list'))

    username = user.username
    db_session.delete(user)
    db_session.commit()
    flash(f'Пользователь "{username}" успешно удален.', 'success')
    return redirect(url_for('admin.users_list'))


# --- REFERENCE BOOKS (DICTIONARIES) MANAGEMENT ---

@admin_bp.route('/dictionaries')
@login_required
@superadmin_required
def dictionaries():
    dict_key = request.args.get('type', 'sources')
    if dict_key not in DICTIONARY_MODELS:
        dict_key = 'sources'

    model_info = DICTIONARY_MODELS[dict_key]
    model = model_info['model']
    items = db_session.query(model).order_by(model.id.asc()).all()

    return render_template(
        'admin/dictionaries.html',
        current_dict=dict_key,
        dict_title=model_info['name'],
        dictionaries=DICTIONARY_MODELS,
        items=items,
    )


@admin_bp.route('/dictionaries/<dict_key>/create', methods=['POST'])
@login_required
@superadmin_required
def dictionary_create(dict_key):
    if dict_key not in DICTIONARY_MODELS:
        abort(404)

    name = request.form.get('name', '').strip()
    code = request.form.get('code', '').strip() or None

    if not name:
        flash('Наименование обязательно для заполнения.', 'danger')
        return redirect(url_for('admin.dictionaries', type=dict_key))

    model = DICTIONARY_MODELS[dict_key]['model']
    existing = db_session.query(model).filter_by(name=name).first()
    if existing:
        flash(f'Элемент с наименованием "{name}" уже существует.', 'danger')
        return redirect(url_for('admin.dictionaries', type=dict_key))

    item = model(name=name, code=code, is_active=True)
    db_session.add(item)
    db_session.commit()
    flash(f'Элемент "{name}" успешно добавлен в справочник.', 'success')
    return redirect(url_for('admin.dictionaries', type=dict_key))


@admin_bp.route('/dictionaries/<dict_key>/<int:item_id>/edit', methods=['POST'])
@login_required
@superadmin_required
def dictionary_edit(dict_key, item_id):
    if dict_key not in DICTIONARY_MODELS:
        abort(404)

    model = DICTIONARY_MODELS[dict_key]['model']
    item = db_session.get(model, item_id)
    if not item:
        abort(404)

    name = request.form.get('name', '').strip()
    code = request.form.get('code', '').strip() or None

    if not name:
        flash('Наименование обязательно для заполнения.', 'danger')
        return redirect(url_for('admin.dictionaries', type=dict_key))

    item.name = name
    item.code = code
    db_session.commit()
    flash(f'Элемент справочника успешно обновлен.', 'success')
    return redirect(url_for('admin.dictionaries', type=dict_key))


@admin_bp.route('/dictionaries/<dict_key>/<int:item_id>/toggle-status', methods=['POST'])
@login_required
@superadmin_required
def dictionary_toggle_status(dict_key, item_id):
    if dict_key not in DICTIONARY_MODELS:
        abort(404)

    model = DICTIONARY_MODELS[dict_key]['model']
    item = db_session.get(model, item_id)
    if not item:
        abort(404)

    item.is_active = not item.is_active
    db_session.commit()
    status_str = 'активирован' if item.is_active else 'деактивирован'
    flash(f'Элемент "{item.name}" {status_str}.', 'info')
    return redirect(url_for('admin.dictionaries', type=dict_key))


@admin_bp.route('/dictionaries/<dict_key>/<int:item_id>/delete', methods=['POST'])
@login_required
@superadmin_required
def dictionary_delete(dict_key, item_id):
    if dict_key not in DICTIONARY_MODELS:
        abort(404)

    model = DICTIONARY_MODELS[dict_key]['model']
    item = db_session.get(model, item_id)
    if not item:
        abort(404)

    # Check if item is referenced in appeals
    field_map = {
        'sources': 'source_id',
        'districts': 'district_id',
        'managements': 'management_id',
        'plots': 'plot_id',
        'appeal_types': 'appeal_type_id',
        'topics': 'topic_id',
        'results': 'result_id',
    }
    col_name = field_map.get(dict_key)
    count = 0
    if col_name:
        count = db_session.query(Appeal).filter(getattr(Appeal, col_name) == item.id).count()

    if count > 0:
        item.is_active = False
        db_session.commit()
        flash(f'Элемент "{item.name}" используется в {count} обращениях, поэтому не может быть удален физически. Он был деактивирован.', 'warning')
        return redirect(url_for('admin.dictionaries', type=dict_key))

    name = item.name
    db_session.delete(item)
    db_session.commit()
    flash(f'Элемент "{name}" успешно удален из справочника.', 'success')
    return redirect(url_for('admin.dictionaries', type=dict_key))


# --- RELATIONS MANAGEMENT: Management <-> Districts & Plots ---
# "зависимости между справочниками в Управление может входить несколько округов, в управление может входить несколько участков"

@admin_bp.route('/relations', methods=['GET', 'POST'])
@login_required
@superadmin_required
def relations():
    managements = db_session.query(Management).order_by(Management.name).all()
    districts = db_session.query(District).filter_by(is_active=True).order_by(District.name).all()
    plots = db_session.query(Plot).filter_by(is_active=True).order_by(Plot.name).all()

    selected_management_id = request.args.get('management_id', type=int)
    if not selected_management_id and managements:
        selected_management_id = managements[0].id

    selected_management = db_session.get(Management, selected_management_id) if selected_management_id else None

    if request.method == 'POST':
        target_management_id = request.form.get('management_id', type=int)
        target_management = db_session.get(Management, target_management_id)
        if not target_management:
            flash('Управление не найдено.', 'danger')
            return redirect(url_for('admin.relations'))

        selected_district_ids = [int(x) for x in request.form.getlist('district_ids') if x.isdigit()]
        selected_plot_ids = [int(x) for x in request.form.getlist('plot_ids') if x.isdigit()]

        # Update districts
        chosen_districts = db_session.query(District).filter(District.id.in_(selected_district_ids)).all() if selected_district_ids else []
        target_management.districts = chosen_districts

        # Update plots
        chosen_plots = db_session.query(Plot).filter(Plot.id.in_(selected_plot_ids)).all() if selected_plot_ids else []
        target_management.plots = chosen_plots

        db_session.commit()
        flash(f'Связи для управления "{target_management.name}" успешно сохранены!', 'success')
        return redirect(url_for('admin.relations', management_id=target_management.id))

    return render_template(
        'admin/relations.html',
        managements=managements,
        districts=districts,
        plots=plots,
        selected_management=selected_management,
        selected_district_ids=[d.id for d in selected_management.districts] if selected_management else [],
        selected_plot_ids=[p.id for p in selected_management.plots] if selected_management else [],
    )
