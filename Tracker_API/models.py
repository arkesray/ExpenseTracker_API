import datetime
# from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, func, text, event, ForeignKeyConstraint
from . import db


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), unique=False, nullable=False)
    is_registered = db.Column(db.Boolean, nullable=False)
    
    # relationships
    events = db.relationship('Event', secondary='event_members', back_populates='members', lazy=True)

    def __init__(self, username, password_hash, name, is_registered):
       self.username = username
       self.password_hash = password_hash
       self.name = name
       self.is_registered = is_registered


class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # metrics
    member_count = db.Column(db.Integer, nullable=False, default=0)
    transaction_count = db.Column(db.Integer, nullable=False, default=0)
    total_amount = db.Column(db.Numeric(12, 6), nullable=False, default=0)

    # relationships
    created_by_user = db.relationship('User', foreign_keys=[created_by_id], backref='created_events')
    members = db.relationship('User', secondary='event_members', back_populates='events', lazy=True)
    transactions = db.relationship('Transaction', backref='event', lazy=True)
    # transaction_shares = db.relationship('TransactionShare', backref='event', lazy=True)

    def __init__(self, name, created_by_id, description=None):
        self.name = name
        self.created_by_id = created_by_id
        self.description = description
        self.member_count = 0
        self.transaction_count = 0
        self.total_amount = 0


class EventMembership(db.Model):
    __tablename__ = 'event_members'
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), primary_key=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True, nullable=False)
    joined_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    liability = db.Column(db.Numeric(12, 6), nullable=False, default=0)

    def __init__(self, event_id, user_id, liability=0.0):
        self.event_id = event_id
        self.user_id = user_id
        self.liability = liability


class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    paid_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(12, 6), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    is_expense = db.Column(db.Boolean, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # relationships
    shared_by_users = db.relationship('User', secondary='transaction_shares', backref='shared_transactions', lazy=True)
    transaction_shares = db.relationship('TransactionShare', back_populates='transaction', lazy=True)
    paid_by_user = db.relationship('User', foreign_keys=[paid_by_id], backref='paid_transactions')
    created_by_user = db.relationship('User', foreign_keys=[created_by_id], backref='created_transactions')

    __table_args__ = (
        ForeignKeyConstraint(
            ['event_id','paid_by_id'],
            ['event_members.event_id','event_members.user_id'],
            name='fk_transactions_paid_by_member',
            ondelete='RESTRICT'
        ),
        ForeignKeyConstraint(
            ['event_id','created_by_id'],
            ['event_members.event_id','event_members.user_id'],
            name='fk_transactions_created_by_member',
            ondelete='RESTRICT'
        ),
    )

    def __init__(self, event_id, paid_by_id, created_by_id, is_expense=True, amount=0, description=None):
        self.event_id = event_id
        self.paid_by_id = paid_by_id
        self.amount = amount
        self.description = description
        self.is_expense = is_expense
        self.created_by_id = created_by_id


class TransactionShare(db.Model):
    __tablename__ = 'transaction_shares'
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), primary_key=True, nullable=False)
    total_amount = db.Column(db.Numeric(12, 6), nullable=False) # DB-level trigger # temporary delete later
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True, nullable=False)
    share_amount = db.Column(db.Numeric(12, 6), nullable=False)

    # relationships
    transaction = db.relationship('Transaction', back_populates='transaction_shares', foreign_keys=[transaction_id], lazy=True)

    def __init__(self, transaction_id, user_id, share_amount):
        self.transaction_id = transaction_id
        self.user_id = user_id
        self.share_amount = share_amount
        self.total_amount = 0


# Not needed with the new trigger-based approach, but leaving here for reference if we want to do it in-app instead of DB triggers
# @event.listens_for(TransactionShare, 'before_insert')
# def _set_total_amount_before_insert(mapper, connection, target):
#     """Ensure total_amount is populated from the related Transaction on insert."""
#     try:
#         if target.total_amount and float(target.total_amount) != 0:
#             return
#     except Exception:
#         pass

#     tx = getattr(target, 'transaction', None)
#     if tx is not None and getattr(tx, 'amount', None) is not None:
#         target.total_amount = tx.amount
#         return

#     if target.transaction_id is not None:
#         res = connection.execute(text("SELECT amount FROM transactions WHERE id = :id"), {"id": target.transaction_id}).fetchone()
#         if res and res[0] is not None:
#             target.total_amount = res[0]
# @event.listens_for(EventMembership, 'after_insert')
# def _after_eventmembership_insert(mapper, connection, target):
#     connection.execute(text(
#         "UPDATE events SET member_count = COALESCE(member_count,0) + 1 WHERE id = :eid"
#     ), {"eid": target.event_id})


