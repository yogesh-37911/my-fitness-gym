"""Members Blueprint — CRUD, profile, attendance."""

from datetime import date
from dateutil.relativedelta import relativedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from ..models import db, Member, MembershipPlan, Payment, Attendance, Settings, Notification
from ..blueprints.auth import login_required
import qrcode, io, base64

members_bp = Blueprint('members', __name__, url_prefix='/members')


def _next_member_id():
    last = Member.query.order_by(Member.id.desc()).first()
    if last and last.member_id:
        # Extract numeric part from e.g. 'GYM0005' -> 5, then increment
        import re
        match = re.search(r'\d+', last.member_id)
        num = int(match.group()) + 1 if match else 1
    else:
        num = 1
    return f'GYM{num:04d}'


def _calc_expiry(joining: date, plan: MembershipPlan) -> date:
    return joining + relativedelta(months=plan.total_months)


@members_bp.route('/')
@login_required
def list_members():
    q = request.args.get('q', '').strip()
    f = request.args.get('filter', 'all')
    today = date.today()

    query = Member.query
    if q:
        query = query.filter(
            (Member.full_name.ilike(f'%{q}%')) |
            (Member.mobile.ilike(f'%{q}%')) |
            (Member.member_id.ilike(f'%{q}%'))
        )
    if f == 'active':
        query = query.filter(Member.expiry_date >= today)
    elif f == 'expired':
        query = query.filter(Member.expiry_date < today)
    elif f == 'expiring':
        from datetime import timedelta
        query = query.filter(Member.expiry_date >= today,
                             Member.expiry_date <= today + __import__('datetime').timedelta(days=20))
    elif f == 'fully_paid':
        query = query.filter(Member.amount_paid >= Member.total_fee)
    elif f == 'partial':
        query = query.filter(Member.amount_paid < Member.total_fee, Member.amount_paid > 0)
    elif f == 'unpaid':
        query = query.filter(Member.amount_paid == 0)
    elif f == 'with_cardio':
        query = query.join(MembershipPlan).filter(MembershipPlan.category == 'with_cardio')
    elif f == 'without_cardio':
        query = query.join(MembershipPlan).filter(MembershipPlan.category == 'without_cardio')

    members = query.order_by(Member.created_at.desc()).all()
    settings = Settings.query.first()
    return render_template('members/list.html', members=members, q=q, filter=f, settings=settings)


