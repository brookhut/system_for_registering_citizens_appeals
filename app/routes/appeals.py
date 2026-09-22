from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_, and_
from app.database import db_session
from app.models import (
    Appeal, Source, District, Management, Plot, AppealType, Topic, Result, User
)
from app.utils import parse_date, format_date_eur

appeals_bp = Blueprint('appeals', __name__)


@appeals_bp.route('/')
@login_required
def index():
    tab = request.args.get('tab', 'active')  # 'active' or 'closed'
    if tab not in ('active', 'closed'):
        tab = 'active'

    # Filter parameters
    search_number = request.args.get('number', '').strip()
    search_reg_date = request.args.get('reg_date', '').strip()
    search_management_id = request.args.get('management_id', '').strip()
    search_district_id = request.args.get('district_id', '').strip()
    search_type_id = request.args.get('type_id', '').strip()
    search_topic_id = request.args.get('topic_id', '').strip()
    search_deadline_filter = request.args.get('deadline_filter', '').strip()
    search_exact_days = request.args.get('exact_days', '').strip()

    parsed_reg_date = parse_date(search_reg_date) if search_reg_date else None

    # Base query
    def build_query(target_status):
        q = db_session.query(Appeal).filter(Appeal.status == target_status)

        if search_number:
            q = q.filter(Appeal.number.ilike(f'%{search_number}%'))

        if parsed_reg_date:
            q = q.filter(Appeal.reg_date == parsed_reg_date)

        if search_management_id and search_management_id.isdigit():
            q = q.filter(Appeal.management_id == int(search_management_id))

        if search_district_id and search_district_id.isdigit():
            q = q.filter(Appeal.district_id == int(search_district_id))

        if search_type_id and search_type_id.isdigit():
            q = q.filter(Appeal.appeal_type_id == int(search_type_id))

        if search_topic_id and search_topic_id.isdigit():
            q = q.filter(Appeal.topic_id == int(search_topic_id))

        # Deadline / Days to answer filter
        today = date.today()
        if search_exact_days and (search_exact_days.isdigit() or (search_exact_days.startswith('-') and search_exact_days[1:].isdigit())):
            exact_d = int(search_exact_days)
            target_deadline = today + timedelta(days=exact_d)
            q = q.filter(Appeal.deadline_date == target_deadline)
        elif search_deadline_filter:
            if search_deadline_filter == 'overdue':  # < 0 days (past deadline)
                q = q.filter(Appeal.deadline_date < today)
            elif search_deadline_filter == 'today':  # 0 days (today)
                q = q.filter(Appeal.deadline_date == today)
            elif search_deadline_filter == '1-3':  # 1 to 3 days
                q = q.filter(Appeal.deadline_date > today, Appeal.deadline_date <= today + timedelta(days=3))
            elif search_deadline_filter == '4-7':  # 4 to 7 days
                q = q.filter(Appeal.deadline_date > today + timedelta(days=3), Appeal.deadline_date <= today + timedelta(days=7))
            elif search_deadline_filter == '>7':  # > 7 days
                q = q.filter(Appeal.deadline_date > today + timedelta(days=7))
            elif search_deadline_filter == 'none':  # no deadline
                q = q.filter(Appeal.deadline_date.is_(None))

        return q

    # Counts
    active_query = build_query('В работе')
    closed_query = build_query('Закрыто')

    active_count = active_query.count()
    closed_count = closed_query.count()

    # Get records for current tab
    if tab == 'active':
        appeals = active_query.order_by(Appeal.deadline_date.asc().nulls_last(), Appeal.id.desc()).all()
    else:
        appeals = closed_query.order_by(Appeal.closed_at.desc().nulls_last(), Appeal.id.desc()).all()

    # Reference data for filter dropdowns
    sources = db_session.query(Source).filter_by(is_active=True).order_by(Source.name).all()
    districts = db_session.query(District).filter_by(is_active=True).order_by(District.name).all()
    managements = db_session.query(Management).filter_by(is_active=True).order_by(Management.name).all()
    appeal_types = db_session.query(AppealType).filter_by(is_active=True).order_by(AppealType.name).all()
    topics = db_session.query(Topic).filter_by(is_active=True).order_by(Topic.name).all()

    return render_template(
        'appeals/list.html',
        appeals=appeals,
        tab=tab,
        active_count=active_count,
        closed_count=closed_count,
        sources=sources,
        districts=districts,
        managements=managements,
        appeal_types=appeal_types,
        topics=topics,
        search_number=search_number,
        search_reg_date=search_reg_date,
        search_reg_date_eur=format_date_eur(parsed_reg_date) if parsed_reg_date else '',
        search_management_id=search_management_id,
        search_district_id=search_district_id,
        search_type_id=search_type_id,
        search_topic_id=search_topic_id,
        search_deadline_filter=search_deadline_filter,
        search_exact_days=search_exact_days,
        today=date.today(),
    )


