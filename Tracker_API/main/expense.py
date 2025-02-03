def grpSumZero(index, payable, total, tem) :

    #print(index, payable, total, tem)

    if total == 0 :
        return True

    if index == len(payable) :
        return False

    if grpSumZero(index+1,payable,total,tem) : 
        return True

    if total == None :
        total = 0
        

    if grpSumZero(index+1,payable,total + payable[index][0], tem) : 
        tem.append(payable[index])
        payable.pop(index)
        return True


def expenseCalculator(payable) :
    
    groups = []

    ans = []

    while payable :
        tem = []
        total = None

        if grpSumZero(0,payable,total,tem) :
            groups.append(tem)
            
        else :
            print("Something went wrong.")
            break

    for grp in groups :
        maxPay = max(grp)
        maxPayInd = grp.index(maxPay)
        #print(maxPayInd)
        
        for i in grp :

            if i[1] == maxPay[1] :
                continue

            if i[0] < 0:
                ans.append([maxPay[1],i[1],i[0]*-1])
            else:
                ans.append([i[1],maxPay[1],i[0]])
    #print("TXNS : ")
    #print(ans)
    return ans


def calcLiability(person, txn) :
    txnNo = len(txn)
    liab = [0.0]*person
    payable = []*person
    paid = [0.0]*person
    ans = []

    ##################################### Calculate Paid and Liablities #####################################

    for i in range(txnNo):
        paid[txn[i][0]] += txn[i][1]
        shr = txn[i][2].count('1')
        expense = txn[i][1]/shr
        for j in range(person):
            if txn[i][2][j] == '1' :
                liab[j] += expense


    ##################################### Calculate Payable #####################################

    for i in range(person):
        payable.append([round((liab[i] - paid[i]),3),i])

    return payable