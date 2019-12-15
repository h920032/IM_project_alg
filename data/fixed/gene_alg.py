import numpy as np
import pandas as pd
import random
from data.fixed.score import score

K_type = ['O','A2','A3','A4','A5','MS','AS','P2','P3','P4','P5','N1','M1','W6','CD','C2','C3','C4','OB']
K_type_dict = {1:'O',2:'A2',3:'A3',4:'A4',5:'A5',6:'MS',7:'AS',8:'P2',9:'P3',10:'P4',11:'P5',12:'N1',13:'M1',14:'W6',15:'CD',16:'C2',17:'C3',18:'C4',19:'OB'}

#def score(input):
#    return random.randint(1,10000)

def alg(score_liz, nDAY,nW, nEMPLOYEE,year,month): #演算法部分
    sort = sorted(score_liz, key = lambda s: s[2],reverse = True) #先按照分數排序
    for i in range(len(score_liz)): #從中兩兩抓取互相配對
        for j in range(len(score_liz)):
            if i != j:
                print(i)
                union = np.logical_or(score_liz[i][1], score_liz[j][1])
                one_not_avb = union * score_liz[i][0]
                one_avb = score_liz[i][0] - one_not_avb
                two_not_avb = union * score_liz[j][0]
                two_avb = score_liz[j][0] - two_not_avb
                sp_row = random.randint(0,nDAY-1)
                sp_col = random.randint(0,nEMPLOYEE-1)
                one_col_left = one_avb[:sp_col]
                one_col_right = one_avb[sp_col:]
                one_row_up = one_avb[:,:sp_row]     #!!??
                one_row_down = one_avb[:,sp_row:]
                two_col_left = two_avb[:sp_col]
                two_col_right = two_avb[sp_col:]
                two_row_up = two_avb[:,:sp_row]
                two_row_down = two_avb[:,sp_row:]
                a_one_one_two = np.concatenate((one_row_up, two_row_down), axis=1) + one_not_avb
                a_two_one_two = np.concatenate((one_row_up, two_row_down), axis=1) + two_not_avb
                a_one_two_one = np.concatenate((two_row_up, one_row_down), axis=1) + one_not_avb
                a_two_two_one = np.concatenate((two_row_up, one_row_down), axis=1) + two_not_avb
                b_one_one_two = np.concatenate((one_col_left, two_col_right), axis=0) + one_not_avb
                b_two_one_two = np.concatenate((one_col_left, two_col_right), axis=0) + two_not_avb
                b_one_two_one = np.concatenate((two_col_left, one_col_right), axis=0) + one_not_avb
                b_two_two_one = np.concatenate((two_col_left, one_col_right), axis=0) + two_not_avb
                sort.append((a_one_one_two,score_liz[i][1],score(a_one_one_two.tolist(),nDAY,nW,year=year,month=month)))
                sort.append((a_two_one_two,score_liz[j][1],score(a_two_one_two.tolist(),nDAY,nW,year=year,month=month)))
                sort.append((a_one_two_one,score_liz[i][1],score(a_one_two_one.tolist(),nDAY,nW,year=year,month=month)))
                sort.append((a_two_two_one,score_liz[j][1],score(a_two_two_one.tolist(),nDAY,nW,year=year,month=month)))
                sort.append((b_one_one_two,score_liz[i][1],score(b_one_one_two.tolist(),nDAY,nW,year=year,month=month)))
                sort.append((b_two_one_two,score_liz[j][1],score(b_two_one_two.tolist(),nDAY,nW,year=year,month=month)))
                sort.append((b_one_two_one,score_liz[i][1],score(b_one_two_one.tolist(),nDAY,nW,year=year,month=month)))
                sort.append((b_two_two_one,score_liz[j][1],score(b_two_two_one.tolist(),nDAY,nW,year=year,month=month)))
    sort = sorted(sort, key = lambda s: s[2],reverse = True) #交配完之後排序
    sort = sort[:len(score_liz)] #取出前一百名
    return sort

def gene_alg(avaliable_sol, fix, nDAY,nW, nEMPLOYEE, gen,year,month): #avaliavle_sol 可行解列表 fix 不能移動的列表
    i_nb = []
    for p in range(len(avaliable_sol)):
        #i_nb.append(np.vectorize({v: k for k, v in K_type_dict.items()}.get)(np.array(avaliable_sol[p])).tolist())
        i_nb.append(avaliable_sol[p])
    score_liz = []
    for i ,j in zip(i_nb,fix):
        score_liz.append((i,j, score(i,nDAY,nW,year=year,month=month)))
    for i in range(gen):
        score_liz = alg(score_liz, nDAY,nW, nEMPLOYEE,year,month)
    result = np.vectorize(K_type_dict.get)(score_liz[0][0])
    return result