@appeals_bp.route('/appeals/new', methods=['GET', 'POST'])
@login_required
def create():
    today = date.today()

    if request.method == 'POST':
        errors = []

        # 1. Дата регистрации (cannot be > today, European standard DD.MM.YYYY, required, no time)
        reg_date_raw = request.form.get('reg_date', '').strip()
        reg_date = parse_date(reg_date_raw)
        if not reg_date:
            errors.append('Дата регистрации обязательна для заполнения (формат ДД.ММ.ГГГГ).')
        elif reg_date > today:
            errors.append(f'Дата регистрации ({format_date_eur(reg_date)}) не может быть больше текущей даты ({format_date_eur(today)}).')

        # 2. № обращения (required, from external system)
        number = request.form.get('number', '').strip()
        if not number:
            errors.append('№ обращения обязателен для заполнения.')

        # 3. Источник поступления (required)
        source_id = request.form.get('source_id', '').strip()
        if not source_id or not source_id.isdigit():
            errors.append('Источник поступления обязателен для выбора.')

        # 4. Округ (required)
        district_id = request.form.get('district_id', '').strip()
        if not district_id or not district_id.isdigit():
            errors.append('Округ обязателен для выбора.')

        # 5. Управление (optional)
        management_id = request.form.get('management_id', '').strip()
        management_id_val = int(management_id) if management_id and management_id.isdigit() else None

        # 6. Участок (optional)
        plot_id = request.form.get('plot_id', '').strip()
        plot_id_val = int(plot_id) if plot_id and plot_id.isdigit() else None

        # 7. Пол заявителя (optional: 'мужской', 'женский')
        applicant_gender = request.form.get('applicant_gender', '').strip()
        if applicant_gender and applicant_gender not in ('мужской', 'женский'):
            applicant_gender = None

        # 8. Тип обращения (required)
        appeal_type_id = request.form.get('appeal_type_id', '').strip()
        if not appeal_type_id or not appeal_type_id.isdigit():
            errors.append('Тип обращения обязателен для выбора.')

        # 9. Тематика обращения (required)
        topic_id = request.form.get('topic_id', '').strip()
        if not topic_id or not topic_id.isdigit():
            errors.append('Тематика обращения обязательна для выбора.')

        # 10. Обоснованность (optional: 'обоснован', 'не обоснован')
        validity = request.form.get('validity', '').strip()
        if validity and validity not in ('обоснован', 'не обоснован'):
            validity = None

        # 11. Повторность (optional: 'Первичное', 'Повторное', 'Многократное')
        recurrence = request.form.get('recurrence', '').strip()
        if recurrence and recurrence not in ('Первичное', 'Повторное', 'Многократное'):
            recurrence = None

        # 12. Результат рассмотрения (optional)
        result_id = request.form.get('result_id', '').strip()
        result_id_val = int(result_id) if result_id and result_id.isdigit() else None

        # 13. Контрольные сроки (optional)
        deadline_date_raw = request.form.get('deadline_date', '').strip()
        deadline_date = parse_date(deadline_date_raw) if deadline_date_raw else None

        # 14. Не состоит на обслуживании (checkbox)
        not_serviced = bool(request.form.get('not_serviced'))

        # 15. Комментарий (optional)
        comment = request.form.get('comment', '').strip()

        if errors:
            for error in errors:
                flash(error, 'danger')
            # Re-render with submitted data
            return render_template(
                'appeals/form.html',
                form_data=request.form,
                action='create',
                sources=db_session.query(Source).filter_by(is_active=True).order_by(Source.name).all(),
                districts=db_session.query(District).filter_by(is_active=True).order_by(District.name).all(),
                managements=db_session.query(Management).filter_by(is_active=True).order_by(Management.name).all(),
                plots=db_session.query(Plot).filter_by(is_active=True).order_by(Plot.name).all(),
                appeal_types=db_session.query(AppealType).filter_by(is_active=True).order_by(AppealType.name).all(),
                topics=db_session.query(Topic).filter_by(is_active=True).order_by(Topic.name).all(),
                results=db_session.query(Result).filter_by(is_active=True).order_by(Result.name).all(),
                today=today,
            )

        # Create appeal
        appeal = Appeal(
            number=number,
            reg_date=reg_date,
            status='В работе',
            source_id=int(source_id),
            district_id=int(district_id),
            management_id=management_id_val,
            plot_id=plot_id_val,
            applicant_gender=applicant_gender or None,
            appeal_type_id=int(appeal_type_id),
            topic_id=int(topic_id),
            validity=validity or None,
            recurrence=recurrence or None,
            result_id=result_id_val,
            deadline_date=deadline_date,
            not_serviced=not_serviced,
            comment=comment or None,
            created_by_id=current_user.id,
            created_at=datetime.now(),
        )
        db_session.add(appeal)
        db_session.commit()

        flash(f'Обращение №{appeal.number} успешно зарегистрировано со статусом "В работе"!', 'success')
        return redirect(url_for('appeals.detail', appeal_id=appeal.id))

    # GET request
    sources = db_session.query(Source).filter_by(is_active=True).order_by(Source.name).all()
    districts = db_session.query(District).filter_by(is_active=True).order_by(District.name).all()
    managements = db_session.query(Management).filter_by(is_active=True).order_by(Management.name).all()
    plots = db_session.query(Plot).filter_by(is_active=True).order_by(Plot.name).all()
    appeal_types = db_session.query(AppealType).filter_by(is_active=True).order_by(AppealType.name).all()
    topics = db_session.query(Topic).filter_by(is_active=True).order_by(Topic.name).all()
    results = db_session.query(Result).filter_by(is_active=True).order_by(Result.name).all()

    default_form_data = {
        'reg_date': today.strftime('%Y-%m-%d'),
        'reg_date_eur': today.strftime('%d.%m.%Y'),
    }

    return render_template(
        'appeals/form.html',
        form_data=default_form_data,
        action='create',
        sources=sources,
        districts=districts,
        managements=managements,
        plots=plots,
        appeal_types=appeal_types,
        topics=topics,
        results=results,
        today=today,
    )


