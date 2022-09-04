from multiprocessing import Event
from datetime import datetime
from . import main
from .. import db
from ..models import tbl_events, tbl_tlist, tbl_users, tbl_eventusers
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

@main.route('/fetch_txns', methods=["GET"])
def fetch_txns():
    all_txns = tbl_tlist.query.all()
    return make_response(
            jsonify(txns = all_txns),
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

# @main.route('/fetch_event_participants', methods=["GET"])
# def fetch_event_participants()

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
    txn_data = request.get_json()
    event_data = tbl_events.query.filter_by(EventName = txn_data["eventName"]).first() 
    txn = tbl_tlist(
            EventID = event_data.EventID,
            paidByID = txn_data["transaction"][0],
            Amount = txn_data["transaction"][1], 
            ShareStats = txn_data["transaction"][2], 
            EventTime = datetime.strptime(txn_data["timeStamp"], "%Y-%m-%dT%H:%M:%S.%fZ")
            )
    
    try:
        db.session.add(txn)
        db.session.commit()
        return json.dumps({'message':'Success', 'TxnID' : txn.TxnID, 'iqbal' : 'output'},
         200, {'ContentType':'application/json'} )
    except:
        db.session.rollback()
        return jsonify(message = "Failed Adding txn"), 500


@main.route('/delete_txns', methods=["DELETE"])
def delete_txns():
    # txnid
    # 200, 500, for that event, list of all txn, iqbal er output
    txn_id = int(request.get_json()["TxnID"])
    txn = tbl_tlist.query.get(txn_id)
    event_id = txn.EventID
    try:
        db.session.delete(txn)
        db.session.commit()
        return jsonify({'message' : "Success", 'iqbal' : 'output'}), 200
        #get all event-txns and return
    except:
        return jsonify({'message' : "Failed to delete"}), 500

