from .models import tbl_users
from flask import request, jsonify, current_app
from functools import wraps

import jwt
import pandas as pd


def isUserInEvent(this_user, this_eventName):
    for event in this_user.user_events:
        if event.EventName == this_eventName:
            return event
    return None
    

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

        if not token:
            return jsonify({'message' : 'Token is missing!'}), 401

        try: 
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = tbl_users.query.filter_by(Username=data['Username']).first()
        except:
            return jsonify({'message' : 'Token is invalid!'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


def expenseCalculator(person, txn) :
    txnNo = len(txn)
    liab = [0.0]*person
    payable = [0.0]*person
    paid = [0.0]*person
    ans = []

    ##################################### Calculate Paid and Liablities #####################################

    for i in range(txnNo):
        paid[txn[i][0]] += txn[i][1];
        shr = txn[i][2].count('1')
        expense = txn[i][1]/shr
        for j in range(person):
            if txn[i][2][j] == '1' :
                liab[j] += expense


    ##################################### Calculate Payable #####################################

    for i in range(person):
        payable[i] = round((liab[i] - paid[i]),3)

    #print(payable)

    maxPay = max(payable)
    maxPayInd = payable.index(maxPay)
    temInd = []
    temInd.append(maxPayInd)

    ##################################### Transactions to be made #####################################

    for i in range(person):
        if payable[i] == 0:
            temInd.append(i)
            continue
        if payable[i] > 0:
            continue
        for j in range(person):
            if i == j or payable[j] < 0:
                continue
            if payable[i]*-1 == payable[j]:
                ans.append([j,i,payable[j]])
                temInd.append(i)
                temInd.append(j)
    #print(temInd)

    for i in range(person):
        if i in temInd:
            continue
        if payable[i] < 0:
            ans.append([maxPayInd,i,payable[i]*-1])
        else:
            ans.append([i,maxPayInd,payable[i]])

    return ans


def get_participant_dues(eventID, conn):
    User_Dues = pd.read_sql(f'SELECT "UserID", sum("AvgAmount") "Dues" FROM tbl_txnshare WHERE "EventID" = {eventID} GROUP BY "UserID"', conn)
    User_Paid = pd.read_sql(f'SELECT "paidByUserID", sum("Amount") "Paid" FROM tbl_tlist WHERE "EventID" = {eventID} GROUP BY "paidByUserID"', conn)
    Event_Users = pd.read_sql(f'SELECT "UserID" FROM tbl_eventusers WHERE "EventID" = {eventID}', conn)

    temp_1 = pd.merge(Event_Users, User_Dues, how="left", left_on="UserID", right_on="UserID")
    temp_2 = pd.merge(temp_1, User_Paid, how="left", left_on="UserID", right_on="paidByUserID").fillna(0)
    temp_2["Payable"] = temp_2["Dues"] - temp_2["Paid"]

    #GUI
    max_bar = max(temp_2["Payable"].max(), temp_2["Paid"].max())
    temp_2["Paid_Bar"] = temp_2["Mask_Bar"] = temp_2["Paid"]/max_bar
    temp_2["Payable_Bar"] = temp_2["Payable"]/max_bar
    temp_2.loc[temp_2["Payable_Bar"] < 0.0, ["Mask_Bar", "Payable_Bar"]] = temp_2.loc[temp_2["Payable_Bar"] < 0.0, ["Payable_Bar", "Mask_Bar"]].values
    temp_2.loc[temp_2["Mask_Bar"] < 0.0, "Mask_Bar"] = temp_2["Payable_Bar"] + temp_2["Mask_Bar"]
    temp_2.index = temp_2["UserID"]
    
    Liability_Matrix = temp_2[["Paid", "Payable", 
                               "Paid_Bar", "Payable_Bar", "Mask_Bar"]]
    
    
    return Liability_Matrix.round(2).to_dict(orient='index')



            
    