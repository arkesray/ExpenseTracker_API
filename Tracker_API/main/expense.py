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

