from datetime import datetime
from flask_login import UserMixin
from . import db

class tbl_events(db.Model):
    __tablename___ = 'tbl_events'
    EventID = db.Column(db.Integer, primary_key=True)
    EventName = db.Column(db.String(100), unique=True, nullable=False)
    EventDescription = db.Column(db.String(100), nullable=True)
    NumberOfMembers = db.Column(db.Integer, nullable=False)
    EventTime = db.Column(db.DateTime(timezone=True), nullable=False)
    txns = db.relationship('tbl_tlist', backref='txn_event', lazy=True)
    event_users = db.relationship('tbl_users', secondary='tbl_eventusers', back_populates='user_events', lazy=True)
    event_txnShare = db.relationship('tbl_txnshare', backref='txnShare_event', lazy=True)

    def __init__(self, EventName, EventDescription=None, NumberOfMembers=0,
                     EventTime=datetime.utcnow(), ):
        self.EventName = EventName
        self.EventDescription = EventDescription
        self.NumberOfMembers = NumberOfMembers
        self.EventTime = EventTime


class tbl_tlist(db.Model):
    __tablename___ = 'tbl_tlist'
    TxnID = db.Column(db.Integer, primary_key=True)
    EventID = db.Column(db.Integer, db.ForeignKey('tbl_events.EventID'), nullable=False) #txn_event
    paidByUserID = db.Column(db.Integer, db.ForeignKey('tbl_users.id'), nullable=False) #txn_paidUser
    createdByUserID = db.Column(db.Integer, db.ForeignKey('tbl_users.id'), nullable=False) #txn_createdUser
    Amount = db.Column(db.Float, nullable=False)
    TxnDescription = db.Column(db.String(100), nullable=True)
    TxnTime = db.Column(db.DateTime(timezone=True), nullable=False)
    shared_users = db.relationship('tbl_users', secondary='tbl_txnshare', back_populates='user_txnShares', lazy=True)

    def __init__(self, EventID, paidByUserID, createdByUserID, Amount=0,
                    TxnDescription=None, TxnTime=datetime.utcnow(), ):
        self.EventID = EventID
        self.paidByUserID = paidByUserID
        self.Amount = Amount
        self.TxnDescription = TxnDescription
        self.TxnTime = TxnTime
        self.createdByUserID = createdByUserID


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

    def __init__(self, Username, Name, isRegistered, Password="Password"):
       self.Username = Username
       self.Password = Password
       self.Name = Name
       self.isRegistered = isRegistered


class tbl_eventusers(db.Model):
    __tablename___ = 'tbl_eventusers'
    EventID = db.Column(db.Integer, db.ForeignKey('tbl_events.EventID'), primary_key=True, nullable=False) #event
    UserID = db.Column(db.Integer, db.ForeignKey('tbl_users.id'), primary_key=True, nullable=False) #user
    JoinTime = db.Column(db.DateTime(timezone=True), nullable=False)

    def __init__(self, EventID, UserID, JoinTime=datetime.utcnow()):
        self.EventID = EventID
        self.UserID = UserID
        self.JoinTime = JoinTime

class tbl_txnshare(db.Model):
    __tablename___ = 'tbl_txnshare'
    TxnID = db.Column(db.Integer, db.ForeignKey('tbl_tlist.TxnID'), primary_key=True, nullable=False)
    UserID = db.Column(db.Integer, db.ForeignKey('tbl_users.id'), primary_key=True, nullable=False)
    EventID = db.Column(db.Integer, db.ForeignKey('tbl_events.EventID'), nullable=True)

    def __init__(self, TxnID, UserID, EventID=None):
        self.TxnID = TxnID
        self.UserID = UserID
        self.EventID = EventID
    