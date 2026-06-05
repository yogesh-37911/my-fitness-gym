"""
Gym Membership Management System
Flask Application Factory
"""

import os
from flask import Flask
from .models import db
from .blueprints.auth import auth_bp
from .blueprints.dashboard import dashboard_bp
from .blueprints.members import members_bp
from .blueprints.settings import settings_bp
from .blueprints.reports import reports_bp
from .blueprints.api import api_bp


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or os.urandom(32).hex()
    
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        # Render/Supabase PostgreSQL URLs start with postgres://, which SQLAlchemy no longer supports
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        # Supabase requires SSL — append sslmode=require if not already present
        if 'postgresql' in db_url and 'sslmode' not in db_url:
            separator = '&' if '?' in db_url else '?'
            db_url += f'{separator}sslmode=require'
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(
            app.instance_path, 'gym.db'
        )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')

    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Init extensions
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(api_bp)

    # Create tables and seed defaults
    with app.app_context():
        db.create_all()
        _seed_defaults()

    return app


def _seed_defaults():
    """Seed default admin, settings, and plans if not present."""
    from .models import Admin, Settings, MembershipPlan
    from werkzeug.security import generate_password_hash

    if not Admin.query.first():
        admin = Admin(pin_hash=generate_password_hash('1234'))
        db.session.add(admin)

    if not Settings.query.first():
        settings = Settings(
            gym_name='My Fitness gym',
            gym_logo='',
            currency='₹'
        )
        db.session.add(settings)

    if not MembershipPlan.query.first():
        plans = [
            MembershipPlan(name='1 Month', duration_months=1, bonus_months=0, category='with_cardio', price=1500),
            MembershipPlan(name='3+1 Month', duration_months=3, bonus_months=1, category='with_cardio', price=4000),
            MembershipPlan(name='6+2 Month', duration_months=6, bonus_months=2, category='with_cardio', price=7000),
            MembershipPlan(name='12+3 Month', duration_months=12, bonus_months=3, category='with_cardio', price=12000),
            MembershipPlan(name='1 Month', duration_months=1, bonus_months=0, category='without_cardio', price=1000),
            MembershipPlan(name='3+1 Month', duration_months=3, bonus_months=1, category='without_cardio', price=2800),
            MembershipPlan(name='6+2 Month', duration_months=6, bonus_months=2, category='without_cardio', price=5000),
            MembershipPlan(name='12+3 Month', duration_months=12, bonus_months=3, category='without_cardio', price=9000),
        ]
        db.session.add_all(plans)

    db.session.commit()