@appeals_bp.route('/appeals/<int:appeal_id>', methods=['GET'])
@login_required
def detail(appeal_id):
    appeal = db_session.get(Appeal, appeal_id)
    if not appeal:
        abort(404)

    sources = db_session.query(Source).filter(or_(Source.is_active == True, Source.id == appeal.source_id)).order_by(Source.name).all()
    districts = db_session.query(District).filter(or_(District.is_active == True, District.id == appeal.district_id)).order_by(District.name).all()
    managements = db_session.query(Management).filter(or_(Management.is_active == True, Management.id == appeal.management_id)).order_by(Management.name).all()
    plots = db_session.query(Plot).filter(or_(Plot.is_active == True, Plot.id == appeal.plot_id)).order_by(Plot.name).all()
    appeal_types = db_session.query(AppealType).filter(or_(AppealType.is_active == True, AppealType.id == appeal.appeal_type_id)).order_by(AppealType.name).all()
    topics = db_session.query(Topic).filter(or_(Topic.is_active == True, Topic.id == appeal.topic_id)).order_by(Topic.name).all()
    results = db_session.query(Result).filter(or_(Result.is_active == True, Result.id == appeal.result_id)).order_by(Result.name).all()

    return render_template(
        'appeals/detail.html',
        appeal=appeal,
        sources=sources,
        districts=districts,
        managements=managements,
        plots=plots,
        appeal_types=appeal_types,
        topics=topics,
        results=results,
        today=date.today(),
    )


