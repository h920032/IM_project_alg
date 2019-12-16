import numpy as np
import pandas as pd
import random as rd

def ARRANGEMENT(work, nEMPLOYEE, nDAY, nK):
    for i in range(nEMPLOYEE):
        for j in range(nDAY):
            is_arrange = False
            for k in range(nK):
                if work[i,j,k] == True:
                    is_arrange = True
            if is_arrange == False:
                work[i,j,rd.randint(1,nK)-1] = True
    return work
