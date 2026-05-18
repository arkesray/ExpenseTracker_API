from .models import User
from flask import request, jsonify, current_app
from functools import wraps
import datetime

import jwt
import pandas as pd
import heapq


def isUserInEvent(this_user, this_eventName):
    for event in this_user.events:
        if event.name == this_eventName:
            return event
    return None
    

def user_in_event(f):
    """Decorator for routes that require the current user to be a member of the event.

    Usage:
      @token_required
      @user_in_event
      def handler(current_user, event, ...):
          # event is the Event object the user belongs to

    The decorator expects the wrapped function to accept `current_user` as
    the first argument (provided by `token_required`) and the event name as
    the next positional argument (from the route). It replaces the event
    name with the actual Event object and returns 403 JSON when not found.
    """
    @wraps(f)
    def decorated(current_user, EventName, *args, **kwargs):
        event = isUserInEvent(current_user, EventName)
        if not event:
            return jsonify(message="Event doesn't exist or You are not Authorised "), 403
        return f(current_user, event, *args, **kwargs)

    return decorated
    

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
            current_user = User.query.filter_by(username=data['username']).first()
        except:
            return jsonify({'message' : 'Token is invalid!'}), 401

        return f(current_user, *args, **kwargs)

    return decorated



def to_iso_z(dt):
    """Return ISO 8601 UTC string with trailing Z (milliseconds precision).

    Accepts naive or tz-aware datetimes. Returns None for falsy inputs.
    """
    if not dt:
        return None
    if not isinstance(dt, datetime.datetime):
        return str(dt)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    dt_utc = dt.astimezone(datetime.timezone.utc)
    s = dt_utc.isoformat(timespec='milliseconds')
    # normalize +00:00 to Z
    if s.endswith('+00:00'):
        s = s[:-6] + 'Z'
    return s


def get_expense_matrix(eventID, conn):
    # 1. Fetch data from SQL (Swapped hardcoded 'Taki' for %s parameter)
    expenses_query = """
        SELECT 
            t.id AS tx_id,
            u_for.username AS paidfor, 
            u_by.username AS paidby, 
            ts.share_amount AS amount, 
            t.description AS item
        FROM events AS e
        JOIN transactions AS t ON e.id = t.event_id
        JOIN transaction_shares AS ts ON t.id = ts.transaction_id
        JOIN users AS u_for ON ts.user_id = u_for.id
        JOIN users AS u_by ON t.paid_by_id = u_by.id
        WHERE t.is_expense = TRUE 
        AND e.id = %s;
    """
    expenses = pd.read_sql(expenses_query, conn, params=(eventID,))
    
    if expenses.empty:
        print("No expenses found for this event.")
        return pd.DataFrame()

    # 2. Base Pivot Table (No native margins to prevent warnings)
    pivot_base = expenses.pivot_table(
        index="tx_id",
        columns="paidfor",
        values="amount",
        aggfunc="sum"
    ).fillna(0)

    # 3. Create maps using the lowercase column outputs from PostgreSQL
    item_map = expenses.set_index("tx_id")["item"].to_dict()
    paid_by_map = expenses.set_index("tx_id")["paidby"].to_dict()

    # 4. Map text columns to the flat row layout
    pivot_base.insert(0, "Item", pivot_base.index.map(item_map))
    pivot_base["PaidBy"] = pivot_base.index.map(paid_by_map)

    # 5. Build the column-wise Grand Total row safely
    numeric_cols = pivot_base.select_dtypes(include='number').columns
    total_row = pd.DataFrame(pivot_base[numeric_cols].sum()).T
    total_row.index = ["Members Total"]

    # 6. Glue the total row to the bottom
    expenses_pivot = pd.concat([pivot_base, total_row])

    # 7. Calculate the row-wise Grand Total column
    expenses_pivot["Items Total"] = expenses_pivot[numeric_cols].sum(axis=1)

    # 8. Clean up NaN fields in the text columns for the Grand Total row
    expenses_pivot[["Item", "PaidBy"]] = expenses_pivot[["Item", "PaidBy"]].fillna("")

    # 9. Reorder columns so 'PaidBy' stays on the absolute far right
    all_cols = list(expenses_pivot.columns)
    all_cols.remove("PaidBy")
    all_cols.append("PaidBy")
    expenses_pivot = expenses_pivot[all_cols]

    # Optional: Capitalize the column names index header for display aesthetics
    expenses_pivot.columns.name = "Paid For"
    expenses_pivot.index.name = "Tx ID"

    # print(expenses_pivot)
    return expenses_pivot


