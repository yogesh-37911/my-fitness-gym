"""
Database Models — SQLAlchemy ORM
"""

from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Admin(db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    pin_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Settings(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    gym_name = db.Column(db.String(100), default='My Fitness gym')
    gym_logo = db.Column(db.String(255), default='')
    currency = db.Column(db.String(10), default='₹')
    dark_mode = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MembershipPlan(db.Model):
    __tablename__ = 'membership_plans'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    duration_months = db.Column(db.Integer, nullable=False)
    bonus_months = db.Column(db.Integer, default=0)
    category = db.Column(db.String(30), nullable=False)  # with_cardio / without_cardio
    price = db.Column(db.Float, nullable=False)

    @property
    def total_months(self):
        return self.duration_months + self.bonus_months

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'duration_months': self.duration_months,
            'bonus_months': self.bonus_months,
            'total_months': self.total_months,
            'category': self.category,
            'price': self.price
        }


class Member(db.Model):
    __tablename__ = 'members'
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.String(20), unique=True, nullable=False)  # GYM0001
    full_name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15), nullable=False)
    emergency_contact = db.Column(db.String(15))
    address = db.Column(db.Text)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    date_of_birth = db.Column(db.Date)

    # Membership
    plan_id = db.Column(db.Integer, db.ForeignKey('membership_plans.id'), nullable=False)
    joining_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)

    # Payment
    total_fee = db.Column(db.Float, nullable=False)
    amount_paid = db.Column(db.Float, default=0)

    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    plan = db.relationship('MembershipPlan', backref='members')
    payments = db.relationship('Payment', backref='member', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='member', lazy=True, cascade='all, delete-orphan')
    attendances = db.relationship('Attendance', backref='member', lazy=True, cascade='all, delete-orphan')

    @property
    def due_amount(self):
        return max(0, self.total_fee - self.amount_paid)

    @property
    def payment_status(self):
        if self.amount_paid <= 0:
            return 'Unpaid'
        elif self.due_amount > 0:
            return 'Partially Paid'
        return 'Fully Paid'

    @property
    def days_remaining(self):
        delta = self.expiry_date - date.today()
        return delta.days

    @property
    def status(self):
        if self.expiry_date < date.today():
            return 'Expired'
        elif self.days_remaining <= 20:
            return 'Expiring Soon'
        return 'Active'

    def to_dict(self):
        return {
            'id': self.id,
            'member_id': self.member_id,
            'full_name': self.full_name,
            'mobile': self.mobile,
            'emergency_contact': self.emergency_contact,
            'address': self.address,
            'age': self.age,
            'gender': self.gender,
            'plan_id': self.plan_id,
            'plan_name': self.plan.name if self.plan else '',
            'plan_category': self.plan.category if self.plan else '',
            'joining_date': self.joining_date.isoformat(),
            'expiry_date': self.expiry_date.isoformat(),
            'total_fee': self.total_fee,
            'amount_paid': self.amount_paid,
            'due_amount': self.due_amount,
            'payment_status': self.payment_status,
            'days_remaining': self.days_remaining,
            'status': self.status,
            'is_active': self.is_active,
        }


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, default=date.today)
    note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    days_before = db.Column(db.Integer)
    is_read = db.Column(db.Boolean, default=False)
    is_paused = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    check_in = db.Column(db.DateTime, default=datetime.utcnow)
    check_out = db.Column(db.DateTime)
