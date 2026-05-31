"""Settings Blueprint."""

import os, shutil
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from ..models import db, Admin, Settings, MembershipPlan
from ..blueprints.auth import login_required

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('/')
@login_required
def index():
    settings = Settings.query.first()
    plans = MembershipPlan.query.all()
    return render_template('settings/index.html', settings=settings, plans=plans)


@settings_bp.route('/update-gym', methods=['POST'])
@login_required
def update_gym():
    settings = Settings.query.first()
    settings.gym_name = request.form.get('gym_name', settings.gym_name).strip()

    logo = request.files.get('gym_logo')
    if logo and logo.filename:
        filename = secure_filename(logo.filename)
        path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        logo.save(path)
        settings.gym_logo = filename

    db.session.commit()
    flash('Gym info updated!', 'success')
    return redirect(url_for('settings.index'))


@settings_bp.route('/change-pin', methods=['POST'])
@login_required
def change_pin():
    new_pin = request.form.get('new_pin', '').strip()
    confirm_pin = request.form.get('confirm_pin', '').strip()
    if not new_pin or len(new_pin) < 4:
        flash('PIN must be at least 4 digits.', 'danger')
    elif new_pin != confirm_pin:
        flash('PINs do not match.', 'danger')
    else:
        admin = Admin.query.first()
        admin.pin_hash = generate_password_hash(new_pin)
        db.session.commit()
        flash('PIN changed successfully!', 'success')
    return redirect(url_for('settings.index'))


@settings_bp.route('/update-prices', methods=['POST'])
@login_required
def update_prices():
    for plan in MembershipPlan.query.all():
        key = f'plan_{plan.id}'
        if key in request.form:
            try:
                plan.price = float(request.form[key])
            except ValueError:
                pass
    db.session.commit()
    flash('Prices updated!', 'success')
    return redirect(url_for('settings.index'))


@settings_bp.route('/backup')
@login_required
def backup():
    from flask import current_app
    db_path = os.path.join(current_app.instance_path, 'gym.db')
    backup_path = os.path.join(current_app.instance_path, 'gym_backup.db')
    shutil.copy2(db_path, backup_path)
    return send_file(backup_path, as_attachment=True, download_name='gym_backup.db')


@settings_bp.route('/restore', methods=['POST'])
@login_required
def restore():
    f = request.files.get('backup_file')
    if f and f.filename.endswith('.db'):
        db_path = os.path.join(current_app.instance_path, 'gym.db')
        f.save(db_path)
        flash('Database restored! Please restart the app.', 'success')
    else:
        flash('Invalid backup file.', 'danger')
    return redirect(url_for('settings.index'))


@settings_bp.route('/toggle-dark', methods=['POST'])
@login_required
def toggle_dark():
    settings = Settings.query.first()
    settings.dark_mode = not settings.dark_mode
    db.session.commit()
    return redirect(request.referrer or url_for('dashboard.index'))