# @event.listens_for(EventMembership, 'after_delete')
# def _after_eventmembership_delete(mapper, connection, target):
#     connection.execute(text(
#         "UPDATE events SET member_count = GREATEST(COALESCE(member_count,0) - 1, 0) WHERE id = :eid"
#     ), {"eid": target.event_id})


# @event.listens_for(Transaction, 'after_insert')
# def _after_transaction_insert(mapper, connection, target):
#     # increment transaction_count
#     connection.execute(text(
#         "UPDATE events SET transaction_count = COALESCE(transaction_count,0) + 1 WHERE id = :eid"
#     ), {"eid": target.event_id})
#     # add to total_amount only if this is an expense
#     if getattr(target, 'is_expense', False):
#         connection.execute(text(
#             "UPDATE events SET total_amount = COALESCE(total_amount,0) + :amt WHERE id = :eid"
#         ), {"amt": str(target.amount), "eid": target.event_id})


# @event.listens_for(Transaction, 'after_delete')
# def _after_transaction_delete(mapper, connection, target):
#     # decrement transaction_count
#     connection.execute(text(
#         "UPDATE events SET transaction_count = GREATEST(COALESCE(transaction_count,0) - 1, 0) WHERE id = :eid"
#     ), {"eid": target.event_id})
#     # subtract from total_amount only if this was an expense
#     if getattr(target, 'is_expense', False):
#         connection.execute(text(
#             "UPDATE events SET total_amount = COALESCE(total_amount,0) - :amt WHERE id = :eid"
#         ), {"amt": str(target.amount), "eid": target.event_id})


# @event.listens_for(Transaction, 'before_update')
# def _before_transaction_update(mapper, connection, target):
#     # Read previous row values from the DB to compute deltas safely
#     res = connection.execute(text(
#         "SELECT amount, is_expense, event_id FROM transactions WHERE id = :id"
#     ), {"id": target.id}).fetchone()
#     if not res:
#         return
#     old_amount, old_is_expense, old_event_id = res[0], res[1], res[2]
#     new_amount = getattr(target, 'amount', None)
#     new_is_expense = getattr(target, 'is_expense', None)
#     new_event_id = getattr(target, 'event_id', None)

#     # If transaction stays within the same event
#     if old_event_id == new_event_id:
#         # both were/is expense: apply delta
#         if old_is_expense and new_is_expense:
#             delta = (new_amount - old_amount)
#             if delta:
#                 connection.execute(text(
#                     "UPDATE events SET total_amount = COALESCE(total_amount,0) + :delta WHERE id = :eid"
#                 ), {"delta": str(delta), "eid": new_event_id})
#         # changed from expense -> non-expense: subtract old amount
#         elif old_is_expense and not new_is_expense:
#             connection.execute(text(
#                 "UPDATE events SET total_amount = COALESCE(total_amount,0) - :amt WHERE id = :eid"
#             ), {"amt": str(old_amount), "eid": old_event_id})
#         # changed from non-expense -> expense: add new amount
#         elif not old_is_expense and new_is_expense:
#             connection.execute(text(
#                 "UPDATE events SET total_amount = COALESCE(total_amount,0) + :amt WHERE id = :eid"
#             ), {"amt": str(new_amount), "eid": new_event_id})
#         # transaction_count unchanged when staying in same event
#     else:
#         # moved between events: adjust counts and totals on both events
#         connection.execute(text(
#             "UPDATE events SET transaction_count = GREATEST(COALESCE(transaction_count,0) - 1, 0) WHERE id = :eid"
#         ), {"eid": old_event_id})
#         connection.execute(text(
#             "UPDATE events SET transaction_count = COALESCE(transaction_count,0) + 1 WHERE id = :eid"
#         ), {"eid": new_event_id})

#         if old_is_expense:
#             connection.execute(text(
#                 "UPDATE events SET total_amount = COALESCE(total_amount,0) - :amt WHERE id = :eid"
#             ), {"amt": str(old_amount), "eid": old_event_id})
#         if new_is_expense:
#             connection.execute(text(
#                 "UPDATE events SET total_amount = COALESCE(total_amount,0) + :amt WHERE id = :eid"
#             ), {"amt": str(new_amount), "eid": new_event_id})
