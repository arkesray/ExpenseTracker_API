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

    print(groups)

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