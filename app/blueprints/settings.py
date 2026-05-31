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


@settings_bp.route('/backup')
@login_required
def backup():
    from flask import current_app
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
    
    # If using local SQLite database, we can just copy the file directly
    if db_uri.startswith('sqlite:///'):
        db_path = db_uri.replace('sqlite:///', '')
        # Handle relative paths for SQLite
        if not os.path.isabs(db_path):
            db_path = os.path.join(current_app.instance_path, db_path)
            
        backup_path = os.path.join(current_app.instance_path, 'gym_backup.db')
        try:
            shutil.copy2(db_path, backup_path)
            return send_file(backup_path, as_attachment=True, download_name='gym_backup.db')
        except Exception as e:
            flash(f'Backup failed: {str(e)}', 'danger')
            return redirect(url_for('settings.index'))
            
    # If using PostgreSQL, compile a SQLite database on the fly and stream it
    else:
        backup_path = os.path.join(current_app.instance_path, 'gym_backup.db')
        # Remove existing backup file if it exists to start fresh
        if os.path.exists(backup_path):
            try:
                os.remove(backup_path)
            except Exception:
                pass
            
        try:
            # Create a temporary SQLite engine and create all tables
            temp_engine = create_engine(f'sqlite:///{backup_path}')
            db.metadata.create_all(bind=temp_engine)
            
            TempSession = sessionmaker(bind=temp_engine)
            temp_session = TempSession()
            
            # Copy all data from primary DB (Postgres) to temp SQLite DB
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
    
    # If primary DB is SQLite, we can just replace the file
    if db_uri.startswith('sqlite:///'):
        db_path = db_uri.replace('sqlite:///', '')
        if not os.path.isabs(db_path):
            db_path = os.path.join(current_app.instance_path, db_path)
        try:
            # Ensure DB connection is closed or we just save over it (Flask-SQLAlchemy handles reconnects)
            db.session.remove()
            f.save(db_path)
            flash('Database restored successfully! Please restart the app if changes do not appear.', 'success')
        except Exception as e:
            flash(f'Restore failed: {str(e)}', 'danger')
            
    # If primary DB is PostgreSQL, import the SQLite file data into Postgres
    else:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # Save uploaded SQLite file to a temporary location
        temp_path = os.path.join(current_app.instance_path, 'temp_restore.db')
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        f.save(temp_path)
        
        try:
            # Connect to the uploaded SQLite file
            temp_engine = create_engine(f'sqlite:///{temp_path}')
            TempSession = sessionmaker(bind=temp_engine)
            temp_session = TempSession()
            
            # Clear PostgreSQL database in reverse order of foreign keys
            Attendance.query.delete()
            Notification.query.delete()
            Payment.query.delete()
            Member.query.delete()
            MembershipPlan.query.delete()
            Settings.query.delete()
            Admin.query.delete()
            db.session.flush()
            
            # Read from SQLite and insert into PostgreSQL in dependency order
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


@settings_bp.route('/toggle-dark', methods=['POST'])
@login_required
def toggle_dark():
    settings = Settings.query.first()
    settings.dark_mode = not settings.dark_mode
    db.session.commit()
    return redirect(request.referrer or url_for('dashboard.index'))
