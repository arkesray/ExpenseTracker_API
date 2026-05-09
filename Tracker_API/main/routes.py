from . import main
from .. import db
from ..models import Event, Transaction, TransactionShare, User, EventMembership
from flask import request, jsonify, make_response

# from .exp import 
from .expense import expenseCalculator, calcLiability
from ..helpers import token_required, isUserInEvent, user_in_event, get_participant_Expense, to_iso_z

@main.route('/members', methods=["GET"])
def get_members():
    search = request.args.get('search', '')
    all_members = User.query.filter(User.username.ilike("%{}%".format(search))).all()

    temp_members = []
    for person in all_members:
        temp_members.append({"id": person.id, "username": person.username, "joinedOn": ""})

    return make_response(jsonify(members=temp_members), 200)


@main.route('/events', methods=["GET"])
@token_required
def list_events(current_user):
    all_User_events = current_user.events

    temp_events = []
    for event in all_User_events:
        temp_events.append({"EventID": event.id,
                    "EventName": event.name,
                    "EventTime": to_iso_z(event.created_at),
                    "EventDescription": event.description,
                    "TotalExpense": float(event.total_amount),
                    "EventOwner": event.created_by_user.username if event.created_by_user else None,
                    })
    
    return make_response(jsonify(Events = temp_events), 200) 


@main.route('/events/<EventName>/members', methods=["GET"])
@token_required
@user_in_event
def get_event_members(current_user, event_data):
    temp_members = []
    for user in event_data.members:
        eventuser_data = EventMembership.query.filter(
                                    EventMembership.event_id == event_data.id,
                                    EventMembership.user_id == user.id).one()
        temp_members.append({"id": user.id, "username": user.username,
                      "joinedOn": to_iso_z(eventuser_data.joined_at)})

    return make_response(jsonify(EventID = event_data.id, EventMembers = temp_members), 200)


@main.route('/events/<EventName>/transactions', methods=["GET"])
@token_required
@user_in_event
def get_event_transactions(current_user, event_data):
    temp_txns = []
    for txn in event_data.transactions:
        temp_txns.append({
            "TxnID": txn.id,
            "EventID": txn.event_id,
            "paidByUserName": txn.paid_by_user.username if txn.paid_by_user else None,
            "Amount": float(txn.amount),
            "sharedByUserNames": [u.username for u in txn.shared_by_users],
            "TxnDescription": txn.description,
            "TxnTime": to_iso_z(txn.created_at),
            "TxnAddedBy": txn.created_by_user.username if txn.created_by_user else None,
        })

    return make_response(jsonify(txns=temp_txns), 200)


@main.route('/events', methods=["POST"])
@token_required
def create_event(current_user):
    event_data = request.get_json()
    event = Event(
        name=event_data["eventName"],
        created_by_id=current_user.id,
        description=event_data["eventDescription"],
    )
    try:
        flag_deleteEventFailed = False
        db.session.add(event)
        db.session.commit()
        try:
            newEventUser = EventMembership(
                    event_id=event.id,
                    user_id=current_user.id,
                )
            event.member_count += 1
            db.session.add(newEventUser)
            db.session.commit()
            return jsonify(eventID=event.id), 201
        except Exception as e:
            print("failed", e)
            flag_deleteEventFailed = True
            db.session.rollback()
            db.session.delete(event)
            db.session.commit()
            return jsonify(message = "Error Adding CreatedByUser to Event. Event Deleted!!!"), 500
    except Exception as e:
        print("failed", e)
        db.session.rollback()
        if not flag_deleteEventFailed:
            return jsonify(message = "Error Adding New Event"), 500
        else:
            return jsonify(message = "EVENT CREATED without CREATOR in event"), 500


@main.route('/events/<EventName>/members', methods=["POST"])
@token_required
@user_in_event
def add_members(current_user, event_data):
    members_payload = request.get_json()
    print(members_payload)
    members_to_add = User.query.filter(
        User.username.in_(members_payload["memberList"]) ).all()
    
    try:
        for member in members_to_add:
            newEventUser = EventMembership(event_id=event_data.id, user_id=member.id,)
            db.session.add(newEventUser)

        event_data.member_count += len(members_to_add)
        db.session.commit()
        return make_response(
            jsonify(message = "Success"), 200,
        )
    except:
        db.session.rollback()
        return make_response(
            jsonify(message = "Adding members to Event Failed"), 500,
        )

    