def get_settlement_matrix(eventID, conn):
    settlements_query = """
        SELECT 
            u_by.username AS "from", 
            u_for.username AS "to", 
            ROUND(ts.share_amount, 4) AS amount
        FROM events AS e
        JOIN transactions AS t ON e.id = t.event_id
        JOIN transaction_shares AS ts ON t.id = ts.transaction_id
        JOIN users AS u_for ON ts.user_id = u_for.id
        JOIN users AS u_by ON t.paid_by_id = u_by.id
        WHERE t.is_expense = FALSE 
        AND e.id = %s;
    """
    # Pandas natively accepts db.engine here
    settlements = pd.read_sql(settlements_query, conn, params=(eventID,))

    if settlements.empty:
        print("No settlements found for this event.")
        return []

    # Fast conversion to list of dicts
    settlement_txns = settlements.to_dict(orient='records')
    
    # print("Existing Settlements:", settlement_txns)
    return settlement_txns



def calculate_required_settlements(expenses_dict, paid_dict, prior_settlements=None):
    if prior_settlements is None:
        prior_settlements = []

    # 1. Calculate initial net balances (Paid - Expense)
    balances = {}
    all_members = set(expenses_dict.keys()).union(set(paid_dict.keys()))
    
    for member in all_members:
        total_paid = paid_dict.get(member, 0.0)
        total_expense = expenses_dict.get(member, 0.0)
        balances[member] = total_paid - total_expense

    # 2. Adjust for prior settlements
    # If A paid B, A's balance increases (they owe less) 
    # and B's balance decreases (they are owed less)
    for settlement in prior_settlements:
        payer = settlement['from']
        receiver = settlement['to']
        amount = settlement['amount']
        
        balances[payer] += amount
        balances[receiver] -= amount

    # 3. Separate into Debtors and Creditors using Heaps
    debtors = []   # Min-heap for negative balances (largest absolute debt stays at top)
    creditors = [] # Min-heap storing inverted positive balances (acts as Max-heap)

    # Use a small tolerance (0.0001) to ignore floating-point rounding errors
    for member, balance in balances.items():
        if balance < -0.0001:
            heapq.heappush(debtors, (balance, member))
        elif balance > 0.0001:
            heapq.heappush(creditors, (-balance, member))

    # 4. Greedily match largest debtor with largest creditor
    transactions = []
    
    while debtors and creditors:
        debt_val, debtor = heapq.heappop(debtors)
        cred_val_neg, creditor = heapq.heappop(creditors)

        # Convert back to positive amounts for transaction sizing
        debt_amt = -debt_val
        cred_amt = -cred_val_neg

        # The transaction is the minimum of what the debtor owes and creditor is owed
        settle_amt = round(min(debt_amt, cred_amt), 4)

        if settle_amt > 0:
            transactions.append({'from': debtor, 'to': creditor, 'amount': settle_amt})

        # Calculate remainders
        rem_debt = debt_amt - settle_amt
        rem_cred = cred_amt - settle_amt

        # Push back to heaps if they still owe / are owed money
        if rem_debt > 0.0001:
            heapq.heappush(debtors, (-rem_debt, debtor))
        if rem_cred > 0.0001:
            heapq.heappush(creditors, (-rem_cred, creditor))

    return transactions

            


# def get_participant_Expense(eventID, conn):
#     # User_Expense = pd.read_sql(f'SELECT "user_id", sum("share_amount") "Expense" FROM transaction_shares WHERE "event_id" = {eventID} GROUP BY "user_id"', conn)
#     # User_Paid = pd.read_sql(f'SELECT "payer_id", sum("amount") "Paid" FROM transactions WHERE "event_id" = {eventID} GROUP BY "payer_id"', conn)
#     # Event_Users = pd.read_sql(f'SELECT "user_id" FROM event_members WHERE "event_id" = {eventID}', conn)
#     # temp_1 = pd.merge(Event_Users, User_Expense, how="left", left_on="UserID", right_on="UserID")
#     # temp_2 = pd.merge(temp_1, User_Paid, how="left", left_on="UserID", right_on="paidByUserID").fillna(0)

