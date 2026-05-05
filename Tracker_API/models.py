import datetime
from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column
from . import db


class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(default=lambda: datetime.datetime.now(datetime.timezone.utc))
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    member_count = db.Column(db.Integer, nullable=False, default=0)
    transaction_count = db.Column(db.Integer, nullable=False, default=0)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    members = db.relationship('User', secondary='event_members', back_populates='events', lazy=True)
    transactions = db.relationship('Transaction', backref='event', lazy=True)
    transaction_shares = db.relationship('TransactionShare', backref='event', lazy=True)

    def __init__(self, name, owner_id, description=None, member_count=0, transaction_count=0, total_amount=0):
        self.name = name
        self.owner_id = owner_id
        self.description = description
        self.member_count = member_count
        self.transaction_count = transaction_count
        self.total_amount = total_amount

    def update_total_amount(self):
        self.total_amount = sum([float(txn.amount) if txn.is_expense else 0 for txn in self.transactions])

    def update_member_count(self):
        self.member_count = len(self.members)

    def update_transaction_count(self):
        self.transaction_count = len(self.transactions)


class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    paid_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    is_expense = db.Column(db.Boolean, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(default=lambda: datetime.datetime.now(datetime.timezone.utc))
    shared_users = db.relationship('User', secondary='transaction_shares', back_populates='shared_transactions', lazy=True)

    paid_by_user = db.relationship('User', foreign_keys=[paid_by], backref='paid_transactions')
    created_by_user = db.relationship('User', foreign_keys=[created_by], backref='created_transactions')

    def __init__(self, event_id, paid_by, created_by, is_expense=True, amount=0, description=None):
        self.event_id = event_id
        self.paid_by = paid_by
        self.amount = amount
        self.description = description
        self.created_by = created_by
        self.is_expense = is_expense


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), unique=False, nullable=False)
    is_registered = db.Column(db.Boolean, nullable=False)
    
    events = db.relationship('Event', secondary='event_members', back_populates='members', lazy=True)
    shared_transactions = db.relationship('Transaction', secondary='transaction_shares', back_populates='shared_users', lazy=True)

    def __init__(self, username, name, is_registered, password_hash):
       self.username = username
       self.password_hash = password_hash
       self.name = name
       self.is_registered = is_registered


class EventMembership(db.Model):
    __tablename__ = 'event_members'
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), primary_key=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True, nullable=False)
    joined_at: Mapped[datetime.datetime] = mapped_column(default=lambda: datetime.datetime.now(datetime.timezone.utc))
    liability = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    def __init__(self, event_id, user_id, liability=0.0):
        self.event_id = event_id
        self.user_id = user_id
        self.liability = liability


class TransactionShare(db.Model):
    __tablename__ = 'transaction_shares'
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), primary_key=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True, nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=True)
    share_amount = db.Column(db.Numeric(12, 2), nullable=False)

    def __init__(self, transaction_id, user_id, share_amount, event_id=None):
        self.transaction_id = transaction_id
        self.user_id = user_id
        self.share_amount = share_amount
        self.event_id = event_id
    
