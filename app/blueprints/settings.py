"""Settings Blueprint."""

import os, shutil
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from ..models import db, Admin, Settings, MembershipPlan, Member, Payment, Notification, Attendance
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


def _resolve_sqlite_path(db_uri):
    """Return the filesystem path for a sqlite:/// URI, handling both Windows and Unix."""
    # Strip the scheme — 'sqlite:///' is 10 characters
    raw = db_uri[len('sqlite:///')]
    # On Windows the URI looks like sqlite:///C:/path/gym.db  →  raw = 'C:/path/gym.db'  (absolute)
    # Relative URI:                  sqlite:///gym.db          →  raw = 'gym.db'
    return raw


@settings_bp.route('/backup')
@login_required
def backup():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']

    if db_uri.startswith('sqlite:///'):
        # Strip 'sqlite:///' (10 chars) to get the raw path component
        raw = db_uri[10:]
        db_path = raw if os.path.isabs(raw) else os.path.join(current_app.instance_path, raw)

        backup_path = os.path.join(current_app.instance_path, 'gym_backup.db')
        try:
            shutil.copy2(db_path, backup_path)
            return send_file(backup_path, as_attachment=True, download_name='gym_backup.db')
        except Exception as e:
            flash(f'Backup failed: {str(e)}', 'danger')
            return redirect(url_for('settings.index'))

    else:
        # PostgreSQL → export to a temporary SQLite file and send it
        backup_path = os.path.join(current_app.instance_path, 'gym_backup.db')
        if os.path.exists(backup_path):
            try:
                os.remove(backup_path)
            except Exception:
                pass

        try:
            temp_engine = create_engine(f'sqlite:///{backup_path}')
            db.metadata.create_all(bind=temp_engine)

            TempSession = sessionmaker(bind=temp_engine)
            temp_session = TempSession()

            models_to_copy = [Admin, Settings, MembershipPlan, Member, Payment, Notification, Attendance]
            for model in models_to_copy:
                for item in model.query.all():
                    attrs = {c.name: getattr(item, c.name) for c in model.__table__.columns}
                    new_item = model(**attrs)
                    temp_session.add(new_item)

            temp_session.commit()
            temp_session.close()
            temp_engine.dispose()

            return send_file(backup_path, as_attachment=True, download_name='gym_backup.db')
        except Exception as e:
            flash(f'Backup failed: {str(e)}', 'danger')
            return redirect(url_for('settings.index'))


@settings_bp.route('/restore', methods=['POST'])
@login_required
def restore():
    f = request.files.get('backup_file')
    if not f or not f.filename.endswith('.db'):
        flash('Invalid backup file. Must be a .db file.', 'danger')
        return redirect(url_for('settings.index'))

    db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']

    if db_uri.startswith('sqlite:///'):
        # Resolve the live database path
        raw = db_uri[10:]
        db_path = raw if os.path.isabs(raw) else os.path.join(current_app.instance_path, raw)
        temp_path = db_path + '.tmp_restore'

        try:
            # Save upload to a temp file first so a corrupt upload can't destroy the live DB
            f.save(temp_path)

            # Validate it is a real SQLite database
            with open(temp_path, 'rb') as chk:
                header = chk.read(16)
            if not header.startswith(b'SQLite format 3'):
                os.remove(temp_path)
                flash('Invalid backup: the file is not a valid SQLite database.', 'danger')
                return redirect(url_for('settings.index'))

            # Release all SQLAlchemy connections so Windows does not lock the file
            db.session.remove()
            db.engine.dispose()

            # Atomically replace the live database
            shutil.move(temp_path, db_path)
            flash('Database restored successfully!', 'success')
        except Exception as e:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            flash(f'Restore failed: {str(e)}', 'danger')

        return redirect(url_for('settings.index'))

    else:
        # PostgreSQL → read from the uploaded SQLite file and insert into Postgres
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        temp_path = os.path.join(current_app.instance_path, 'temp_restore.db')
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        f.save(temp_path)

        # Validate the uploaded file
        try:
            with open(temp_path, 'rb') as chk:
                header = chk.read(16)
            if not header.startswith(b'SQLite format 3'):
                os.remove(temp_path)
                flash('Invalid backup: the file is not a valid SQLite database.', 'danger')
                return redirect(url_for('settings.index'))
        except Exception as e:
            flash(f'Restore failed during validation: {str(e)}', 'danger')
            return redirect(url_for('settings.index'))

        try:
            temp_engine = create_engine(f'sqlite:///{temp_path}')
            TempSession = sessionmaker(bind=temp_engine)
            temp_session = TempSession()

            # Clear existing data in reverse FK order
            Attendance.query.delete()
            Notification.query.delete()
            Payment.query.delete()
            Member.query.delete()
            MembershipPlan.query.delete()
            Settings.query.delete()
            Admin.query.delete()
            db.session.flush()

            # Insert from backup in dependency order
            models_to_restore = [Admin, Settings, MembershipPlan, Member, Payment, Notification, Attendance]
            for model in models_to_restore:
                items = temp_session.query(model).all()
                for item in items:
                    attrs = {c.name: getattr(item, c.name) for c in model.__table__.columns}
                    new_item = model(**attrs)
                    db.session.add(new_item)

            db.session.commit()
            temp_session.close()
            temp_engine.dispose()

            flash('Database restored successfully from backup!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Restore failed: {str(e)}', 'danger')
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

        return redirect(url_for('settings.index'))


@settings_bp.route('/toggle-dark', methods=['POST'])
@login_required
def toggle_dark():
    settings = Settings.query.first()
    settings.dark_mode = not settings.dark_mode
    db.session.commit()
    return redirect(request.referrer or url_for('dashboard.index'))
