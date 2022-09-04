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
    paidByID = db.Column(db.Integer, nullable=False)
    Amount = db.Column(db.Integer, nullable=False)
    ShareStats = db.Column(db.String(100), nullable=False)
    TxnDescription = db.Column(db.String(100), nullable=True)
    TxnTime = db.Column(db.DateTime, nullable=False)
    CreatedByUserID = db.Column(db.Integer, nullable=False)

    def __init__(self, EventID, paidByID, Amount, ShareStats="all", 
                    TxnDescription=None, TxnTime=datetime.now(), ):
        self.EventID = EventID
        self.paidByID = paidByID
        self.Amount = Amount
        if ShareStats == "all":
            self.ShareStats = '1'*self.NumberOfMembers
        else:
            self.ShareStats = ShareStats
        self.TxnDescription = TxnDescription
        self.TxnTime = TxnTime
        self.CreatedByUserID = -1 #later


class tbl_users(UserMixin, db.Model):
    __tablename___ = 'tbl_users'
    id = db.Column(db.Integer, primary_key=True)
    Username = db.Column(db.String(30), unique=True, nullable=False)
    Password = db.Column(db.String(255), nullable=False)
    user_event = db.relationship('tbl_eventusers', backref='user_event', lazy=True)

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