#     sql_query = f"""
#     WITH 
#         ExpenseSub AS (
#             SELECT ts."user_id" AS "UserID", SUM(ts."share_amount") AS "Expense"
#             FROM transaction_shares ts
#             WHERE "event_id" = {eventID}
#             GROUP BY "user_id"
#         ),
#         PaidSub AS (
#             SELECT t."paid_by" AS "UserID", SUM(t."amount") AS "Paid"
#             FROM transactions t
#             WHERE t."event_id" = {eventID}
#             GROUP BY t."paid_by"
#         )
#         SELECT 
#             eu."user_id" AS "UserID",
#             COALESCE(e."Expense", 0) AS "Expense",
#             COALESCE(p."Paid", 0) AS "Paid",
#             (COALESCE(e."Expense", 0) - COALESCE(p."Paid", 0)) AS "Payable"
#         FROM event_members eu
#         LEFT JOIN ExpenseSub e ON eu."user_id" = e."UserID"
#         LEFT JOIN PaidSub p ON eu."user_id" = p."UserID"
#         WHERE eu."event_id" = {eventID};
#     """
#     agg_expense = pd.read_sql(sql_query, conn)

#     sender = [ [r[0],round(r[1],3)] for r in agg_expense.loc[agg_expense["Payable"] > 0.0, ["UserID", "Payable"]].values.tolist()]
#     receiver = [ [r[0],round(-1.0*r[1],3)] for r in agg_expense.loc[agg_expense["Payable"] < 0.0, ["UserID", "Payable"]].values.tolist()]
#     sender.sort(key = lambda x:x[1])
#     receiver.sort(key = lambda x:x[1], reverse=True)
#     # print(sender, receiver)

#     To, From, Txn = 0, 0, []
#     while To < len(receiver):
#         Amount = receiver[To][1]
#         while Amount - sender[From][1] >= 0:
#             Amount = Amount - sender[From][1]
#             Txn.append([sender[From][0], receiver[To][0], sender[From][1]])
#             sender.pop(From)
#             receiver[To][1] = Amount
#             if len(sender) == 0:
#                 break
#         To += 1
    
#     # print(Txn)
#     # print("Sender List: ", sender)
#     # print("Receiver List: ",receiver)

#     To, From = 0, 0
#     while From < len(sender):
#         if len(receiver) == 0 or len(sender) == 0:
#             break
#         while To < len(receiver):
#             Excess = sender[From][1] - receiver[To][1]
#             if Excess > 0:
#                 Txn.append([sender[From][0], receiver[To][0], receiver[To][1]])
#                 receiver.pop(To)
#                 sender[From][1] = Excess
#             elif Excess == 0:
#                 Txn.append([sender[From][0], receiver[To][0], receiver[To][1]])
#                 receiver.pop(To)
#                 sender.pop(From)
#             else:
#                 Txn.append([sender[From][0], receiver[To][0], sender[From][1]])
#                 receiver[To][1] = -Excess
#                 sender.pop(From)
#             if len(receiver) == 0 or len(sender) == 0:
#                 break
    
#     # print(Txn)
#     # print(sender)
#     # print(receiver)
#     Txn = [[int(t[0]), int(t[1]), round(t[2], 2)] for t in Txn]

#     #GUI
#     # max_bar = max(temp_2["Payable"].max(), temp_2["Paid"].max())
#     # temp_2["Paid_Bar"] = temp_2["Mask_Bar"] = temp_2["Paid"]/max_bar
#     # temp_2["Payable_Bar"] = temp_2["Payable"]/max_bar
#     # temp_2.loc[temp_2["Payable_Bar"] < 0.0, ["Mask_Bar", "Payable_Bar"]] = temp_2.loc[temp_2["Payable_Bar"] < 0.0, ["Payable_Bar", "Mask_Bar"]].values
#     # temp_2.loc[temp_2["Mask_Bar"] < 0.0, "Mask_Bar"] = temp_2["Payable_Bar"] + temp_2["Mask_Bar"]
#     # temp_2.loc[temp_2["Payable"] > 0.0, "Payable_Bar"] = temp_2["Mask_Bar"] + temp_2["Payable_Bar"]
#     # temp_2.index = temp_2["UserID"]
#     # Liability_Matrix = temp_2[["Paid", "Payable", 
#     #                            "Paid_Bar", "Payable_Bar", "Mask_Bar"]]

