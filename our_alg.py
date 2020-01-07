#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, time
import numpy as np
import pandas as pd
import random as rd
import data.fixed.tool as tl
import data.fixed.gene_alg as gen
from data.fixed.CSR_order import CSR_ORDER
from data.fixed.LIMIT_ORDER import LIMIT_ORDER
from data.fixed.CONFIRM import confirm
from data.fixed.score import score
import datetime, calendar, sys

#========================================================================#
# Global Variables
#========================================================================#
# 產生親代的迴圈數
parent = 100	    # int
ordernum = 100      #limit_order的排序數量
#基因演算法的世代數量
generation = 1000
shuffle = False    

# 生成Initial pool的100個親代
INITIAL_POOL = []

miniresult = 1000000 #親代最佳分數
#=======================================================================================================#
#=======================================================================================================#
tstart_0 = time.time()  #計時用

#測試檔案檔名 - 沒有要測試時請將TestPath留空白
# TestPath = ""
EmployeeTest = "_20191230"
AssignTest = "_20191230"
NeedTest = ""
U_ttest = "_20191230"

#=======================================================================================================#
#====================================================================================================#
#=================================================================================================#
# import data
#=================================================================================================#
#====================================================================================================#
#=======================================================================================================#
#讀檔路徑import data

f = open('path.txt', "r")
dir_name = f.read().replace('\n', '')

if dir_name == "":
    dir_name = './data/'   #預設資料路徑：./data/

# 測試用
#if TestPath != "":
#    dir_name = TestPath
#    parameters_dir = TestPath
#else:
#    EmployeeTest = ""
#    AssignTest = ""
#    NeedTest = ""
print('資料輸入路徑:',dir_name)
#========================================s=====================================#
#每月更改的資料
#=============================================================================#
#year/month
date = pd.read_csv(dir_name + 'per_month/Date.csv', header = None, index_col = 0)
year = int(date.iloc[0,0])
month = int(date.iloc[1,0])

#指定排班
print('指定排班表 :',dir_name + 'per_month/Assign'+AssignTest+'.csv')
M_t = tl.readFile(dir_name + 'per_month/Assign'+AssignTest+'.csv')
#M_t = tl.readFile(dir_name + 'per_month/Assign.csv')
M_t[0] = [ str(x) for x in M_t[0] ]           #強制將ID設為string
#進線需求預估
print('連線需求表 :',dir_name+"per_month/Need"+NeedTest+".csv")
DEMAND_t = pd.read_csv(dir_name+"per_month/Need"+NeedTest+".csv", header=0, index_col=0, engine='python').T
#DEMAND_t = pd.read_csv(dir_name+"per_month/Need.csv", header=0, index_col=0, engine='python').T
DATES = [ int(x) for x in DEMAND_t.index ]    #所有的日期 - 對照用

#employees data
print('員工資料表 :',dir_name+"per_month/Employee"+EmployeeTest+".csv")
EMPLOYEE_t = pd.read_csv(dir_name+"per_month/Employee"+EmployeeTest+".csv", header = 0, engine='python') 
#EMPLOYEE_t = pd.read_csv(dir_name+"per_month/Employee.csv", header = 0) 
E_NAME = list(EMPLOYEE_t['Name_English'])       #E_NAME - 對照名字與員工index時使用
E_ID = [ str(x) for x in EMPLOYEE_t['ID'] ]     #E_ID - 對照ID與員工index時使用
E_SENIOR_t = EMPLOYEE_t['Senior']
E_POSI_t = EMPLOYEE_t['Position']
E_SKILL_t = EMPLOYEE_t[ list(filter(lambda x: re.match('skill-',x), EMPLOYEE_t.columns)) ]  #抓出員工技能表


print('員工總人數 :',len(EMPLOYEE_t),'人')
#=============================================================================#
####NM 及 NW 從人壽提供之上個月的班表裡面計算
if month>1:
    lastmonth = pd.read_csv(dir_name + 'per_month/Schedule_'+str(year)+'_'+str(month-1)+'.csv', engine='python')
else:
    lastmonth = pd.read_csv(dir_name + 'per_month/Schedule_'+str(year-1)+'_12.csv', engine='python')
lastday_column = len(lastmonth.columns) 
lastday_row = lastmonth.shape[0]
lastday_ofmonth = lastmonth.iloc[0,(lastday_column-1)]
nEMPLOYEE = EMPLOYEE_t.shape[0]

#上個月的最後一天是週五，且有排晚班者，有則是1，沒有則是0
tl.calculate_NW (EMPLOYEE_t,lastday_ofmonth,lastday_row,lastday_column,lastmonth,nEMPLOYEE)

#上個月為斷頭週，並計算該週總共排了幾次晚班
tl.calculate_NM (EMPLOYEE_t,lastday_ofmonth,lastday_row,lastday_column,lastmonth,nEMPLOYEE)
NM_t = EMPLOYEE_t['NM']
NW_t = EMPLOYEE_t['NW']
#####

#=============================================================================#
#半固定參數
#=============================================================================#
P_t = pd.read_csv(dir_name + 'parameters/weight_p.csv', header = None, index_col = 0, engine='python') #權重
L_t = pd.read_csv(dir_name + "parameters/lower_limit.csv", header = 0, engine='python')          #指定日期、班別、職位，人數下限
U_t     = tl.readFile(dir_name + "parameters/upper_limit"+U_ttest+".csv")                      #指定星期幾、班別，人數上限
U_t[0] = [ str(x) for x in U_t[0] ]           #強制將ID設為string
Ratio_t = tl.readFile(dir_name + "parameters/senior_limit.csv")                     #指定年資、星期幾、班別，要占多少比例以上

SKset_t = pd.read_csv(dir_name + 'parameters/skill_class_limit.csv')  #class set for skills
U_Kset = pd.read_csv(dir_name + 'parameters/class_upperlimit.csv')  #upper bound for class per month

try:    # 下面的try/except都是為了因應條件全空時
    SENIOR_bp = Ratio_t[3]
except:
    SENIOR_bp = []
try:
    timelimit = pd.read_csv(dir_name + "parameters/time_limit.csv", header = 0, engine='python')
    timelimit = int(timelimit.loc[0][0])
except:
    print('無法順利讀取 time_limit.csv 的數值，改用預測時間限制')
    timelimit = 300 #預設跑五分鐘
nightdaylimit = EMPLOYEE_t['night_perWeek']


