#initial
import numpy as np
import pandas as pd
import data.fixed.tool as tl
import datetime, calendar

def score(df_x,nDAY,nW,year,month,fixed_dir = './data/fixed/', parameters_dir = './data/parameters/', per_month_dir = './data/per_month/',AssignTest='',NeedTest='',EmployeeTest=''):
    A_t = pd.read_csv(fixed_dir + 'fix_class_time.csv', header = 0, index_col = 0)
    DEMAND_t = pd.read_csv(per_month_dir+"Need"+NeedTest+".csv", header = 0, index_col = 0, engine = 'python').T
    EMPLOYEE_t = pd.read_csv(per_month_dir+"Employee"+EmployeeTest+".csv", header = 0, engine = 'python')
    #NM_t = EMPLOYEE_t['NM']
    #NW_t = EMPLOYEE_t['NW']
    #E_NAME = list(EMPLOYEE_t['Name_English'])   #E_NAME - 對照名字與員工index時使用
    #E_SENIOR_t = EMPLOYEE_t['Senior']
    #E_POSI_t = EMPLOYEE_t['Position']
    #E_SKILL_t = EMPLOYEE_t[list(filter(lambda x: re.match('skill-',x), EMPLOYEE_t.columns))]
    #SKILL_NAME = list(E_SKILL_t.columns)
    P_t = pd.read_csv(parameters_dir + 'weight_p.csv', header = None, index_col = 0)
    Kset_t = pd.read_csv(fixed_dir + 'fix_classes.csv', header = None, index_col = 0)
    Rset_t = pd.read_csv(fixed_dir + 'fix_resttime.csv', header = None, index_col = 0) #rest set
    Shift_name = Kset_t.iloc[0].tolist()
    #SKset_t = pd.read_csv(parameters_dir + 'skill_class_limit.csv')  #class set for skills
    #M_t = pd.read_csv(per_month_dir+'Assign'+AssignTest+'.csv', header = None, skiprows=[0], engine = 'python')
    #L_t = pd.read_csv(parameters_dir+"lower_limit.csv", header = 0, engine='python')
    #U_t = pd.read_csv(parameters_dir+"upper_limit.csv", header = None, skiprows=[0])
    #Ratio_t = pd.read_csv(parameters_dir+"senior_limit.csv",header = None, skiprows=[0])
    #SENIOR_bp = Ratio_t[3]
    #timelimit = pd.read_csv(parameters_dir+"time_limit.csv", header=0)
    nightdaylimit = EMPLOYEE_t['night_perWeek']
    
    date = pd.read_csv(per_month_dir + 'Date.csv', header = None, index_col = 0)
    #year = int(date.iloc[0,0])
    #month = int(date.iloc[1,0])

    nEMPLOYEE = EMPLOYEE_t.shape[0]
    #nDAY = tl.get_nDAY(year,month)
    #nW = tl.get_nW(year,month)
    nK = A_t.shape[0]
    nT = 24
    nR = Rset_t.shape[0]
    mDAY = int(calendar.monthrange(year,month)[1])
    DEMAND = DEMAND_t.values.tolist()

    P0 = 100
    P1 = P_t[1]['P1']
    P2 = P_t[1]['P2']
    P3 = P_t[1]['P3']
    P4 = P_t[1]['P4']

    SHIFTset= {}                                                    #SHIFTset - 通用的班別集合，S=1,…,nS
    for ki in range(len(Kset_t)):
        SHIFTset[Kset_t.index[ki]] = [ tl.Tran_t2n(x,Shift_name) for x in Kset_t.iloc[ki].dropna().values ]
    for ki in range(len(Shift_name)):
        SHIFTset[Shift_name[ki]] = [ki]
    
    BREAK_t =[]
    for ki in range(len(Rset_t)):
        BREAK_t.append([ tl.Tran_t2n(x, Shift_name) for x in Rset_t.iloc[ki].dropna().values ]) 
    
    S_NIGHT = []
    S_NIGHT.extend(SHIFTset['night'])                                     #S_NIGHT - 所有的晚班
    for i in range(len(S_NIGHT)):
        S_NIGHT[i] += 1
    
    S_NOON = []
    S_NOON.extend(SHIFTset['noon'])                                       #S_NOON - 所有的午班
    for i in range(len(S_NOON)):
        S_NOON[i] += 1

    S_BREAK = [tmp for tmp in range(nR)]
    for r in range(nR):
        S_BREAK[r] = []
        for j in range(len(BREAK_t[r])):
            S_BREAK[r].append(BREAK_t[r][j]+1)

    S_DEMAND = []
    S_DEMAND.extend(SHIFTset['phone'])
    for i in range(len(S_DEMAND)):
        S_DEMAND[i] += 1
    
    #S_BREAK = [[11,12],[1,7,14,15],[2,8,16,18],[3,9,17],[4,10]]
    
    DAY = [tmp for tmp in range(nDAY)]              #DAY - 日子集合，J=0,…,nJ-1
    DATES = [ int(x) for x in DEMAND_t.index ]    #所有的日期 - 對照用
    month_start = tl.get_startD(year,month)         #本月第一天是禮拜幾 (Mon=0, Tue=1..)
    D_WEEK = tl.SetDAYW(month_start+1,mDAY,nW, DAY, DATES)  	#D_WEEK - 第 w 週中所包含的日子集合
    WEEK_of_DAY = tl.SetWEEKD(D_WEEK, nW) #WEEK_of_DAY - 日子j所屬的那一週


    #輸入班表
    """
    df_x = []
    for i in pd.read_csv("排班結果.csv", header = 0, index_col = 0).drop('name', axis = 1).values.tolist():
        df_x.append(list(filter(lambda x: x!='X', i)))
    """

    K_type = Shift_name
    # K_type = ['O','A2','A3','A4','A5','MS','AS','P2','P3','P4','P5','N1','M1','W6','CD','C2','C3','C4','OB']
    # K_type_dict = {0:'',1:'O',2:'A2',3:'A3',4:'A4',5:'A5',6:'MS',7:'AS',8:'P2',9:'P3',10:'P4',11:'P5',12:'N1',13:'M1',14:'W6',15:'CD',16:'C2',17:'C3',18:'C4',19:'OB'}
    K_type_int = {0:''}
    for i in range(len(Shift_name)):
        K_type_int[i+1] = i
    # K_type_int = {0:'',1:0,2:1,3:2,4:3,5:4,6:5,7:6,8:7,9:8,10:9,11:10,12:11,13:12,14:13,15:14,16:15,17:16,18:17,19:18}
    i_nb = np.vectorize({v: k for k, v in K_type_int.items()}.get)(np.array(df_x))
    #i_nb = df_x
    #計算人力情形

    people = np.zeros((nDAY,nT))
    #print(people)

    #print(nDAY)
    for i in range(nEMPLOYEE):
        for j in range(nDAY):
            for k in range(nT):
                #print(i,j,k)
                if i_nb[i][j] in S_DEMAND:
                    people[j][k] = people[j][k] + A_t.values[i_nb[i][j]-1][k]   

    
    output_people = (people - DEMAND).tolist()
    
    lack = 0
    for i in output_people:
        for j in i:
            if j < 0:
                lack = -j + lack

    surplus = 0
    surplus_t = 0
    for i in output_people:
        for j in i:
            if j > 0:
                surplus_t = j
                if surplus_t > surplus:
                    surplus = surplus_t

    nightcount = []
    for i in range(len(i_nb)):
        night_t = 0
        if (nightdaylimit[i]>0):
            count = 0
            for j in i_nb[i]:
                if j in S_NIGHT:
                    count = count + 1
            night_t = count / nightdaylimit[i]
        nightcount.append(night_t)
    nightcount = max(nightcount)

    breakCount = np.zeros((nEMPLOYEE,nW,5))
    for i in range(nEMPLOYEE):
        for j in range(nDAY):
            w_d = WEEK_of_DAY[j]
            for r in range(len(S_BREAK)):
                if i_nb[i][j] in S_BREAK[r]:
                    breakCount[i][w_d][r] = 1
                    break
    breakCount = int(sum(sum(sum(breakCount))))
    
    nooncount = []
    for i in i_nb:
        count = 0
        for j in i:
            if j in S_NOON:
                count = count + 1
        nooncount.append(count)
    nooncount = max(nooncount)

    result = P0 * lack + P1 * surplus + P2 * nightcount + P3 * breakCount + P4 * nooncount
    #print(result, lack, surplus, nightcount, breakCount, nooncount)
    return result
