"""Auth Blueprint — PIN-based login/logout."""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from ..models import Admin

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@auth_bp.route('/', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('dashboard.index'))

    error = None
    if request.method == 'POST':
        pin = request.form.get('pin', '').strip()
        admin = Admin.query.first()
        if admin and check_password_hash(admin.pin_hash, pin):
            session['logged_in'] = True
            session.permanent = True
            return redirect(url_for('dashboard.index'))
        else:
            error = 'Incorrect PIN. Please try again.'

    return render_template('auth/login.html', error=error)


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
