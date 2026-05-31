"""Dashboard Blueprint."""

from datetime import date, timedelta
from flask import Blueprint, render_template, session, redirect, url_for
from ..models import db, Member, Notification, Settings
from ..blueprints.auth import login_required
from sqlalchemy import func

dashboard_bp = Blueprint('dashboard', __name__)


def generate_notifications():
    """Auto-generate expiry notifications."""
    thresholds = [20, 15, 10, 5, 1]
    today = date.today()
    members = Member.query.filter(Member.is_active == True).all()
    for member in members:
        days = member.days_remaining
        if days in thresholds:
            # Avoid duplicates
            existing = Notification.query.filter_by(
                member_id=member.id, days_before=days, is_read=False
            ).first()
            if not existing:
                msg = f"{member.full_name}'s membership expires in {days} day{'s' if days > 1 else ''}!"
                notif = Notification(member_id=member.id, message=msg, days_before=days)
                db.session.add(notif)
    db.session.commit()


@dashboard_bp.route('/dashboard')
@login_required
def index():
    generate_notifications()

    today = date.today()
    settings = Settings.query.first()

    total = Member.query.count()
    active = Member.query.filter(Member.expiry_date >= today).count()
    expired = Member.query.filter(Member.expiry_date < today).count()
    expiring_soon = Member.query.filter(
        Member.expiry_date >= today,
        Member.expiry_date <= today + timedelta(days=20)
    ).count()

    # Revenue
    from sqlalchemy import extract
    monthly_revenue = db.session.query(func.sum(Member.amount_paid)).filter(
        extract('year', Member.joining_date) == today.year,
        extract('month', Member.joining_date) == today.month
    ).scalar() or 0

    pending_fees = db.session.query(
        func.sum(Member.total_fee - Member.amount_paid)
    ).scalar() or 0

    recent = Member.query.order_by(Member.created_at.desc()).limit(5).all()
    notifications = Notification.query.filter_by(is_read=False, is_paused=False)\
        .order_by(Notification.created_at.desc()).limit(10).all()

    # Today's birthdays
    birthdays = Member.query.filter(
        extract('month', Member.date_of_birth) == today.month,
        extract('day', Member.date_of_birth) == today.day
    ).all() if today else []

    # Revenue chart data (last 6 months)
    chart_labels = []
    chart_data = []
    for i in range(5, -1, -1):
        d = today.replace(day=1) - timedelta(days=i*30)
        label = d.strftime('%b %Y')
        rev = db.session.query(func.sum(Member.amount_paid)).filter(
            extract('year', Member.joining_date) == d.year,
            extract('month', Member.joining_date) == d.month
        ).scalar() or 0
        chart_labels.append(label)
        chart_data.append(float(rev))

    return render_template('dashboard/index.html',
        settings=settings,
        total=total,
        active=active,
        expired=expired,
        expiring_soon=expiring_soon,
        monthly_revenue=monthly_revenue,
        pending_fees=pending_fees,
        recent=recent,
        notifications=notifications,
        birthdays=birthdays,
        chart_labels=chart_labels,
        chart_data=chart_data,
        unread_count=len(notifications)
    )
