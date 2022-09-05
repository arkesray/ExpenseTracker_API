from multiprocessing import Event
from datetime import datetime
from . import main
from .. import db
from ..models import tbl_events, tbl_tlist, tbl_txnshare, tbl_users, tbl_eventusers
from flask import request, redirect, url_for, jsonify, make_response

from .expense import expenseCalculator
import json

@main.route('/')
@main.route('/home')
def home():
    response = make_response(
                jsonify(
                    {"message": "This is Home Page"}
                ),
                200,
            )
    response.headers["Content-Type"] = "application/json"
    return response

@main.route('/fetch_txns/<EventName>', methods=["GET"])
def fetch_txns(EventName):
    event = tbl_events.query.filter_by(EventName=EventName).first() 
    event_txns = tbl_tlist.query.filter_by(EventID=event.EventID).all()

    temp_txns = []
    for txn in event_txns:
        temp_txns.append({
            "TxnID" : txn.TxnID, 
            "EventID" : txn.EventID,
            "paidByUserID" : txn.paidByUserID,
            "Amount": txn.Amount,

            "TxnDescription" : txn.TxnDescription,
            "TxnTime" : txn.TxnTime,
        })

    return make_response(
            jsonify(txns = temp_txns),
            200,
        )

@main.route('/fetch_participants', methods=["GET"])
def fetch_participants():
    all_participants = tbl_users.query.all()

    temp_persons = []
    for person in all_participants:
        temp_persons.append({"id" : person.id, "username" : person.Username})

    return make_response(
            jsonify(Participants = temp_persons),
            200,
        )

@main.route('/fetch_events', methods=["GET"])
def fetch_events():
    all_events = tbl_events.query.all()

    temp_events = []
    for event in all_events:
        temp_events.append({"EventID" : event.EventID, "EventName" : event.EventName})
    
    return make_response(
            jsonify(Events = temp_events),
            200,
        ) 

@main.route('/fetch_event_participants/<EventName>', methods=["GET"])
def fetch_event_participants(EventName):
    event = tbl_events.query.filter_by(EventName=EventName).first() 
    event_participants = tbl_eventusers.query.filter_by(EventID=event.EventID).all()

    temp_eventUser = tbl_users.query.filter(
        tbl_users.id.in_([v.UserID for v in event_participants])).all()
    
    temp_persons = []
    for person in temp_eventUser:
        temp_persons.append({"id" : person.id, "username" : person.Username})

    return make_response(
            jsonify(EventID = event.EventID, EventParticipants = temp_persons),
            200,
        )

@main.route('/add_event', methods=["PUT"])
def add_event():

    #{ "eventName" : "Aquatica", "eventDescription" : "Aquatica des"}
    # eventID, 500
    event_data = request.get_json()
    event = tbl_events(
        EventName=event_data["eventName"],
        EventDescription=event_data["eventDescription"]
    )
    try:
        db.session.add(event)
        db.session.commit()
        return make_response(
            jsonify(eventID = event.EventID),
            200,
        )
    except:
        db.session.rollback()
        return make_response(
            jsonify(message = "Error Adding New Event"),
            500,
        )
    
@main.route('/add_participant2event', methods=["PUT"])
def add_participant2event():

    #{ "participantName" : "arkes", "eventName" : "Aquatica des"}
    # 200, 500
    participant2event_data = request.get_json()
    event = tbl_events.query.filter_by(EventName=participant2event_data["eventName"]).first()
    
    try:
        for user in participant2event_data["participantList"]:
            participant = tbl_users.query.filter_by(Username=user).first()
            newEventUser = tbl_eventusers(EventID=event.EventID, UserID=participant.id)
            db.session.add(newEventUser)
        
        event.NumberOfMembers += len(participant2event_data["participantList"])
        db.session.commit()
        return make_response(
            jsonify(message = "Success"), 200,
        )
    except:
        db.session.rollback()
        return make_response(
            jsonify(message = "Adding Participant to Event Failed"), 500,
        )

    
@main.route('/add_txns', methods=["PUT"])
def add_txns():
    #200 ok , txn ID, iqbal er output
    #500 internal server error

    # {"eventName":"aquatica", "transaction":[1,10, "0011"], "timeStamp":"2022-09-03T20:33:23.559Z"}

    # {"eventName":"aquatica", "paidByUserName":"Arkes", "Amount : 100", sharedByUserNames : ["Arkes", "Puspak"],
    # "timeStamp":"2022-09-03T20:33:23.559Z"}
    flag_addTxnSuccess = False

    txn_data = request.get_json()
    event_data = tbl_events.query.filter_by(EventName=txn_data["eventName"]).first()
    paidByUser_data = tbl_users.query.filter_by(Username=txn_data["paidByUserName"]).first()
    sharedUser_data = []

    for user in txn_data["sharedByUserNames"]:
        sharedUser_data.append(tbl_users.query.filter_by(Username=user).first())

    try:
        EventTime = datetime.strptime(txn_data["timeStamp"], "%Y-%m-%dT%H:%M:%S.%fZ")
    except:
        EventTime = None

    txn = tbl_tlist(
            EventID = event_data.EventID,
            paidByUserID = paidByUser_data.id,
            Amount = txn_data["Amount"], 
            EventTime = EventTime
            )
    
    try:
        db.session.add(txn)
        db.session.commit()
        flag_addTxnSuccess = True
        try:
            for user in sharedUser_data:
                txn_Shares = tbl_txnshare(txn.TxnID, user.id, event_data.EventID)
                db.session.add(txn_Shares)
            
            db.session.commit()

            return json.dumps({
                            'message':'Success', 
                            'TxnID' : txn.TxnID,
                            },
                        200,
                        {'ContentType':'application/json'} )
        except:
            db.session.rollback()
            db.session.delete(txn)
            db.session.commit()
            return jsonify(message = "Failed Adding Shares of txn. Removed Transaction"), 500
        
    except:
        db.session.rollback()
        return jsonify(message = "Failed Adding txn"), 500


@main.route('/delete_txns', methods=["DELETE"])
def delete_txns():
    # txnid
    # 200, 500, for that event, list of all txn, iqbal er output
    txn_id = int(request.get_json()["TxnID"])
    txn = tbl_tlist.query.get(txn_id)
    txn_shares = tbl_txnshare.query.filter_by(TxnID=txn_id).all()

    try:
        db.session.delete(txn)
        for txn_share in txn_shares:
            db.session.delete(txn_share)
        db.session.commit()
        return jsonify({'message' : "Success"}), 200
        #get all event-txns and return
    except:
        return jsonify({'message' : "Failed to delete"}), 500

@main.route('/calculate', methods=["GET"])
def calculate():
    pass