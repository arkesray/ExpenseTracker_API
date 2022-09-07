from multiprocessing import Event
from datetime import datetime
from urllib import response
from . import main
from .. import db
from ..models import tbl_events, tbl_tlist, tbl_txnshare, tbl_users, tbl_eventusers
from flask import request, jsonify, make_response

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
    # event_participants = tbl_eventusers.query.filter_by(EventID=event.EventID).all()

    # temp_eventUsers = tbl_users.query.filter(
    #     tbl_users.id.in_([eventUser.UserID for eventUser in event_participants])).all()
    
    temp_persons = []
    for user in event.event_users:
        temp_persons.append({"id" : user.id, "username" : user.Username})

    return make_response(
            jsonify(EventID = event.EventID, EventParticipants = temp_persons),
            200,
        )


@main.route('/fetch_txns/<EventName>', methods=["GET"])
def fetch_txns(EventName):
    event = tbl_events.query.filter_by(EventName=EventName).first() 
    #event_txns = tbl_tlist.query.filter_by(EventID=event.EventID).all()

    temp_txns = []
    for txn in event.txns:
        # paidByUser = tbl_users.query.filter_by(id=txn.paidByUserID).first()
        # sharedByUsers = []
        # txns_shares = tbl_txnshare.query.filter_by(EventID=event.EventID, TxnID=txn.TxnID).all()
        # for txn_sharedUser in txns_shares:
        #     sharedUser = tbl_users.query.filter_by(id=txn_sharedUser.UserID).first()
        #     sharedByUsers.append(sharedUser.Username)
        # sharedByUsers = []
        # for txn_sharedUser in txn.shared_users:
        #     sharedByUsers.append(txn_sharedUser.Username)

        temp_txns.append({
            "TxnID" : txn.TxnID, 
            "EventID" : txn.EventID,
            "paidByUserName" : txn.txn_paidUser.Username,
            "Amount": txn.Amount,
            "sharedByUserNames" : [txn_sharedUser.Username for txn_sharedUser in txn.shared_users],
            "TxnDescription" : txn.TxnDescription,
            "TxnTime" : txn.TxnTime,
        })

    return make_response(
            jsonify(txns = temp_txns),
            200,
        )


@main.route('/add_event', methods=["PUT"])
def add_event():

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

    # {"eventName":"string", "participantList":["puspak","iqbal","arkes"]}
    # 200, 500
    participant2event_data = request.get_json()
    event = tbl_events.query.filter_by(EventName=participant2event_data["eventName"]).first()
    
    participants = tbl_users.query.filter(
        tbl_users.Username.in_(participant2event_data["participantList"])).all()
    
    try:
        for participant in participants:
            newEventUser = tbl_eventusers(EventID=event.EventID, UserID=participant.id, 
                                            JoinTime=datetime.now())
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
    flag_addTxnSuccess = False

    txn_data = request.get_json()
    event_data = tbl_events.query.filter_by(EventName=txn_data["eventName"]).first()
    paidByUser_data = tbl_users.query.filter_by(Username=txn_data["paidByUserName"]).first()
    sharedUser_data = tbl_users.query.filter(
        tbl_users.Username.in_(txn_data["sharedByUserNames"])).all()

    # for user in txn_data["sharedByUserNames"]:
    #     sharedUser_data.append(tbl_users.query.filter_by(Username=user).first())

    try:
        EventTime = datetime.strptime(txn_data["timeStamp"], "%Y-%m-%dT%H:%M:%S.%fZ")
    except:
        EventTime = datetime.now()

    txn = tbl_tlist(
            EventID = event_data.EventID,
            paidByUserID = paidByUser_data.id,
            Amount = float(txn_data["Amount"]), 
            TxnTime = EventTime
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
            return jsonify(message = "Success", TxnID = txn.TxnID, ), 200
            
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
    txn_id = int(request.get_json()["TxnID"])
    txn = tbl_tlist.query.get(txn_id)
    txn_shares = tbl_txnshare.query.filter_by(TxnID=txn_id).all()

    try:
        db.session.delete(txn)
        # for txn_share in txn_shares:
        #     db.session.delete(txn_share)
        db.session.commit()
        return jsonify({'message' : "Success"}), 200
        #get all event-txns and return
    except:
        return jsonify({'message' : "Failed to delete"}), 500


@main.route('/calculate/<EventName>', methods=["GET"])
def calculate(EventName):

    event_data = tbl_events.query.filter_by(EventName=EventName).first()
    # event_participants = tbl_eventusers.query.filter_by(EventID=event_data.EventID).all()
    # event_txns = tbl_tlist.query.filter_by(EventID=event_data.EventID).all()

    numberOfParticipants = len(event_data.event_users)
    person_mapping, person_mapping_rev = {}, {}
    for i in range(numberOfParticipants):
        event_participant = event_data.event_users[i]
        person_mapping[event_participant.id] = i
        person_mapping_rev[i] = event_participant.id

    txns = []
    for txn in event_data.txns:
        bin_str = [0]*numberOfParticipants
        # shared_users = tbl_txnshare.query.filter_by(TxnID=txn.TxnID).all()
        for user in txn.shared_users:
            bin_str[person_mapping[user.id]] = 1
        txns.append([person_mapping[txn.paidByUserID],
                     txn.Amount, 
                     "".join([str(v) for v in bin_str])
                ])
    
    pendingTxns = expenseCalculator(numberOfParticipants, txns)

    temp_pendingTxns = []
    for pendingTxn in pendingTxns:
        sender = tbl_users.query.filter_by(id=person_mapping_rev[pendingTxn[0]]).first()
        receiver = tbl_users.query.filter_by(id=person_mapping_rev[pendingTxn[1]]).first()
        temp_pendingTxns.append([sender.Username, receiver.Username, pendingTxn[2]])

    response = {
        "eventID" : event_data.EventID,
        "transactionDetails" : temp_pendingTxns
    }

    return jsonify(response), 200