#=============================================================================#
#固定參數：班別總數與時間
#=============================================================================#
Kset_t = pd.read_csv(dir_name + 'fixed/fix_classes.csv', header = None, index_col = 0) #class set
A_t = pd.read_csv(dir_name + 'fixed/fix_class_time.csv', header = 0, index_col = 0)
Posi = pd.read_csv(dir_name + 'fixed/position.csv', header = None, engine='python').iloc[0].tolist()
Shift_name = Kset_t.iloc[0].tolist()
Rset_t = pd.read_csv(dir_name + 'fixed/fix_resttime.csv', header = None, index_col = 0) #rest set

#=======================================================================================================#
#====================================================================================================#
#=================================================================================================#
# 資料前處理
#=================================================================================================#
#====================================================================================================#
#=======================================================================================================#

#============================================================================#
#Indexs 都從0開始

#i 員工 i
#j 日子 j，代表一個月中的需要排班的第 j 個日子
#k 班別 k，代表每天可選擇的不同上班別態
#t 工作時段 t，表示某日的第 t 個上班的小時
#w 週次 w，代表一個月中的第 w 週
#r 午休方式r，每個班別有不同的午休方式

#休假:0
#早班-A2/A3/A4/A5/MS/AS:1~6
#午班-P2/P3/P4/P5:7~10
#晚班-N1/M1/W6:11~13
#其他-CD/C2/C3/C4/OB:14~18

#============================================================================#
#Parameters
#-------number-------#
nEMPLOYEE = EMPLOYEE_t.shape[0]     #總員工人數
nDAY = len(DEMAND_t.index)          #總日數
nK = A_t.shape[0]                   #班別種類數
nT = 24                             #總時段數
nR = Rset_t.shape[0]                #午休種類數
nW = tl.get_nW(year,month)          #總週數
mDAY = int(calendar.monthrange(year,month)[1])

#-------Basic-------#
CONTAIN = A_t.values.tolist()      #CONTAIN_kt - 1表示班別k包含時段t，0則否
DEMAND = DEMAND_t.values.tolist()  #DEMAND_jt - 日子j於時段t的需求人數
ASSIGN = []                        #ASSIGN_ijk - 員工i指定第j天須排班別k，形式為 [(i,j,k)]

for c in range(M_t.shape[0]):
    e = tl.Tran_t2n(M_t.iloc[c,0], E_ID)
    d = tl.Tran_t2n(M_t.iloc[c,1], DATES)
    k = tl.Tran_t2n( str(M_t.iloc[c,2]),Shift_name )
    #回報錯誤
    if e!=e:
        print('指定排班表中發現不明ID：',M_t.iloc[c,0],'不在員工資料的ID列表中，請再次確認ID正確性（包含大小寫、空格、換行）')
    if d!=d:
        print('指定排班的日期錯誤：',M_t.iloc[c,1],'不是上班日（上班日指有進線預測資料的日子）')
    if k!=k:
        print('指定排班中發現不明班別：',M_t.iloc[c,2],'不在登錄的班別中，請指定班別列表中的一個班別（注意大小寫）')
    ASSIGN.append( (e, d, k) )

LMNIGHT = NM_t.values            #LMNIGHT_i - 表示員工i在上月終未滿一週的日子中曾排幾次晚班
FRINIGHT = NW_t.values           #FRINIGHT_i - 1表示員工i在上月最後一日排晚班，0則否
# -------調整權重-------#
P0 = 100    					#目標式中的調整權重(lack)
P1 = P_t[1]['P1']    			#目標式中的調整權重(surplus)
P2 = P_t[1]['P2']   	    	#目標式中的調整權重(nightCount)
P3 = P_t[1]['P3']    	   		#目標式中的調整權重(breakCount)
P4 = P_t[1]['P4']    	   		#目標式中的調整權重(noonCount)

#-----排班特殊限制-----#
LOWER = L_t.values.tolist()       	#LOWER - 日期j，班別集合ks，職位p，上班人數下限
for i in range(len(LOWER)):
    d = tl.Tran_t2n( LOWER[i][0], DATES)
    LOWER[i][0] = d
UPPER = []                          #UPPER - 員工i，日子集合js，班別集合ks，排班次數上限
for c in range(U_t.shape[0]):
    e = tl.Tran_t2n(U_t.iloc[c,0], E_ID)
    #回報錯誤
    if e==None:
        print('指定排班表中發現不明ID：',U_t.iloc[c,0],'不在員工資料的ID列表中，請再次確認ID正確性（包含大小寫、空格、換行）')
    UPPER.append( (e, U_t.iloc[c,1], U_t.iloc[c,2], U_t.iloc[c,3]) )
PERCENT = Ratio_t.values.tolist()	#PERCENT - 日子集合，班別集合，要求占比，年資分界線


#----------------新-----------------#
#特殊班別一定人數
#特殊班別每天人數相同
NOTPHONE_CLASS = []
#特殊班別假日後一天人數不同
NOTPHONE_CLASS_special = []
for i in range(SKset_t.shape[0]):
    if(SKset_t['Special'][i]==1):
        tmp = SKset_t.iloc[i].values.tolist()
        del tmp[3]

        NOTPHONE_CLASS_special.append(tmp)
    else:
        tmp = SKset_t.iloc[i].values.tolist()
        del tmp[3]
        del tmp[3]
        NOTPHONE_CLASS.append(tmp)

#特殊班別每人排班上限
Upper_shift = U_Kset.values.tolist()

#============================================================================#
#Sets
EMPLOYEE = [tmp for tmp in range(nEMPLOYEE)]    #EMPLOYEE - 員工集合，I=0,…,nI 
DAY = [tmp for tmp in range(nDAY)]              #DAY - 日子集合，J=0,…,nJ-1
TIME = [tmp for tmp in range(nT)]               #TIME - 工作時段集合，T=1,…,nT
BREAK = [tmp for tmp in range(nR)]              #BREAK - 午休方式，R=1,…,nR
WEEK = [tmp for tmp in range(nW)]               #WEEK - 週次集合，W=1,…,nW
SHIFT = [tmp for tmp in range(nK)]              #SHIFT - 班別種類集合，K=1,…,nK ;0代表休假
 
#-------員工集合-------#
E_POSITION = tl.SetPOSI(E_POSI_t,Posi)                                #E_POSITION - 擁有特定職稱的員工集合，POSI=1,…,nPOSI
E_SKILL = tl.SetSKILL(E_SKILL_t)                                 #E_SKILL - 擁有特定技能的員工集合，SKILL=1,…,nSKILL
E_SENIOR = [tl.SetSENIOR(E_SENIOR_t,tmp) for tmp in SENIOR_bp]   #E_SENIOR - 達到特定年資的員工集合    

