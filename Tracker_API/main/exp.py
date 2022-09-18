def calcLiability(person, txn) :
    txnNo = len(txn)
    liab = [0.0]*person
    payable = []*person
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
        payable.append([round((liab[i] - paid[i]),3),i])

    return payable
