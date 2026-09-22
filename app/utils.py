from functools import wraps
from datetime import datetime, date
from flask import flash, redirect, url_for, abort
from flask_login import current_user


def superadmin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_superadmin:
            flash('Доступ запрещен. Требуются права супер-администратора.', 'danger')
            return redirect(url_for('appeals.index'))
        return f(*args, **kwargs)
    return decorated_function


def parse_date(date_str):
    """
    Parses a date string in DD.MM.YYYY or YYYY-MM-DD format.
    Returns datetime.date or None.
    """
    if not date_str or not date_str.strip():
        return None
    date_str = date_str.strip()
    for fmt in ('%d.%m.%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            pass
    return None


def format_date_eur(d):
    """Formats a date object or string into European DD.MM.YYYY."""
    if not d:
        return ''
    if isinstance(d, (datetime, date)):
        return d.strftime('%d.%m.%Y')
    parsed = parse_date(str(d))
    if parsed:
        return parsed.strftime('%d.%m.%Y')
    return str(d)