#-------日子集合-------#
month_start = tl.get_startD(year,month)         #本月第一天是禮拜幾 (Mon=0, Tue=1..)
D_WEEK = tl.SetDAYW(month_start+1,mDAY,nW, DAY, DATES)  	#D_WEEK - 第 w 週中所包含的日子集合
DAYset = tl.SetDAY(month_start, nDAY, DATES)     		#DAYset - 通用日子集合 [all,Mon,Tue...]
WEEK_of_DAY = tl.SetWEEKD(D_WEEK, nW) #WEEK_of_DAY - 日子j所屬的那一週
VACnextdayset, NOT_VACnextdayset = tl.SetVACnext(month_start, nDAY, DATES) #VACnextdayset - 假期後或週一的日子集合

#-------班別集合-------#
SHIFTset= {}                                                    #SHIFTset - 通用的班別集合，S=1,…,nS
for ki in range(len(Kset_t)):
    SHIFTset[Kset_t.index[ki]] = [ tl.Tran_t2n(x, Shift_name) for x in Kset_t.iloc[ki].dropna().values ]
for ki in range(len(Shift_name)):
    SHIFTset[Shift_name[ki]] = [ki]
S_MORNING = SHIFTset['morning']                                 #S_MORNING - 所有的早班
S_NIGHT = SHIFTset['night']                                     #S_NIGHT - 所有的晚班
S_NOON = SHIFTset['noon']                                       #S_NOON  - 所有的午班
S_BREAK =[]
for ki in range(len(Rset_t)):
    S_BREAK.append([ tl.Tran_t2n(x, Shift_name) for x in Rset_t.iloc[ki].dropna().values ]) 


#============================================================================#
#Variables

work = {}  #work_ijk - 1表示員工i於日子j值班別為k的工作，0 則否 ;workij0=1 代表員工i在日子j休假
for i in range(nEMPLOYEE):
    for j in range(nDAY):
        for k in range(nK):
            work[i, j, k] = False  

"""
#Test Variables
lack = {}  #y_jt - 代表第j天中時段t的缺工人數
for j in range(nDAY):
    for t in range(nT):
        lack[j, t] = 0
        
surplus = 0 #每天每個時段人數與需求人數的差距中的最大值
nightCount = 0 #員工中每人排晚班總次數的最大值

breakCount = {}  #breakCount_iwr - 1表示員工i在第w周中在午休時段r有午休，0則否
for i in range(nEMPLOYEE):
    for w in range(nW):
        for r in range(nR):
            breakCount[i, w, r] = False

noonCount = 0 #員工中每人排午班總次數的最大值
"""

#============================================================================#

"""============================================================================#
新變數
CURRENT_DEMAND[j,t]: 日子j時段t的剩餘需求人數
LIMIT_MATRIX[a]: LIMIT_ORDER函數所生成的matrix，預設5種排序
LIMIT_LIST[b]: LIMIT_MATRIX的第a種限制式排序的限制式順序
n_LIMIT_LIST: 人數硬限制式的個數
LIMIT: LIMIT_LIST的第b個限制式
CSR_LIST: CSR_ORDER函數所生成的list
BOUND: 人數下限

總表的資料結構：bool  x[i, j, k]	 	i=人, j=日子, k=班別

限制式的資料結構：
[	上限/下限/比例 (‘upper’/’lower’/’ratio’),
	人的組合, 
	工作日的組合, 
	班別的組合, 
	幾人/比例 
]
============================================================================#"""

#========================================================================#
# class
#========================================================================#
class Pool():
    def __init__(self, result, df_x1):
        #result: 目標式結果
        self.result = result
        #df_x1 : 員工班表(整數班別)
        self.df_x1 = df_x1
	

#========================================================================#
# ABLE(i,j,k): 確認員工i在日子j是否可排班別k 
#========================================================================#
def ABLE(this_i,this_j,this_k):
    ans = True
    
    #only one work a day
    for k in SHIFT:
        if(work[this_i,this_j,k] == 1) and (k != this_k):    
            ans = False
            return ans
    #被指定的排班及當天被排除的排班
    for tmp in ASSIGN:
        if(tmp[0]==this_i):
            if(tmp[1]==this_j):
                #被指定的排班
                if(tmp[2]==this_k):
                    return ans
                else:
                    ans = False
                    return ans
    
    #判斷是否正在排晚班
    arrangenightshift = False
    for tmp in S_NIGHT:
        if(this_k == tmp):
            arrangenightshift = True
            
    #正在排晚班才進去判斷
    if(arrangenightshift == True):
        #no continuous night shift:
        
        if(this_j!=0 and this_j!=nDAY-1): #非第一天或最後一天
            for tmp in S_NIGHT:
                if(work[this_i,this_j-1,tmp] == 1):
                    ans = False
                    return ans
                if(work[this_i,this_j+1,tmp] == 1):
                    ans = False
                    return ans
        elif (this_j==nDAY-1):           #最後一天
            for tmp in S_NIGHT:
                if(work[this_i,this_j-1,tmp] == 1):
                    ans = False
                    return ans
        else:                             #第一天
            if(FRINIGHT[this_i] == 1):
                ans = False
                return ans
            for tmp in S_NIGHT:
                if(work[this_i,this_j+1,tmp] == 1):
                    ans = False
                    return ans
        #no too many night shift a week:
        whichweek = WEEK_of_DAY[this_j]
        #非第一週
        if(whichweek!=0):
            countnightshift = 0
            for theday in D_WEEK[whichweek]:
                for tmp in S_NIGHT:
                    if(work[this_i,theday,tmp] == 1):
                        if(theday == this_j and tmp == this_k):
                            countnightshift += 0
                        else:
                            countnightshift += 1
            if(countnightshift >= nightdaylimit[this_i]):
                ans = False
                return ans              
        #第一週
        else:
            countnightshift = 0
            for theday in D_WEEK[0]:
                for tmp in S_NIGHT:
                    if(work[this_i,theday,tmp] == 1):
                        if(theday == this_j and tmp == this_k):
                            countnightshift += 0
                        else:
                            countnightshift += 1
            if(countnightshift+LMNIGHT[this_i] >= nightdaylimit[this_i]):
                ans = False
                return ans            
            
    #排班的上限
    for item in UPPER:
        if(this_i == item[0] and this_j in DAYset[item[1]] and this_k in SHIFTset[item[2]]):
            tmpcount = 0
            for whichday in DAYset[item[1]]:
                for tmp in  SHIFTset[item[2]]:
                    if(work[this_i,whichday,tmp]==1):
                        if(whichday == this_j and tmp == this_k):
                            tmpcount+=0
                        else:
                            tmpcount+=1
            if(tmpcount>=item[3]):
                ans = False
                return ans

    

    
    #排特殊技能班別的上限
    
    #有每月總數上限
    for item in Upper_shift:
        if(this_k in SHIFTset[item[0]]):
            if(this_i in E_SKILL['phone']):
                tmpcount = 0
                for whichday in DAY:
                    if(work[this_i,whichday,this_k]==1):
                        if(whichday == this_j):
                            tmpcount+=0
                        else:
                            tmpcount+=1
                if(tmpcount>=item[1]):
                    ans = False
                    return ans
            else:   #無此技能
                ans = False
                return ans
    
    
    #特殊技能排班
    for item in NOTPHONE_CLASS:
        if(this_k in SHIFTset[item[0]]):
            if(this_i in E_SKILL[item[2]]):
                tmpcount = 0
                for people in EMPLOYEE:
                    if(work[people,this_j,this_k]==1):
                        if(people == this_i):
                            tmpcount+=0
                        else:
                            tmpcount+=1
                if(tmpcount>=item[1]):
                    ans = False
                    return ans
            else:   #無此技能
                ans = False
                return ans

    #特殊技能排班（有假日後要多人的限制）
    for item in NOTPHONE_CLASS_special:
        if(this_k in SHIFTset[item[0]]):
            if(this_i in E_SKILL[item[2]]):
                tmpcount = 0
                for people in EMPLOYEE:
                    if(work[people,this_j,this_k]==1):
                        if(people == this_i):
                            tmpcount+=0
                        else:
                            tmpcount+=1
                            
                if(this_j in VACnextdayset):
                    if(tmpcount>=item[3]):
                        ans = False
                        return ans                  
                else:
                    if(tmpcount>=item[1]):
                        ans = False
                        return ans
            else:   #無此技能
                ans = False
                return ans            
               
    
    return ans                 