@main.route('/events/<EventName>/transactions', methods=["POST"])
@token_required
@user_in_event
def create_transaction(current_user, event_data):
    txn_data = request.get_json()
    print(txn_data)
    # event_data is provided by the decorator
    paidByUser_data = User.query.filter_by(username=txn_data["paidByUserName"]).first()

    if paidByUser_data:
        if not isUserInEvent(paidByUser_data, event_data.name):
            return jsonify(message = "Paid By User not in event"), 500 
    else:
        return jsonify(message = "Paid By User doesn't exists"), 500

    sharedUser_data = User.query.filter(
        User.username.in_(txn_data["sharedByUserNames"])).all()

    if len(txn_data["sharedByUserNames"]) == 0 or len(txn_data["sharedByUserNames"]) != len(sharedUser_data):
        return jsonify(message = "Can't add txn without SharedUsers or Missing Shared User"), 500

    for sharedUser in sharedUser_data:
        if sharedUser not in event_data.members:
            return jsonify(message = "SharedUsers not found in Event"), 500


        txn = Transaction(
            event_id = event_data.id,
            paid_by_id = paidByUser_data.id,
            created_by_id = current_user.id,
            amount = float(txn_data["Amount"]),
            description = txn_data["description"],
            is_expense=bool(txn_data.get("isExpense", True)),
            )

    try:
        flag_deleteTxnFailed = False
        db.session.add(txn)
        db.session.commit()
        try:
            for user in sharedUser_data:
                txn_Shares = TransactionShare(transaction_id=txn.id, user_id=user.id, share_amount=float(txn_data["Amount"])/len(sharedUser_data))
                db.session.add(txn_Shares)
            
            db.session.commit()
            return jsonify(message = "Success", TxnID=txn.id), 201
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


@main.route('/transactions/<int:txn_id>', methods=["DELETE"])
@token_required
def delete_transaction(current_user, txn_id):
    txn = Transaction.query.get(txn_id)
    if not txn:
        return jsonify(message="Txn not found"), 404

    if current_user not in txn.event.members:
        return jsonify(message="You are not Authorised to delete Txn"), 403

    try:
        db.session.delete(txn)
        db.session.commit()
        return jsonify({'message': "Success"}), 200
    except:
        return jsonify({'message': "Failed to delete"}), 500


# @main.route('/events/<EventName>/liability/<UserName>', methods=["GET"])
# @token_required
# @user_in_event
# def get_liability(current_user, event_data, UserName):

#     user = User.query.filter_by(username=UserName).first()
#     userRecord = EventMembership.query.filter_by(
#             user_id=user.id, 
#             event_id=event_data.id).first()

#     response = {"eventID": userRecord.event_id,
#                 "eventName": event_data.name,
#                 "userID": userRecord.user_id,
#                 "userName": UserName,
#                 "userLiability": float(userRecord.liability)
#     }

#     return jsonify(response), 200


# @main.route('/events/<EventName>/calculate', methods=["GET"])
# @token_required
# @user_in_event
# def calculate(current_user, event_data):

#     numberOfParticipants = len(event_data.members)
#     person_mapping, person_mapping_rev = {}, {}
#     for i in range(numberOfParticipants):
#         event_participant = event_data.members[i]
#         person_mapping[event_participant.id] = i
#         person_mapping_rev[i] = event_participant.id

#     txns = []
#     for txn in event_data.transactions:
#         bin_str = [0]*numberOfParticipants
#         for user in txn.shared_users:
#             bin_str[person_mapping[user.id]] = 1
#         txns.append([person_mapping[txn.paid_by],
#                  float(txn.amount), 
#                      "".join([str(v) for v in bin_str])
#                 ])
    
#     liabilities = calcLiability(numberOfParticipants, txns)
#     pendingTxns = expenseCalculator(liabilities[:])
#     for user_liability in liabilities:
#         userRecord = EventMembership.query.filter_by(
#             user_id=person_mapping_rev[user_liability[1]], 
#             event_id=event_data.id).first()
#         if userRecord:
#             userRecord.liability = user_liability[0]
#             try:
#                 db.session.commit()
#             except:
#                 db.session.rollback()
    

#     temp_liability = []
#     for user_liability in liabilities:
#         user = User.query.filter_by(id=person_mapping_rev[user_liability[1]]).first()
#         temp_liability.append([user.username , user_liability[0]])


#     temp_pendingTxns = []
#     for pendingTxn in pendingTxns:
#         sender = User.query.filter_by(id=person_mapping_rev[pendingTxn[0]]).first()
#         receiver = User.query.filter_by(id=person_mapping_rev[pendingTxn[1]]).first()
#         temp_pendingTxns.append([sender.username, receiver.username, pendingTxn[2]])

#     response = {
#         "eventID" : event_data.id,
#         # "liabilities" : temp_liability,
#         "transactionDetails" : temp_pendingTxns
#     }

#     return jsonify(response), 200


@main.route('/events/<EventName>/analytics', methods=["GET"])
@token_required
@user_in_event
def get_event_analytics(current_user, event_data):

    member_map = {}
    for user in event_data.members:
        member_map[user.id] = user.username
    
    response, sqOffTxns = [], []
    result = get_participant_Expense(event_data.id, db.engine)
    memberDues = result["GUI"]
    for userID in memberDues:
        temp_memberDue = {}
        temp_memberDue['Username'] = member_map[userID]
        temp_memberDue.update(memberDues[userID])
        response.append(temp_memberDue)
    
    squareOffs = result["SqOffs"]
    for sq in squareOffs:
        temp_SqOff = {}
        temp_SqOff["sender"] = member_map[sq[0]]
        temp_SqOff["receiver"] = member_map[sq[1]]
        temp_SqOff["Amount"] = sq[2]
        sqOffTxns.append(temp_SqOff)

    return make_response(jsonify(memberDues = response, squareOffs = sqOffTxns), 200)