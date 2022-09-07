from datetime import datetime
from multiprocessing import Event
from flask_login import UserMixin
from . import db

class tbl_events(db.Model):
    __tablename___ = 'tbl_events'
    EventID = db.Column(db.Integer, primary_key=True)
    EventName = db.Column(db.String(100), unique=True, nullable=False)
    EventDescription = db.Column(db.String(100), nullable=True)
    NumberOfMembers = db.Column(db.Integer, nullable=False)
    EventTime = db.Column(db.DateTime, nullable=False)
    t_list = db.relationship('tbl_tlist', backref='events', lazy=True)
    event_user = db.relationship('tbl_eventusers', backref='event_user', lazy=True)
    event_txnShare = db.relationship('tbl_txnshare', backref='event_txnShare', lazy=True)

    def __init__(self, EventName, EventDescription=None, NumberOfMembers=0,
                     EventTime=datetime.now(), ):
        self.EventName = EventName
        self.EventDescription = EventDescription
        self.NumberOfMembers = NumberOfMembers
        self.EventTime = EventTime


class tbl_tlist(db.Model):
    __tablename___ = 'tbl_tlist'
    TxnID = db.Column(db.Integer, primary_key=True)
    EventID = db.Column(db.Integer, db.ForeignKey('tbl_events.EventID'), nullable=False)
    paidByUserID = db.Column(db.Integer, db.ForeignKey('tbl_users.id'), nullable=False)
    Amount = db.Column(db.Float, nullable=False)
    TxnDescription = db.Column(db.String(100), nullable=True)
    TxnTime = db.Column(db.DateTime, nullable=False)
    CreatedByUserID = db.Column(db.Integer, nullable=True)
    txn_Share = db.relationship('tbl_txnshare', backref='txn_Share', lazy=True)

    def __init__(self, EventID, paidByUserID, Amount=0,
                    TxnDescription=None, TxnTime=datetime.now(), ):
        self.EventID = EventID
        self.paidByUserID = paidByUserID
        self.Amount = Amount
        self.TxnDescription = TxnDescription
        self.TxnTime = TxnTime
        self.CreatedByUserID = -1 #later


class tbl_users(UserMixin, db.Model):
    __tablename___ = 'tbl_users'
    id = db.Column(db.Integer, primary_key=True)
    Username = db.Column(db.String(30), unique=True, nullable=False)
    Password = db.Column(db.String(255), nullable=False)
    user_event = db.relationship('tbl_eventusers', backref='user_event', lazy=True)
    user_txn = db.relationship('tbl_tlist', backref='user_txn', lazy=True)
    user_txnShare = db.relationship('tbl_txnshare', backref='user_txnShare', lazy=True)

    def __init__(self, Username, Password="Password"):
       self.Username = Username
       self.Password = Password


class tbl_eventusers(db.Model):
    __tablename___ = 'tbl_eventusers'
    EventID = db.Column(db.Integer, db.ForeignKey('tbl_events.EventID'), primary_key=True, nullable=False)
    UserID = db.Column(db.Integer, db.ForeignKey('tbl_users.id'), primary_key=True, nullable=False)
    JoinTime = db.Column(db.DateTime, nullable=False)

    def __init__(self, EventID, UserID, JoinTime=datetime.now()):
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
    