def REPEAT(this_i,this_j,this_k):   #一次安排可滿足多條限制式時使用
    ans = False
    
    for k in SHIFT:
        if(work[this_i,this_j,k] == 1) and (k == this_k):    
            ans = True
    return ans                    
#========================================================================#
# GENE(): 切分並交配的函數 
#========================================================================#
def GENE(K_type_dict, timelimit, avaliable_sol, fix, nDAY,nW, nEMPLOYEE, generation,year,month,\
ASSIGN, S_NIGHT, D_WEEK, nightdaylimit,\
    LOWER, SHIFTset, E_POSITION, UPPER, PERCENT, E_SENIOR, Upper_shift, NOTPHONE_CLASS, NOTPHONE_CLASS_special, E_SKILL, DAYset,\
    VACnextdayset, NOT_VACnextdayset, FRINIGHT, LMNIGHT,\
    per_month_dir='./data/per_month/',AssignTest='',NeedTest='',EmployeeTest=''):
	return gen.gene_alg(K_type_dict, timelimit, avaliable_sol, fix, nDAY,nW, nEMPLOYEE, generation,year,month,\
        ASSIGN, S_NIGHT, D_WEEK, nightdaylimit,\
        LOWER, SHIFTset, E_POSITION, UPPER, PERCENT, E_SENIOR, Upper_shift, NOTPHONE_CLASS, NOTPHONE_CLASS_special, E_SKILL, DAYset,\
        VACnextdayset, NOT_VACnextdayset, FRINIGHT, LMNIGHT,\
        per_month_dir,AssignTest=AssignTest,NeedTest=NeedTest,EmployeeTest=EmployeeTest)

#========================================================================#
# SHIFT_ORDER(): 班別排序的函數 
#========================================================================#
def takeNeck(alist):
	try:
		return alist[-1]
	except:
		print('找不到項目 ',end='')
		print(alist,end='')
		print(' 的瓶頸程度參數')
		return None
def SHIFT_ORDER(demand, shift, nT, CONTAIN, day, csr=-1):
    ans = []
    for i in shift:
        demand_t = []
        demand_t.extend(demand)
        for t in range(nT):
            if CONTAIN[i][t] == 1:
                demand_t[t] -=1
        dem_l = np.array(demand_t)
        dem_s = np.array(demand_t)
        dem_ni = 0
        dem_br = 0
        dem_no = 0
        for j in range(len(dem_l)):
            if dem_l[j] < 0:
                dem_l[j] = 0
        for j in range(len(dem_s)):
            if dem_s[j] > 0:
                dem_s[j] = 0
        if i in S_NIGHT:
            if csr != -1:
                dem_ni = 1/nightdaylimit[csr]
            else:
                dem_ni = 1
        elif i in S_NOON:
            dem_no = 1
        if csr != -1:
            takebreak = -1
            for r in range(len(S_BREAK)):
                if i in S_BREAK[r]:
                    takebreak = r
                    break
            if takebreak != -1:
                found = False
                w = WEEK_of_DAY[day]
                for y in D_WEEK[w]:
                    for k in SHIFT:
                        if work[csr,y,k] == True:
                            if k in S_BREAK[takebreak]:
                                dem_br = 0
                                found = True
                                break
                            else:
                                dem_br = 1
                                break
                    if found == True:
                        break

        d = P0 * np.sum(dem_l) + P1 * max(dem_s) + P2 * dem_ni + P3 * dem_br + P4 * dem_no
        ans.append([i,d])
    ans.sort(key=takeNeck, reverse=False)

    return ans 

def RATIO_CSR_ORDER(demand, shift, nT, CONTAIN, day, csr_list):
    ans = []
    for i in csr_list:
        demand_t = []
        demand_t.extend(demand)
        for t in range(nT):
            if CONTAIN[shift][t] == 1:
                demand_t[t] -=1
        dem_l = np.array(demand_t)
        dem_s = np.array(demand_t)
        dem_ni = 0
        dem_br = 0
        dem_no = 0
        for j in range(len(dem_l)):
            if dem_l[j] < 0:
                dem_l[j] = 0
        for j in range(len(dem_s)):
            if dem_s[j] > 0:
                dem_s[j] = 0
        if shift in S_NIGHT:
            if nightdaylimit[i] > 0:
                dem_ni = 1/nightdaylimit[i]
            else:
                dem_ni = 1000000
        elif shift in S_NOON:
            dem_no = 1
        takebreak = -1
        for r in range(len(S_BREAK)):
            if shift in S_BREAK[r]:
                takebreak = r
                break
        if takebreak != -1:
            found = False
            w = WEEK_of_DAY[day]
            for y in D_WEEK[w]:
                for k in SHIFT:
                    if work[i,y,k] == True:
                        if k in S_BREAK[takebreak]:
                            dem_br = 0
                            found = True
                            break
                        else:
                            dem_br = 1
                            break
                if found == True:
                    break

        d = P0 * np.sum(dem_l) + P1 * max(dem_s) + P2 * dem_ni + P3 * dem_br + P4 * dem_no
        ans.append([i,d])
    ans.sort(key=takeNeck, reverse=False)

    return ans

