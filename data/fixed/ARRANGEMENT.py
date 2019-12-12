import numpy as np
import pandas as pd
import random as rd

def ARRANGEMENT(W):
    for i in range(W.shape[0]):
        for j in range(W.shape[1]):
            if W[i][j].sum() == 0:
                W[i][j][rd.randint(1,W.shape[2])-1] = 1
    return W