@members_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_member():
    plans = MembershipPlan.query.all()
    settings = Settings.query.first()

    if request.method == 'POST':
        try:
            f = request.form

            # Validate plan_id — hidden input so HTML 'required' doesn't enforce it
            plan_id_raw = f.get('plan_id', '').strip()
            if not plan_id_raw:
                flash('Please select a membership plan.', 'danger')
                return render_template('members/add.html', plans=plans, settings=settings, today=date.today().isoformat())

            plan = MembershipPlan.query.get_or_404(int(plan_id_raw))
            joining = date.fromisoformat(f['joining_date'])
            expiry = _calc_expiry(joining, plan)

            total_fee = float(f.get('total_fee') or plan.price)
            amount_paid = float(f.get('amount_paid') or 0)

            dob = None
            if f.get('date_of_birth'):
                try:
                    dob = date.fromisoformat(f['date_of_birth'])
                except Exception:
                    pass

            member = Member(
                member_id=_next_member_id(),
                full_name=f['full_name'].strip(),
                mobile=f['mobile'].strip(),
                emergency_contact=f.get('emergency_contact', '').strip(),
                address=f.get('address', '').strip(),
                age=int(f['age']) if f.get('age') else None,
                gender=f.get('gender', ''),
                date_of_birth=dob,
                plan_id=plan.id,
                joining_date=joining,
                expiry_date=expiry,
                total_fee=total_fee,
                amount_paid=amount_paid,
            )
            db.session.add(member)
            db.session.flush()

            if amount_paid > 0:
                payment = Payment(member_id=member.id, amount=amount_paid, note='Initial payment')
                db.session.add(payment)

            db.session.commit()
            flash(f'Member {member.member_id} added successfully!', 'success')
            return redirect(url_for('members.profile', member_id=member.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding member: {str(e)}', 'danger')

    return render_template('members/add.html', plans=plans, settings=settings, today=date.today().isoformat())


@members_bp.route('/<int:member_id>')
@login_required
def profile(member_id):
    member = Member.query.get_or_404(member_id)
    settings = Settings.query.first()

    # Generate QR code
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(f'Member: {member.member_id}\nName: {member.full_name}\nMobile: {member.mobile}')
    qr.make(fit=True)
    img = qr.make_image(fill_color='#0a1628', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    attendance = Attendance.query.filter_by(member_id=member_id).order_by(Attendance.check_in.desc()).limit(10).all()
    payments = Payment.query.filter_by(member_id=member_id).order_by(Payment.payment_date.desc()).all()

    return render_template('members/profile.html', member=member, settings=settings,
                           qr_b64=qr_b64, attendance=attendance, payments=payments)


@members_bp.route('/<int:member_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_member(member_id):
    member = Member.query.get_or_404(member_id)
    plans = MembershipPlan.query.all()
    settings = Settings.query.first()

    if request.method == 'POST':
        f = request.form
        plan = MembershipPlan.query.get_or_404(int(f['plan_id']))
        joining = date.fromisoformat(f['joining_date'])
        expiry = _calc_expiry(joining, plan)

        member.full_name = f['full_name'].strip()
        member.mobile = f['mobile'].strip()
        member.emergency_contact = f.get('emergency_contact', '').strip()
        member.address = f.get('address', '').strip()
        member.age = int(f['age']) if f.get('age') else None
        member.gender = f.get('gender', '')
        member.plan_id = plan.id
        member.joining_date = joining
        member.expiry_date = expiry
        member.total_fee = float(f.get('total_fee', plan.price))
        member.amount_paid = float(f.get('amount_paid', 0))

        if f.get('date_of_birth'):
            try:
                member.date_of_birth = date.fromisoformat(f['date_of_birth'])
            except Exception:
                pass

        db.session.commit()
        flash('Member updated successfully!', 'success')
        return redirect(url_for('members.profile', member_id=member.id))

    return render_template('members/edit.html', member=member, plans=plans,
                           settings=settings)


@members_bp.route('/<int:member_id>/delete', methods=['POST'])
@login_required
def delete_member(member_id):
    member = Member.query.get_or_404(member_id)
    db.session.delete(member)
    db.session.commit()
    flash(f'Member {member.member_id} deleted.', 'info')
    return redirect(url_for('members.list_members'))


@members_bp.route('/<int:member_id>/pay', methods=['POST'])
@login_required
def add_payment(member_id):
    member = Member.query.get_or_404(member_id)
    amount = float(request.form.get('amount', 0))
    if amount > 0:
        member.amount_paid = min(member.amount_paid + amount, member.total_fee)
        payment = Payment(member_id=member_id, amount=amount, note=request.form.get('note', ''))
        db.session.add(payment)
        db.session.commit()
        flash(f'Payment of ₹{amount:.0f} recorded.', 'success')
    return redirect(url_for('members.profile', member_id=member_id))


@members_bp.route('/<int:member_id>/checkin', methods=['POST'])
@login_required
def checkin(member_id):
    member = Member.query.get_or_404(member_id)
    # Check if already checked in today
    from datetime import datetime
    today_start = datetime.combine(date.today(), datetime.min.time())
    existing = Attendance.query.filter(
        Attendance.member_id == member_id,
        Attendance.check_in >= today_start,
        Attendance.check_out == None
    ).first()
    if existing:
        existing.check_out = datetime.utcnow()
        flash('Checked out!', 'info')
    else:
        att = Attendance(member_id=member_id)
        db.session.add(att)
        flash('Checked in!', 'success')
    db.session.commit()
    return redirect(url_for('members.profile', member_id=member_id))


@members_bp.route('/renew/<int:member_id>', methods=['GET', 'POST'])
@login_required
def renew(member_id):
    member = Member.query.get_or_404(member_id)
    plans = MembershipPlan.query.all()
    settings = Settings.query.first()

    if request.method == 'POST':
        f = request.form
        plan = MembershipPlan.query.get_or_404(int(f['plan_id']))
        new_joining = date.fromisoformat(f['joining_date'])
        new_expiry = _calc_expiry(new_joining, plan)

        member.plan_id = plan.id
        member.joining_date = new_joining
        member.expiry_date = new_expiry
        member.total_fee = float(f.get('total_fee', plan.price))
        member.amount_paid = float(f.get('amount_paid', 0))

        # Clear old notifications
        Notification.query.filter_by(member_id=member_id).delete()

        if member.amount_paid > 0:
            payment = Payment(member_id=member_id, amount=member.amount_paid, note='Renewal payment')
            db.session.add(payment)

        db.session.commit()
        flash('Membership renewed!', 'success')
        return redirect(url_for('members.profile', member_id=member_id))

    return render_template('members/renew.html', member=member, plans=plans,
                           settings=settings, today=date.today().isoformat())