def SPECIAL_CSR_ORDER(shift, nT, CONTAIN, day, csr_list):
    ans = []
    for i in csr_list:
        dem_ni = 0
        dem_br = 0
        if shift in S_NIGHT:
            if nightdaylimit[i] > 0:
                dem_ni = 1/nightdaylimit[i]
            else:
                dem_ni = 1000000
        takebreak = -1
        for r in range(len(S_BREAK)):
            if shift in S_BREAK[r]:
                takebreak = r
                break
        if takebreak != -1:
            found = False
            w = WEEK_of_DAY[day]
            for y in D_WEEK[w]:
                for k in SHIFT:
                    if work[i,y,k] == True:
                        if k in S_BREAK[takebreak]:
                            dem_br = 0
                            found = True
                            break
                        else:
                            dem_br = 1
                            break
                if found == True:
                    break

        d = P2 * dem_ni + P3 * dem_br
        ans.append([i,d])
    ans.sort(key=takeNeck, reverse=False)

    return ans
#=======================================================================================================#
#====================================================================================================#
#=================================================================================================#
#  main function
#=================================================================================================#
#====================================================================================================#
#=======================================================================================================#

LIMIT_MATRIX = LIMIT_ORDER(ordernum,LOWER,NOTPHONE_CLASS,NOTPHONE_CLASS_special,\
    PERCENT,DEMAND,E_POSITION,E_SENIOR,E_SKILL,DAYset,VACnextdayset,NOT_VACnextdayset,SHIFTset,CONTAIN) #生成多組限制式matrix
#print(LIMIT_MATRIX)
sequence = 0 #限制式順序
char = 'a' #CSR沒用度順序
fix = [] #存可行解的哪些部分是可以動的

