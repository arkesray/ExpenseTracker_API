from datetime import datetime
from . import main
from .. import db
from ..models import tbl_events, tbl_tlist, tbl_txnshare, tbl_users, tbl_eventusers
from flask import request, jsonify, make_response
from .exp import calcLiability
from .expense import expenseCalculator

from ..helpers import expenseCalculator, token_required, isUserInEvent
import json


@main.route('/fetch_participants', methods=["GET"])
def fetch_participants():
    all_participants = tbl_users.query.all()

    temp_persons = []
    for person in all_participants:
        temp_persons.append({"id" : person.id, "username" : person.Username})

    return make_response(jsonify(Participants = temp_persons), 200)


@main.route('/fetch_events', methods=["GET"])
@token_required
def fetch_events(current_user):
    all_User_events = current_user.user_events

    temp_events = []
    for event in all_User_events:
        temp_events.append({"EventID" : event.EventID, "EventName" : event.EventName})
    
    return make_response(jsonify(Events = temp_events), 200) 


@main.route('/fetch_event_participants/<EventName>', methods=["GET"])
@token_required
def fetch_event_participants(current_user, EventName):
    event_data = isUserInEvent(current_user, EventName)
    if event_data == None:
        return jsonify(message = "Event doesn't exist or You are not Authorised "), 403

    temp_persons = []
    for user in event_data.event_users:
        temp_persons.append({"id" : user.id, "username" : user.Username})

    return make_response(
            jsonify(EventID = event_data.EventID, EventParticipants = temp_persons),
            200,
        )


@main.route('/fetch_txns/<EventName>', methods=["GET"])
@token_required
def fetch_txns(current_user, EventName):
    event_data = isUserInEvent(current_user, EventName)
    if event_data == None:
        return jsonify(message = "Event doesn't exist or You are not Authorised "), 403

    temp_txns = []
    for txn in event_data.txns:
        temp_txns.append({
            "TxnID" : txn.TxnID, 
            "EventID" : txn.EventID,
            "paidByUserName" : txn.txn_paidUser.Username,
            "Amount": txn.Amount,
            "sharedByUserNames" : [txn_sharedUser.Username for txn_sharedUser in txn.shared_users],
            "TxnDescription" : txn.TxnDescription,
            "TxnTime" : txn.TxnTime,
        })

    return make_response(jsonify(txns = temp_txns), 200)


@main.route('/add_event', methods=["PUT"])
@token_required
def add_event(current_user):
    event_data = request.get_json()
    event = tbl_events(
        EventName=event_data["eventName"],
        EventDescription=event_data["eventDescription"]
    )
    try:
        flag_deleteEventFailed = False
        db.session.add(event)
        db.session.commit()
        try:
            newEventUser = tbl_eventusers(
                    EventID=event.EventID,
                    UserID=current_user.id
                )
            event.NumberOfMembers += 1
            db.session.add(newEventUser)
            db.session.commit()
            return jsonify(eventID = event.EventID), 200
        except:
            flag_deleteEventFailed = True
            db.session.rollback()
            db.session.delete(event)
            db.session.commit()
            return jsonify(message = "Error Adding CreatedByUser to Event. Event Deleted!!!"), 500
    except:
        db.session.rollback()
        if not flag_deleteEventFailed:
            return jsonify(message = "Error Adding New Event"), 500
        else:
            return jsonify(message = "EVENT CREATED without CREATOR in event"), 500


@main.route('/add_participant2event', methods=["PUT"])
@token_required
def add_participant2event(current_user):
    participant2event_data = request.get_json()
    event_data = isUserInEvent(current_user, participant2event_data["eventName"])
    if event_data == None:
        return jsonify(message = "Event doesn't exist or You are not Authorised "), 403
    
    participants = tbl_users.query.filter(
        tbl_users.Username.in_(participant2event_data["participantList"])).all()
    
    try:
        for participant in participants:
            newEventUser = tbl_eventusers(EventID=event_data.EventID, UserID=participant.id)
            db.session.add(newEventUser)

        event_data.NumberOfMembers += len(participant2event_data["participantList"])
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
@token_required
def add_txns(current_user):
    txn_data = request.get_json()

    event_data = isUserInEvent(current_user, txn_data["eventName"])
    if event_data == None:
        return jsonify(message = "Event doesn't exist or You are not Authorised "), 403

    if len(txn_data["sharedByUserNames"]) == 0:
        return jsonify(message = "Can't add txn without SharedUsers"), 500

    paidByUser_data = tbl_users.query.filter_by(Username=txn_data["paidByUserName"]).first()
    sharedUser_data = tbl_users.query.filter(
        tbl_users.Username.in_(txn_data["sharedByUserNames"])).all()

    try:
        TxnTime = datetime.strptime(txn_data["timeStamp"], "%Y-%m-%dT%H:%M:%S.%fZ")
        TxnDescription = txn_data["description"]
    except:
        TxnTime = datetime.utcnow()
        TxnDescription = None

    txn = tbl_tlist(
            EventID = event_data.EventID,
            paidByUserID = paidByUser_data.id,
            createdByUserID = current_user.id,
            Amount = float(txn_data["Amount"]),
            TxnDescription = TxnDescription,
            TxnTime = TxnTime
            )

    try:
        flag_deleteTxnFailed = False
        db.session.add(txn)
        db.session.commit()
        try:
            for user in sharedUser_data:
                txn_Shares = tbl_txnshare(txn.TxnID, user.id, event_data.EventID)
                db.session.add(txn_Shares)

            db.session.commit()
            return jsonify(message = "Success", TxnID = txn.TxnID, ), 200
        except:
            flag_deleteTxnFailed = True
            db.session.rollback()
            db.session.delete(txn)
            db.session.commit()
            flag_deleteTxnFailed = False
            return jsonify(message = "Failed Adding Shares of txn. Removed Transaction"), 500
        
    except:
        db.session.rollback()
        if not flag_deleteTxnFailed:
            return jsonify(message = "Failed Adding txn"), 500
        else:
            return jsonify(message = "TXNs ADDED without SHARED USERS"), 500


@main.route('/delete_txns', methods=["DELETE"])
@token_required
def delete_txns(current_user):
    txn_id = int(request.get_json()["TxnID"])
    txn = tbl_tlist.query.get(txn_id)

    if current_user not in txn.txn_event.event_users:
        return jsonify(message = "You are not Authorised to delete Txn"), 403

    try:
        db.session.delete(txn)
        # for txn_share in txn_shares:
        #     db.session.delete(txn_share)
        db.session.commit()
        return jsonify({'message' : "Success"}), 200
    except:
        return jsonify({'message' : "Failed to delete"}), 500


@main.route('/calculate/<EventName>', methods=["GET"])
@token_required
def calculate(current_user, EventName):

    event_data = isUserInEvent(current_user, EventName)
    if event_data == None:
        return jsonify(message = "Event doesn't exist or You are not Authorised "), 403

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
    
    liability = calcLiability(numberOfParticipants, txns)
    pendingTxns = expenseCalculator(liability)

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