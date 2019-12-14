import numpy as np
import pandas as pd
import random as rd

def ARRANGEMENT(work, nEMPLOYEE, nDAY, nK, CONTAIN, CURRENT_DEMAND, nT):
    fix = []
    for i in range(nEMPLOYEE):
        employee = []
        for j in range(nDAY):
            is_arrange = False
            for k in range(nK):
                if work[i,j,k] == True:
                    is_arrange = True
                    employee.append(1)
            if is_arrange == False:
                rand = rd.randint(1,nK)
                work[i,j,rand-1] = True
                for t in range(nT):
                    if CONTAIN[rand-1][t] == 1:              
                        CURRENT_DEMAND[j][t] -= 1
                employee.append(0)
        fix.append(employee)
    return work, fix, CURRENT_DEMAND