#迴圈計時
tStart = time.time()
#成功數計算
success = 0
#產生100個親代的迴圈
for p in range(parent):
    
    #動態需工人數
    CURRENT_DEMAND = [tmp for tmp in range(nDAY)]
    for j in DAY:
        CURRENT_DEMAND[j] = []
        for t in range(nT):
            CURRENT_DEMAND[j].append(DEMAND[j][t])
    
    #指定班別
    for c in ASSIGN:
        work[c[0],c[1],c[2]] = True
        if c[2] in SHIFTset['phone']: #非其他班別時扣除需求
            for t in range(nT):
                if CONTAIN[c[2]][t] == 1:
                    CURRENT_DEMAND[c[1]][t] -= 1
    
    #瓶頸排班
    LIMIT_LIST = LIMIT_MATRIX[sequence] #一組限制式排序
    LIMIT = [] #一條限制式
    CSR_LIST = [] #可排的員工清單
    BOUND = [] #限制人數
    for l in range(len(LIMIT_LIST)):
        LIMIT = LIMIT_LIST[l]
        nightbound = False
        #print(LIMIT)
        for n in S_NIGHT:
            if LIMIT[3][0] == n:
                nightbound = True
                break
        CSR_LIST = CSR_ORDER(char, LIMIT[0], LIMIT[1], EMPLOYEE_t, Posi, nightbound) #員工沒用度排序
        for j in LIMIT[2]:
            if shuffle == True:
                rd.shuffle(CSR_LIST)
            if LIMIT[0] == 'lower' :
                BOUND = LIMIT[4]
                for i in CSR_LIST:
                    DAY_DEMAND = []
                    DAY_DEMAND.extend(CURRENT_DEMAND[j])
                    SHIFT_SET = SHIFT_ORDER(DAY_DEMAND, LIMIT[3], nT, CONTAIN, j, i)
                    SHIFT_LIST = []
                    if nightbound == True:
                        SHIFT_LIST.append(12)
                    for k in range(len(SHIFT_SET)):
                        SHIFT_LIST.append(SHIFT_SET[k][0])
                    if BOUND <= 0:  #若限制式參數(n)不合理，忽略之
                        break
                    for k in SHIFT_LIST:  
                        if BOUND <= 0:
                            break
                        elif ABLE(i, j, k) == True: #若此人可以排此班，就排
                            repeat = False
                            if REPEAT(i, j, k) == True:
                                repeat = True
                            work[i, j, k] = True
                            if k in SHIFTset['phone'] and repeat == False: #非其他班別時扣除需求
                                for t in range(nT):
                                    if CONTAIN[k][t] == 1:              
                                        CURRENT_DEMAND[j][t] -= 1
                            BOUND -= 1
                        else:
                            continue
            elif LIMIT[0] == 'ratio':
                DAY_DEMAND = []
                DAY_DEMAND.extend(CURRENT_DEMAND[j])
                SHIFT_SET = SHIFT_ORDER(DAY_DEMAND, LIMIT[3], nT, CONTAIN, j)
                SHIFT_LIST = []
                if nightbound == True:
                    SHIFT_LIST.append(12)
                for k in range(len(SHIFT_SET)):
                    SHIFT_LIST.append(SHIFT_SET[k][0])
                for k in SHIFT_LIST:
                    BOUND = LIMIT[4]
                    RATIO_CSR_SET = RATIO_CSR_ORDER(DAY_DEMAND, k, nT, CONTAIN, j, CSR_LIST)
                    RATIO_CSR_LIST = []
                    for i in range(len(RATIO_CSR_SET)):
                        RATIO_CSR_LIST.append(RATIO_CSR_SET[i][0])
                    for i in RATIO_CSR_LIST:
                        if BOUND <= 0:
                            break
                        elif ABLE(i, j, k) == True: #若此人可以排此班，就排
                            repeat = False
                            if REPEAT(i, j, k) == True:
                                repeat = True
                            work[i, j, k] = True
                            if k in SHIFTset['phone'] and repeat == False: #非其他班別時扣除需求
                                for t in range(nT):
                                    if CONTAIN[k][t] == 1:              
                                        CURRENT_DEMAND[j][t] -= 1
                            BOUND -= 1
                        else:
                            continue
            elif LIMIT[0] == 'skill':
                for k in LIMIT[3]:
                    BOUND = LIMIT[4]
                    SPECIAL_CSR_SET = SPECIAL_CSR_ORDER(k, nT, CONTAIN, j, CSR_LIST)
                    SPECIAL_CSR_LIST = []
                    for i in range(len(SPECIAL_CSR_SET)):
                        SPECIAL_CSR_LIST.append(SPECIAL_CSR_SET[i][0])
                    for i in SPECIAL_CSR_LIST:
                        if BOUND <= 0:
                            break
                        elif ABLE(i, j, k) == True: #若此人可以排此班，就排
                            repeat = False
                            if REPEAT(i, j, k) == True:
                                repeat = True
                            work[i, j, k] = True
                            if k in SHIFTset['phone'] and repeat == False: #非其他班別時扣除需求
                                for t in range(nT):
                                    if CONTAIN[k][t] == 1:              
                                        CURRENT_DEMAND[j][t] -= 1
                            BOUND -= 1
                        else:
                            continue
            elif LIMIT[0] == 'skill_special':
                for k in LIMIT[3]:
                    BOUND = LIMIT[4]
                    SPECIAL_CSR_SET = SPECIAL_CSR_ORDER(k, nT, CONTAIN, j, CSR_LIST)
                    SPECIAL_CSR_LIST = []
                    for i in range(len(SPECIAL_CSR_SET)):
                        SPECIAL_CSR_LIST.append(SPECIAL_CSR_SET[i][0])
                    for i in SPECIAL_CSR_LIST:
                        if BOUND <= 0:
                            break
                        elif ABLE(i, j, k) == True: #若此人可以排此班，就排
                            repeat = False
                            if REPEAT(i, j, k) == True:
                                repeat = True
                            work[i, j, k] = True
                            if k in SHIFTset['phone'] and repeat == False: #非其他班別時扣除需求
                                for t in range(nT):
                                    if CONTAIN[k][t] == 1:              
                                        CURRENT_DEMAND[j][t] -= 1
                            BOUND -= 1
                        else:
                            continue
    
    sequence += 1
    if sequence >= len(LIMIT_MATRIX) and char == 'a':
        sequence = 0
        char = 'b'
    elif sequence >= len(LIMIT_MATRIX) and char == 'b':
        sequence = 0
        char = 'c'
    elif sequence >= len(LIMIT_MATRIX) and char == 'c':
        sequence = 0
        char = 'd'
    elif sequence >= len(LIMIT_MATRIX) and char == 'd':
        sequence = 0
        char = 'e'
    elif sequence >= len(LIMIT_MATRIX) and char == 'e':
        sequence = 0
        char = 'a'
    
    
    
    #=================================================================================================#
    #安排空班別
    #=================================================================================================#
    fix_temp = []
    for i in range(nEMPLOYEE):
        employee = []
        for j in range(nDAY):
            is_arrange = False
            for k in range(nK):
                if work[i,j,k] == True:
                    for c in ASSIGN:
                        if i == c[0] and j == c[1] and k == c[2]:
                            is_arrange = True
                            employee.append(1)
                            break
                    if is_arrange == False:
                        is_arrange = True
                        employee.append(1)
            if is_arrange == False:
                DAY_DEMAND = []
                DAY_DEMAND.extend(CURRENT_DEMAND[j])
                SHIFT_SET = SHIFT_ORDER(DAY_DEMAND, SHIFTset['phone'], nT, CONTAIN, j, i)
                SHIFT_LIST = []
                for k in range(len(SHIFT_SET)):
                    SHIFT_LIST.append(SHIFT_SET[k][0])
                #優先排能減少缺工冗員最多的班
                for r in SHIFT_LIST:
                    if ABLE(i,j,r) == True and REPEAT(i, j, r) == False:
                        work[i,j,r] = True
                        if r in SHIFTset['phone']: #非其他班別時扣除需求
                            for t in range(nT):
                                if CONTAIN[r][t] == 1:              
                                    CURRENT_DEMAND[j][t] -= 1
                        is_arrange = True
                        employee.append(0)
                        break
        fix_temp.append(employee)
    #work, fix_temp, CURRENT_DEMAND = ARRANGEMENT(work, nEMPLOYEE, nDAY, nK, CONTAIN, CURRENT_DEMAND, nT)
    fix.append(fix_temp)    
    


    """
    #=================================================================================================#
    #計算變數
    #=================================================================================================#
    surplus_temp = 0
    for j in DAY:
        for t in TIME:
            if CURRENT_DEMAND[j][t] > 0:    
                lack[j, t] = CURRENT_DEMAND[j][t]
            else:
                surplus_temp = -1 * CURRENT_DEMAND[j][t]
                if surplus_temp > surplus:
                    surplus = surplus_temp

    nightCount_temp = {}
    for i in EMPLOYEE:
        nightCount_temp[i] = 0
        if (nightdaylimit[i]>0):
            for j in DAY:
                for k in S_NIGHT:
                    if work[i, j, k] == True:
                        nightCount_temp[i] += 1
                        break
            nightCount_temp[i] = nightCount_temp[i] / nightdaylimit[i]
        if nightCount_temp[i] > nightCount:
            nightCount = nightCount_temp[i]
    
    for i in EMPLOYEE:
        for w in WEEK:
            for j in D_WEEK[w]:
                for r in BREAK:
                    for k in S_BREAK[r]:
                        if work[i, j, k] == True:
                            breakCount[i,w,r] = True
    
    noonCount_temp = {}
    for i in EMPLOYEE:
        noonCount_temp[i] = 0
        for j in DAY:
            for k in S_NOON:
                if work[i, j, k] == True:
                    noonCount_temp[i] += 1
                    break
        if noonCount_temp[i] > noonCount:
            noonCount = noonCount_temp[i]
    """
    #=================================================================================================#
    # 輸出
    #=================================================================================================#
    #Dataframe_x
    K_type = Shift_name
    K_type_dict = {}
    for i in range(len(K_type)):
        K_type_dict[i] = K_type[i]
    
    employee_name = E_NAME
    employee_name2 = EMPLOYEE
    which_worktime = []
    which_worktime2 = []
    for i in EMPLOYEE:
        tmp = []
        tmp2 = []
        for j in DAY:
            for k in SHIFT:
                if(work[i,j,k]==True):
                    tmp.append(K_type[k])
                    tmp2.append(k)
                    break
            else:
                print('CSR ',E_NAME[i],' 在',DATES[j],'號的排班發生錯誤。')
                print('請嘗試讓程式運行更多時間，或是減少限制條件。\n')
        which_worktime.append(tmp)
        which_worktime2.append(tmp2)
            

    df_x = pd.DataFrame(which_worktime, index = employee_name, columns = DATES)   #字串班表
    df_x1 = pd.DataFrame(which_worktime2, index = employee_name, columns = DATES) #整數班表
    df_x2 = which_worktime2                                                       #confirm用
    
    #print(df_x)
    #=================================================================================================#
    #確認解是否可行
    #=================================================================================================#
    message = 'All constraints are met.'
    message = confirm(df_x2, ASSIGN, S_NIGHT, D_WEEK, nightdaylimit,\
        LOWER, SHIFTset, E_POSITION, UPPER, DAYset, PERCENT, E_SENIOR, Upper_shift,\
        NOTPHONE_CLASS, NOTPHONE_CLASS_special, E_SKILL, DAYset, VACnextdayset, NOT_VACnextdayset, nDAY, FRINIGHT, LMNIGHT)
        
    
    #====================================================================================================#
    #計算目標式
    #====================================================================================================#
    result = score(df_x1,nDAY,nW,year=year,month=month,per_month_dir=dir_name+'per_month/',AssignTest=AssignTest,NeedTest=NeedTest,EmployeeTest=EmployeeTest)
    """
    sumlack = 0
    for j in range(nDAY):
        for t in range(nT):
            sumlack += lack[j, t]
    
    sumbreak = 0
    for i in EMPLOYEE:
        for w in WEEK:
             for r in BREAK:
                if breakCount[i,w,r] == True:
                    sumbreak += 1
    
    result2 = P0 * sumlack + P1 * surplus + P2 * nightCount + P3 * sumbreak + P4 * noonCount
    print(result2, sumlack, surplus, nightCount, sumbreak, noonCount)
    """
    #====================================================================================================#
    #將結果放入INITIAL_POOL中
    #====================================================================================================#
    INITIAL_POOL.append(Pool(result, df_x1))
    
    for i in range(nEMPLOYEE):
        for j in range(nDAY):
            for k in range(nK):
                work[i, j, k] = False
    """
    #print("result2 = ", result2)
    for j in range(nDAY):
        for t in range(nT):
            lack[j, t] = 0
    
    surplus = 0
    nightCount = 0

    for i in range(nEMPLOYEE):
        for w in range(nW):
            for r in range(nR):
                breakCount[i, w, r] = False
    
    noonCount = 0
    """
    
    if message != 'All constraints are met.':
        INITIAL_POOL[p].result = INITIAL_POOL[p].result * 1000000
    else:
        success += 1

    print('\n生成INITIAL POOL： parent =',p,', result =', INITIAL_POOL[p].result)
    print(message)
    if message != 'All constraints are met.':
        print('Some constraints fails.')
    if INITIAL_POOL[p].result < miniresult:
        miniresult = INITIAL_POOL[p].result
    
    if p == parent-1:
        print("\nINITIAL POOL completed")
        
    #====================================================================================================#
    #====================================================================================================#
