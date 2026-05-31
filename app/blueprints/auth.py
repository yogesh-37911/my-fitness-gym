"""Auth Blueprint — PIN-based login/logout."""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, Response
from werkzeug.security import check_password_hash
from ..models import Admin, Settings

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


@auth_bp.route('/manifest.json')
def manifest():
    settings = Settings.query.first()
    gym_name = settings.gym_name if settings else 'Gym Manager'
    logo_filename = settings.gym_logo if (settings and settings.gym_logo) else 'My_Fitness_Logo.png'
    
    # Generate full absolute URLs (required by some mobile platforms)
    if settings and settings.gym_logo:
        logo_url = url_for('static', filename=f'uploads/{logo_filename}', _external=True)
    else:
        logo_url = url_for('static', filename=f'uploads/My_Fitness_Logo.png', _external=True)
        
    m = {
        "short_name": gym_name,
        "name": gym_name,
        "icons": [
            {
                "src": logo_url,
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": logo_url,
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": logo_url,
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "maskable"
            }
        ],
        "start_url": url_for('auth.login', _external=True),
        "background_color": "#0A1628",
        "theme_color": "#0A1628",
        "display": "standalone",
        "orientation": "portrait"
    }
    return jsonify(m)


@auth_bp.route('/service-worker.js')
def service_worker():
    sw_code = """
    self.addEventListener('install', function(event) {
        self.skipWaiting();
    });
    self.addEventListener('activate', function(event) {
        event.waitUntil(self.clients.claim());
    });
    self.addEventListener('fetch', function(event) {
        event.respondWith(fetch(event.request));
    });
    """
    return Response(sw_code, mimetype='application/javascript')