@appeals_bp.route('/appeals/<int:appeal_id>/edit', methods=['POST'])
@login_required
def edit(appeal_id):
    appeal = db_session.get(Appeal, appeal_id)
    if not appeal:
        abort(404)

    # Locking rule: If appeal is closed, editing is completely blocked!
    # "после нажатия на нее редактирование карточки не возможно"
    if appeal.is_closed:
        flash('Редактирование закрытого обращения невозможно.', 'danger')
        return redirect(url_for('appeals.detail', appeal_id=appeal.id))

    today = date.today()
    errors = []

    # 1. Дата регистрации
    reg_date_raw = request.form.get('reg_date', '').strip()
    reg_date = parse_date(reg_date_raw)
    if not reg_date:
        errors.append('Дата регистрации обязательна для заполнения (формат ДД.ММ.ГГГГ).')
    elif reg_date > today:
        errors.append(f'Дата регистрации ({format_date_eur(reg_date)}) не может быть больше текущей даты ({format_date_eur(today)}).')

    # 2. № обращения
    number = request.form.get('number', '').strip()
    if not number:
        errors.append('№ обращения обязателен для заполнения.')

    # 3. Источник поступления
    source_id = request.form.get('source_id', '').strip()
    if not source_id or not source_id.isdigit():
        errors.append('Источник поступления обязателен для выбора.')

    # 4. Округ
    district_id = request.form.get('district_id', '').strip()
    if not district_id or not district_id.isdigit():
        errors.append('Округ обязателен для выбора.')

    # 5. Управление
    management_id = request.form.get('management_id', '').strip()
    management_id_val = int(management_id) if management_id and management_id.isdigit() else None

    # 6. Участок
    plot_id = request.form.get('plot_id', '').strip()
    plot_id_val = int(plot_id) if plot_id and plot_id.isdigit() else None

    # 7. Пол заявителя
    applicant_gender = request.form.get('applicant_gender', '').strip()
    if applicant_gender and applicant_gender not in ('мужской', 'женский'):
        applicant_gender = None

    # 8. Тип обращения
    appeal_type_id = request.form.get('appeal_type_id', '').strip()
    if not appeal_type_id or not appeal_type_id.isdigit():
        errors.append('Тип обращения обязателен для выбора.')

    # 9. Тематика обращения
    topic_id = request.form.get('topic_id', '').strip()
    if not topic_id or not topic_id.isdigit():
        errors.append('Тематика обращения обязательна для выбора.')

    # 10. Обоснованность
    validity = request.form.get('validity', '').strip()
    if validity and validity not in ('обоснован', 'не обоснован'):
        validity = None

    # 11. Повторность
    recurrence = request.form.get('recurrence', '').strip()
    if recurrence and recurrence not in ('Первичное', 'Повторное', 'Многократное'):
        recurrence = None

    # 12. Результат рассмотрения
    result_id = request.form.get('result_id', '').strip()
    result_id_val = int(result_id) if result_id and result_id.isdigit() else None

    # 13. Контрольные сроки
    deadline_date_raw = request.form.get('deadline_date', '').strip()
    deadline_date = parse_date(deadline_date_raw) if deadline_date_raw else None

    # 14. Не состоит на обслуживании
    not_serviced = bool(request.form.get('not_serviced'))

    # 15. Комментарий
    comment = request.form.get('comment', '').strip()

    if errors:
        for error in errors:
            flash(error, 'danger')
        return redirect(url_for('appeals.detail', appeal_id=appeal.id))

    # Update appeal
    appeal.number = number
    appeal.reg_date = reg_date
    appeal.source_id = int(source_id)
    appeal.district_id = int(district_id)
    appeal.management_id = management_id_val
    appeal.plot_id = plot_id_val
    appeal.applicant_gender = applicant_gender or None
    appeal.appeal_type_id = int(appeal_type_id)
    appeal.topic_id = int(topic_id)
    appeal.validity = validity or None
    appeal.recurrence = recurrence or None
    appeal.result_id = result_id_val
    appeal.deadline_date = deadline_date
    appeal.not_serviced = not_serviced
    appeal.comment = comment or None

    db_session.commit()
    flash(f'Изменения в обращении №{appeal.number} успешно сохранены.', 'success')
    return redirect(url_for('appeals.detail', appeal_id=appeal.id))


@appeals_bp.route('/appeals/<int:appeal_id>/close', methods=['POST'])
@login_required
def close_appeal(appeal_id):
    """
    Кнопка закрыть обращение:
    после нажатия на нее редактирование карточки не возможно,
    в бд записывается текущая дата закрытия, статус меняется на "Закрыто"
    """
    appeal = db_session.get(Appeal, appeal_id)
    if not appeal:
        abort(404)

    if appeal.is_closed:
        flash('Обращение уже закрыто.', 'info')
        return redirect(url_for('appeals.detail', appeal_id=appeal.id))

    appeal.status = 'Закрыто'
    appeal.closed_at = datetime.now()
    appeal.closed_by_id = current_user.id
    db_session.commit()

    flash(f'Обращение №{appeal.number} успешно закрыто ({appeal.closed_at_formatted}). Редактирование карточки заблокировано.', 'success')
    return redirect(url_for('appeals.detail', appeal_id=appeal.id))