print('\n產生',parent,'個結果於 initail pool (',success,'個合理解) ，共花費', (time.time()-tStart) ,'秒')
print("\n親代最佳分數: result = ",miniresult,'\n\n')

avaliable_sol = []

for i in range(parent):
    avaliable_sol.append(INITIAL_POOL[i].df_x1.values.tolist())



#=======================================================================================================#
#====================================================================================================#
#=================================================================================================#
#  切分並交配
#=================================================================================================#
#====================================================================================================#
#=======================================================================================================#
tstart_gen = time.time()
print('\n基因演算法開始')
print('time limit =',timelimit)
gene_result = GENE(K_type_dict, timelimit,avaliable_sol, fix, nDAY,nW, nEMPLOYEE, generation,year,month,\
    ASSIGN, S_NIGHT, D_WEEK, nightdaylimit,\
    LOWER, SHIFTset, E_POSITION, UPPER, PERCENT, E_SENIOR, Upper_shift, NOTPHONE_CLASS, NOTPHONE_CLASS_special, E_SKILL, DAYset,\
    VACnextdayset, NOT_VACnextdayset, FRINIGHT, LMNIGHT,\
    per_month_dir=dir_name+'per_month/',AssignTest=AssignTest,NeedTest=NeedTest,EmployeeTest=EmployeeTest)


#=======================================================================================================#
#====================================================================================================#
#=================================================================================================#
#  輸出
#=================================================================================================#
#====================================================================================================#
#=======================================================================================================#
print('基因演算法共耗時',time.time()-tstart_gen,'秒\n')
print('基因演算法進行',generation,'代\n')
schedule = pd.DataFrame(gene_result, index = employee_name, columns = DATES)
#print(schedule)
#schedule.to_csv(EmployeeTest[1:]+'alg_Schedul_2019_4.csv', encoding="utf-8_sig")

#輸出檔名
result_x = './alg_Schedule_'+str(year)+'_'+str(month)+'.csv'
result_y = './alg_lack&over_'+str(year)+'_'+str(month)+'.csv'
result = './alg_schedule_data_'+str(year)+'_'+str(month)+'.xlsx'



#============================================================================#
#輸出班表
#============================================================================#
output_name = []
output_id = []
for i in range(0,nEMPLOYEE):
    output_id.append(str(EMPLOYEE_t.ID.values.tolist()[i]))
for i in range(0,nEMPLOYEE):
    output_name.append(EMPLOYEE_t.Name_Chinese.values.tolist()[i])
mDAY = int(calendar.monthrange(year,month)[1])
date_list = []
date_name = []
for i in range(1,mDAY+1): #產生日期清單
    weekday=""
    date = datetime.datetime.strptime(str(year)+'-'+str(month)+'-'+str(i), "%Y-%m-%d")
    date_list.append(date)
    if date.weekday()==5:
        weekday="六"
    elif date.weekday()==6:
        weekday="日"
    elif date.weekday()==0:
        weekday="一"
    elif date.weekday()==1:
        weekday="二"
    elif date.weekday()==2:
        weekday="三"
    elif date.weekday()==3:
        weekday="四"
    else:
        weekday="五"
    date_name.append(date.strftime("%Y-%m-%d")+' ('+weekday+')')

new = pd.DataFrame()
new['name'] = output_name
NO_WORK=[]
for i in range(0,nEMPLOYEE): #假日全部填X
    NO_WORK.append("X")

for i in range(0,mDAY):
    if (i+1) not in DATES:
        new[date_name[i]] = NO_WORK
    else:
        new[date_name[i]] = schedule[i+1].values.tolist()

new['id']=output_id
new.set_index("id",inplace=True)
new.to_csv(result_x, encoding="utf-8_sig")
#print(new)

#============================================================================#
#輸出冗員與缺工人數表
#============================================================================#
T_type = ['09:00','09:30','10:00','10:30','11:00','11:30','12:00','12:30','13:00','13:30','14:00','14:30'
        ,'15:00','15:30','16:00','16:30','17:00','17:30','18:00','18:30','19:00','19:30','20:00','20:30']


K_type_dict= {}
K_type_dict= {0:None}
for ki in range(1,len(Shift_name)+1):
    K_type_dict[ki] =Shift_name[ki-1]
#K_type_dict = {0:'None',1:'O',2:'A2',3:'A3',4:'A4',5:'A5',6:'MS',7:'AS',8:'P2',9:'P3',10:'P4',11:'P5',12:'N1',13:'M1',14:'W6',15:'CD',16:'C2',17:'C3',18:'C4',19:'OB'}
try:
    x_nb = np.vectorize({v: k for k, v in K_type_dict.items()}.get)(np.array(schedule))