#     sql_query_gui = f"""
#     WITH 
#         TList AS (
#             SELECT * FROM transactions WHERE "event_id" = {eventID}
#         ),
#         ExpenseSub AS (
#             SELECT ts."user_id" AS "UserID", SUM(ts."share_amount") AS "Expense"
#             FROM transaction_shares ts
#             INNER JOIN TList t ON ts."transaction_id" = t."id" AND t."is_expense" = TRUE
#             GROUP BY ts."user_id"
#         ),
#         ReceiveSub AS (
#             SELECT ts."user_id" AS "UserID", SUM(ts."share_amount") AS "Received"
#             FROM transaction_shares ts
#             INNER JOIN TList t ON ts."transaction_id" = t."id" AND t."is_expense" = FALSE
#             GROUP BY ts."user_id"
#         ),
#         PaidSub AS (
#             SELECT t."paid_by" AS "UserID", SUM(t."amount") AS "Paid"
#             FROM transactions t
#             WHERE t."event_id" = {eventID} and t."is_expense" = TRUE
#             GROUP BY t."paid_by"
#         ),
#         SqoffSub AS (
#             SELECT t."paid_by" AS "UserID", SUM(t."amount") AS "Transferred"
#             FROM transactions t
#             WHERE t."event_id" = {eventID} and t."is_expense" = False
#             GROUP BY t."paid_by"
#         )
#         SELECT 
#             eu."user_id" AS "UserID",
#             COALESCE(e."Expense", 0) AS "Expense",
#             COALESCE(r."Received", 0) AS "Received",
#             COALESCE(p."Paid", 0) AS "Paid",
#             COALESCE(s."Transferred", 0) AS "Transferred",
#             COALESCE("Expense" + "Received" - "Paid" - "Transferred", 0) AS "Payable"
#         FROM event_members eu
#         LEFT JOIN ExpenseSub e ON eu."user_id" = e."UserID"
#         LEFT JOIN PaidSub p ON eu."user_id" = p."UserID"
#         LEFT JOIN SqoffSub s ON eu."user_id" = s."UserID"
#         LEFT JOIN ReceiveSub r ON eu."user_id" = r."user_id"
#         WHERE eu."event_id" = {eventID};
#     """

#     agg_expense_gui = pd.read_sql(sql_query_gui, conn)
#     print(agg_expense_gui) 
#     max_bar = max(agg_expense_gui["Expense"].max(), agg_expense_gui["Received"].max(),
#                   agg_expense_gui["Paid"].max(), agg_expense_gui["Transferred"].max(),
#                   agg_expense_gui["Payable"].max(), )
#     agg_expense_gui["Expense_Bar"] = agg_expense_gui["Expense"]/max_bar
#     agg_expense_gui["Received_Bar"] = agg_expense_gui["Received"]/max_bar
#     agg_expense_gui["Paid_Bar"] = agg_expense_gui["Paid"]/max_bar
#     agg_expense_gui["Transferred_Bar"] = agg_expense_gui["Transferred"]/max_bar
#     agg_expense_gui["Payable_Bar"] = agg_expense_gui["Payable"].abs()/max_bar

#     agg_expense_gui.index = agg_expense_gui["UserID"]
#     Liability_Matrix = agg_expense_gui[["Expense","Received", "Paid", "Transferred", "Payable", 
#                                "Expense_Bar","Received_Bar", "Paid_Bar", "Transferred_Bar", "Payable_Bar"]]

#     result = {"GUI" : Liability_Matrix.round(2).to_dict(orient='index'),
#               "SqOffs" : Txn}
#     return result

# def expenseCalculator(person, txn) :
#     txnNo = len(txn)
#     liab = [0.0]*person
#     payable = [0.0]*person
#     paid = [0.0]*person
#     ans = []

#     ##################################### Calculate Paid and Liablities #####################################

#     for i in range(txnNo):
#         paid[txn[i][0]] += txn[i][1];
#         shr = txn[i][2].count('1')
#         expense = txn[i][1]/shr
#         for j in range(person):
#             if txn[i][2][j] == '1' :
#                 liab[j] += expense


#     ##################################### Calculate Payable #####################################

#     for i in range(person):
#         payable[i] = round((liab[i] - paid[i]),3)

#     #print(payable)

#     maxPay = max(payable)
#     maxPayInd = payable.index(maxPay)
#     temInd = []
#     temInd.append(maxPayInd)

#     ##################################### Transactions to be made #####################################

#     for i in range(person):
#         if payable[i] == 0:
#             temInd.append(i)
#             continue
#         if payable[i] > 0:
#             continue
#         for j in range(person):
#             if i == j or payable[j] < 0:
#                 continue
#             if payable[i]*-1 == payable[j]:
#                 ans.append([j,i,payable[j]])
#                 temInd.append(i)
#                 temInd.append(j)
#     #print(temInd)

#     for i in range(person):
#         if i in temInd:
#             continue
#         if payable[i] < 0:
#             ans.append([maxPayInd,i,payable[i]*-1])
#         else:
#             ans.append([i,maxPayInd,payable[i]])

#     return ans

