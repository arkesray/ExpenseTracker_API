import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Integer, String, Boolean, Numeric, DateTime, func, text, event, ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload
from sqlalchemy.ext.associationproxy import association_proxy
from . import db


class User(db.Model):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_registered: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))

    # relationships
    events: Mapped[List['Event']] = relationship('Event', secondary='event_members', back_populates='members', lazy='selectin')
    # association-proxy to expose transactions a user participates in via TransactionShare
    # shared_transactions = association_proxy('transaction_shares', 'transaction')

    # memberships: Mapped[List['EventMembership']] = relationship('EventMembership', back_populates='user', lazy='selectin', cascade='all, delete-orphan')
    # transaction_shares: Mapped[List['TransactionShare']] = relationship('TransactionShare', back_populates='user', lazy='selectin', cascade='all, delete-orphan')
    # created_events: Mapped[List['Event']] = relationship('Event', back_populates='created_by_user', lazy='selectin')
    # created_transactions: Mapped[List['Transaction']] = relationship('Transaction', back_populates='created_by_user', lazy='selectin')
    # paid_transactions: Mapped[List['Transaction']] = relationship('Transaction', back_populates='paid_by_user', lazy='selectin')


    def __init__(self, username: str, password_hash: str, name: str, is_registered: bool = False) -> None:
        self.username = username
        self.password_hash = password_hash
        self.name = name
        self.is_registered = is_registered


class Event(db.Model):
    __tablename__ = 'events'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False, index=True)

    # metrics (DB-level defaults for production)
    member_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    transaction_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, server_default=text('0'))

    # relationships
    # created_by_user: Mapped['User'] = relationship('User', foreign_keys=[created_by_id], back_populates='created_events', lazy='selectin')
    created_by_user: Mapped['User'] = relationship('User', foreign_keys=[created_by_id], lazy='selectin')
    members: Mapped[List['User']] = relationship('User', secondary='event_members', back_populates='events', lazy='selectin')
    transactions: Mapped[List['Transaction']] = relationship('Transaction', back_populates='event', lazy='selectin')
    # memberships: Mapped[List['EventMembership']] = relationship('EventMembership', back_populates='event', lazy='selectin', cascade='all, delete-orphan')

    def __init__(self, name: str, created_by_id: int, description: Optional[str] = None) -> None:
        self.name = name
        self.created_by_id = created_by_id
        self.description = description
        self.member_count = 0
        self.transaction_count = 0
        self.total_amount = 0


class EventMembership(db.Model):
    __tablename__ = 'event_members'
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey('events.id', ondelete='RESTRICT'), primary_key=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), primary_key=True, nullable=False)
    joined_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    liability: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, server_default=text('0'))

    # relationships for easier navigation
    # user: Mapped['User'] = relationship('User', foreign_keys=[user_id], back_populates='memberships', lazy='joined')
    user: Mapped['User'] = relationship('User', foreign_keys=[user_id], lazy='joined', overlaps="events,members")
    # event: Mapped['Event'] = relationship('Event', foreign_keys=[event_id], back_populates='memberships', lazy='joined')
    event: Mapped['Event'] = relationship('Event', foreign_keys=[event_id], lazy='joined', overlaps="events,members")

    def __init__(self, event_id: int, user_id: int, liability: float = 0.0) -> None:
        self.event_id = event_id
        self.user_id = user_id
        self.liability = liability


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey('events.id', ondelete='RESTRICT'), nullable=False, index=True)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    paid_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_expense: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # relationships
    # association-proxy to expose users who share this transaction through TransactionShare
    shared_by_users = association_proxy('transaction_shares', 'user')
    # paid_by_user: Mapped['User'] = relationship('User', foreign_keys=[paid_by_id], back_populates='paid_transactions', lazy='selectin')
    paid_by_user: Mapped['User'] = relationship('User', foreign_keys=[paid_by_id], lazy='selectin')
    # created_by_user: Mapped['User'] = relationship('User', foreign_keys=[created_by_id], back_populates='created_transactions', lazy='selectin')
    created_by_user: Mapped['User'] = relationship('User', foreign_keys=[created_by_id], lazy='selectin')
    transaction_shares: Mapped[List['TransactionShare']] = relationship('TransactionShare', back_populates='transaction', lazy='selectin')
    event: Mapped['Event'] = relationship('Event', back_populates='transactions', lazy='selectin')

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

    def __init__(self, event_id: int, paid_by_id: int, created_by_id: int, is_expense: bool = True, amount: Decimal | float = 0, description: Optional[str] = None) -> None:
        self.event_id = event_id
        self.paid_by_id = paid_by_id
        self.amount = Decimal(amount)
        self.description = description
        self.is_expense = is_expense
        self.created_by_id = created_by_id

    def add_share(self, user: 'User', amount: Decimal | float) -> 'TransactionShare':
        """Convenience helper to add a TransactionShare for this transaction.

        Example:
            tx.add_share(user_obj, Decimal('12.34'))
        """
        ts = TransactionShare(transaction=self, user=user, share_amount=Decimal(amount))
        self.transaction_shares.append(ts)
        return ts

    @staticmethod
    def list_with_shares(session):
        """Return all transactions with their shares and share users eager-loaded to avoid N+1."""
        return session.query(Transaction).options(
            selectinload(Transaction.transaction_shares).selectinload(TransactionShare.user)
        ).all()


class TransactionShare(db.Model):
    __tablename__ = 'transaction_shares'

    transaction_id: Mapped[int] = mapped_column(Integer, ForeignKey('transactions.id', ondelete='RESTRICT'), primary_key=True, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)  # DB-level trigger / temporary
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), primary_key=True, nullable=False)
    share_amount: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)

    # relationships
    transaction: Mapped['Transaction'] = relationship('Transaction', back_populates='transaction_shares', foreign_keys=[transaction_id], lazy='selectin')
    # user: Mapped['User'] = relationship('User', back_populates='transaction_shares', foreign_keys=[user_id], lazy='joined')
    user: Mapped['User'] = relationship('User', foreign_keys=[user_id], lazy='joined')

    def __init__(
        self,
        transaction_id: Optional[int] = None,
        user_id: Optional[int] = None,
        share_amount: Decimal | float = 0,
        transaction: Optional['Transaction'] = None,
        user: Optional['User'] = None,
    ) -> None:
        # allow creation by ids or by objects; SQLAlchemy will handle relationship syncing
        if transaction is not None:
            self.transaction = transaction
        elif transaction_id is not None:
            self.transaction_id = transaction_id

        if user is not None:
            self.user = user
        elif user_id is not None:
            self.user_id = user_id

        self.share_amount = Decimal(share_amount)
        self.total_amount = Decimal(0)


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
