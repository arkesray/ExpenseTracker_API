from .models import tbl_users
from flask import request, jsonify, make_response, current_app
from functools import wraps

import jwt


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
        except Exception as e:
            print(e)
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

