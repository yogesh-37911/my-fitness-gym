"""API Blueprint — JSON endpoints for AJAX."""

from flask import Blueprint, jsonify, request, session
from ..models import db, Notification, MembershipPlan, Member
from ..blueprints.auth import login_required

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/notifications/read/<int:notif_id>', methods=['POST'])
@login_required
def mark_read(notif_id):
    n = Notification.query.get_or_404(notif_id)
    n.is_read = True
    db.session.commit()
    return jsonify({'ok': True})


@api_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_read():
    Notification.query.filter_by(is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'ok': True})


@api_bp.route('/notifications/pause/<int:notif_id>', methods=['POST'])
@login_required
def pause_notif(notif_id):
    n = Notification.query.get_or_404(notif_id)
    n.is_paused = True
    db.session.commit()
    return jsonify({'ok': True})


@api_bp.route('/notifications/delete/<int:notif_id>', methods=['POST'])
@login_required
def delete_notif(notif_id):
    n = Notification.query.get_or_404(notif_id)
    db.session.delete(n)
    db.session.commit()
    return jsonify({'ok': True})


@api_bp.route('/plans')
@login_required
def get_plans():
    category = request.args.get('category', 'with_cardio')
    plans = MembershipPlan.query.filter_by(category=category).all()
    return jsonify([p.to_dict() for p in plans])


@api_bp.route('/members/search')
@login_required
def search_members():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    members = Member.query.filter(
        (Member.full_name.ilike(f'%{q}%')) |
        (Member.mobile.ilike(f'%{q}%')) |
        (Member.member_id.ilike(f'%{q}%'))
    ).limit(10).all()
    return jsonify([{
        'id': m.id,
        'member_id': m.member_id,
        'full_name': m.full_name,
        'mobile': m.mobile,
        'status': m.status
    } for m in members])
