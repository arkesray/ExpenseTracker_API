import datetime
from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column
from . import db

class tbl_events(db.Model):
    __tablename___ = 'tbl_events'
    EventID = db.Column(db.Integer, primary_key=True)
    EventName = db.Column(db.String(10), unique=True, nullable=False)
    EventDescription = db.Column(db.String(100), nullable=True)
    # EventTime = db.Column(db.DateTime(timezone=True), nullable=False,)
    EventTime: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.now(datetime.UTC))
    EventOwner = db.Column(db.Integer, db.ForeignKey('tbl_users.id'), nullable=False)
    
    #event dynamics
    NumberOfMembers = db.Column(db.Integer, nullable=False)
    NumberOfTxns = db.Column(db.Integer, nullable=False)
    TotalExpense = db.Column(db.Float, nullable=False)
    event_users = db.relationship('tbl_users', secondary='tbl_eventusers', back_populates='user_events', lazy=True)
    txns = db.relationship('tbl_tlist', backref='txn_event', lazy=True)
    event_txnShare = db.relationship('tbl_txnshare', backref='txnShare_event', lazy=True)

    def __init__(self, EventName, EventOwner, EventDescription=None,
                  NumberOfMembers=0, NumberOfTxns=0, TotalExpense=0.0):
        self.EventName = EventName
        self.EventOwner = EventOwner
        self.EventDescription = EventDescription
        self.NumberOfMembers = NumberOfMembers
        self.NumberOfTxns = NumberOfTxns
        self.TotalExpense = TotalExpense
    
    def updateTotalExpense(self,):
        self.TotalExpense = sum([txn.Amount if txn.isExpense else 0 for txn in self.txns])

    def updateTotalMembers(self,):
        self.NumberOfMembers = len(self.event_users)
    
    def updateTotalTxns(self,):
        self.NumberOfTxns = len(self.txns)


class tbl_tlist(db.Model):
    __tablename___ = 'tbl_tlist'
    TxnID = db.Column(db.Integer, primary_key=True)
    EventID = db.Column(db.Integer, db.ForeignKey('tbl_events.EventID'), nullable=False) #txn_event
    paidByUserID = db.Column(db.Integer, db.ForeignKey('tbl_users.id'), nullable=False) #txn_paidUser
    createdByUserID = db.Column(db.Integer, db.ForeignKey('tbl_users.id'), nullable=False) #txn_createdUser
    Amount = db.Column(db.Float, nullable=False)
    TxnDescription = db.Column(db.String(100), nullable=True)
    isExpense = db.Column(db.Boolean, nullable=False)
    # TxnTime = db.Column(db.DateTime(timezone=True), nullable=False)
    TxnTime: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.now(datetime.UTC))
    shared_users = db.relationship('tbl_users', secondary='tbl_txnshare', back_populates='user_txnShares', lazy=True)

    def __init__(self, EventID, paidByUserID, createdByUserID, isExpense=True, Amount=0,
                    TxnDescription=None,):
        self.EventID = EventID
        self.paidByUserID = paidByUserID
        self.Amount = Amount
        self.TxnDescription = TxnDescription
        self.createdByUserID = createdByUserID
        self.isExpense = isExpense


class tbl_users(UserMixin, db.Model):
    __tablename___ = 'tbl_users'
    id = db.Column(db.Integer, primary_key=True)
    Username = db.Column(db.String(30), unique=True, nullable=False)
    Password = db.Column(db.String(255), nullable=False)
    Name = db.Column(db.String(30), unique=False, nullable=False)
    isRegistered = db.Column(db.Boolean, nullable=False)
    paid_txns = db.relationship('tbl_tlist', foreign_keys='tbl_tlist.paidByUserID', backref='txn_paidUser', lazy=True)
    created_txns = db.relationship('tbl_tlist', foreign_keys='tbl_tlist.createdByUserID', backref='txn_createdUser', lazy=True)
    user_events = db.relationship('tbl_events', secondary='tbl_eventusers', back_populates='event_users', lazy=True)
    user_txnShares = db.relationship('tbl_tlist', secondary='tbl_txnshare', back_populates='shared_users', lazy=True)

    def __init__(self, Username, Name, isRegistered, Password):
       self.Username = Username
       self.Password = Password
       self.Name = Name
       self.isRegistered = isRegistered


class tbl_eventusers(db.Model):
    __tablename___ = 'tbl_eventusers'
    EventID = db.Column(db.Integer, db.ForeignKey('tbl_events.EventID'), primary_key=True, nullable=False) #event
    UserID = db.Column(db.Integer, db.ForeignKey('tbl_users.id'), primary_key=True, nullable=False) #user
    # JoinTime = db.Column(db.DateTime(timezone=True), nullable=False)
    JoinTime: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.now(datetime.UTC))
    Liability = db.Column(db.Float, nullable=False)

    def __init__(self, EventID, UserID, Liability=0.0):
        self.EventID = EventID
        self.UserID = UserID
        self.Liability = Liability


class tbl_txnshare(db.Model):
    __tablename___ = 'tbl_txnshare'
    TxnID = db.Column(db.Integer, db.ForeignKey('tbl_tlist.TxnID'), primary_key=True, nullable=False)
    UserID = db.Column(db.Integer, db.ForeignKey('tbl_users.id'), primary_key=True, nullable=False)
    EventID = db.Column(db.Integer, db.ForeignKey('tbl_events.EventID'), nullable=True)
    AvgAmount = db.Column(db.Float, nullable=False)

    def __init__(self, TxnID, UserID, AvgAmount, EventID=None):
        self.TxnID = TxnID
        self.UserID = UserID
        self.AvgAmount = AvgAmount
        self.EventID = EventID
    