except:
    print('無法輸出缺工冗員表：排班班表不完整，請嘗試讓程式運行更多時間。')
    try:
        sys.exit(0)     #出錯的情況下，讓程式退出
    except:
        print('\n程式已結束。')
S_DEMAND = []
S_DEMAND.extend(SHIFTset['phone'])
for i in range(len(S_DEMAND)):
    S_DEMAND[i] += 1

people = np.zeros((nDAY,nT))
for i in range(nEMPLOYEE):
    for j in range(nDAY):
        for k in range(nT):
            if x_nb[i][j] in S_DEMAND:
                people[j][k] = people[j][k] + A_t.values[x_nb[i][j]-1][k]
output_people = (people - DEMAND).tolist()

NO_PEOPLE=[]
new_2=pd.DataFrame()
for i in range(0,24):
    NO_PEOPLE.append('X')
j = 0
for i in range(0,mDAY):
    if (i+1) not in DATES:
        new_2[date_name[i]]=NO_PEOPLE
    else:
        new_2[date_name[i]]= [ int(x) for x in output_people[j] ]
        j = j + 1
new_2['name']=T_type
new_2.set_index("name",inplace=True)
new_2.to_csv(result_y, encoding="utf-8_sig")
# print(new_2.T)

# ============================================================================ #
# 輸出其他資訊
# ============================================================================ #
S_NIGHT_dict = []
S_NIGHT_dict.extend(SHIFTset['night'])                                     #S_NIGHT - 所有的晚班
for i in range(len(S_NIGHT_dict)):
    S_NIGHT_dict[i] += 1

S_NOON_dict = []
S_NOON_dict.extend(SHIFTset['noon'])                                       #S_NOON - 所有的午班
for i in range(len(S_NOON_dict)):
    S_NOON_dict[i] += 1

S_BREAK_dict = [tmp for tmp in range(nR)]
for r in range(nR):
    S_BREAK_dict[r] = []
    for j in range(len(S_BREAK[r])):
        S_BREAK_dict[r].append(S_BREAK[r][j]+1)

#Dataframe_y
lesspeople_count = []
for j in DAY:
    tmp = []
    for x in output_people[j]:
        if x < 0:
            tmp.append(int(x)*(-1))
        else:
            tmp.append(0)
    lesspeople_count.append(tmp)


df_y = pd.DataFrame(lesspeople_count, index = DATES, columns = T_type) #which_day , columns = T_type)

#計算總和
df_y['SUM_per_day'] = df_y.sum(axis=1)
df_y.loc['SUM_per_time'] = df_y.sum()

#計算需求
demand_day = DEMAND_t.sum(axis=1).values
demand_time = DEMAND_t.sum().values
#計算缺工比例
less_percent_day = (df_y['SUM_per_day'].drop(['SUM_per_time']).values)/demand_day
less_percent_time = (df_y.loc['SUM_per_time'].drop(['SUM_per_day']).values)/demand_time
df_percent_day = pd.DataFrame(less_percent_day, index = DATES, columns = ["Percentage"]) #which_day , columns = ["Percentage"])
df_percent_time = pd.DataFrame(less_percent_time, index = T_type , columns = ["Percentage"])


#h1h2
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

print("\n所有天每個時段人數與需求人數的差距中的最大值 = "+str(int(surplus))+"\n")



#晚班次數dataframe
night_work_total = []
nightcount = []
for i in range(len(x_nb)):
    night_t = 0
    if (nightdaylimit[i]>0):
        count = 0
        for j in x_nb[i]:
            if j in S_NIGHT_dict:
                count = count + 1
        night_work_total.append(count)
        night_t = count / nightdaylimit[i]
    nightcount.append(night_t)     
nightCount = max(nightcount)


df_nightcount = pd.DataFrame(night_work_total, index = employee_name, columns = ['NightWork_count'])
print("\n員工中每人排晚班次數加權平均的最大值 = "+str(int(nightCount))+"\n")


#午班次數dataframe
noon_work_total = []
nooncount = []
for i in x_nb:
    count = 0
    for j in i:
        if j in S_NOON_dict:
            count = count + 1
    nooncount.append(count)
    noon_work_total.append(count)
noonCount = max(nooncount)


df_nooncount = pd.DataFrame(noon_work_total, index = employee_name, columns = ['NoonWork_count'])
print("\n員工中每人排午班總次數的最大值 = "+str(int(noonCount))+"\n")

      
#休息時間 Dataframe_z
breakCount = np.zeros((nEMPLOYEE,nW,5))
for i in range(nEMPLOYEE):
    for j in range(nDAY):
        w_d = WEEK_of_DAY[j]
        for r in range(len(S_BREAK_dict)):
            if x_nb[i][j] in S_BREAK_dict[r]:
                breakCount[i][w_d][r] = 1
                break
breakcount = int(sum(sum(sum(breakCount))))

R_type = ['11:30','12:00','12:30','13:00','13:30']     
which_week = [tmp+1 for tmp in WEEK] 
which_resttime = []     
for i in EMPLOYEE:
    tmp = []
    for w in WEEK:
        tmp2 = []
        for r in BREAK:
            if(breakCount[i][w][r]==1):
                tmp2.append(R_type[r])
        tmp.append(tmp2)
    which_resttime.append(tmp)


df_resttime = pd.DataFrame(which_resttime, index=employee_name, columns=which_week)




with pd.ExcelWriter(result) as writer:
    schedule.to_excel(writer, sheet_name="員工排班表")
    df_nightcount.to_excel(writer, sheet_name="員工本月晚班次數")
    df_percent_time.to_excel(writer, sheet_name="每個時段缺工百分比表")
    df_percent_day.to_excel(writer, sheet_name="每天缺工百分比表")
    df_nightcount.to_excel(writer, sheet_name="員工本月晚班次數")
    df_nooncount.to_excel(writer, sheet_name="員工本月午班次數")
    df_y.to_excel(writer, sheet_name="缺工人數表")
    df_resttime.to_excel(writer, sheet_name="員工每週有哪幾種休息時間")

#========================================================================#
# program end
#========================================================================#
print('\n\ncheck point 2\n')
print(new)

print('\n\nlack = ',lack, ', surplus = ',surplus, ', nightCount = ',nightCount, ', breakCount = ',breakcount, ', noonCount = ',noonCount)
score = P0 * lack + P1 * surplus + P2 * nightCount + P3 * breakcount + P4 * noonCount
print('score:',score)

print('\n\n*** Done in', time.time()-tstart_0 ,'sec. ***')
