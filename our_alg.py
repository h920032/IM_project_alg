#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import numpy as np
import pandas as pd
import data.fixed.tool as tl
import data.fixed.gene_alg as gen
from data.fixed.CSR_order import CSR_ORDER
from data.fixed.LIMIT_ORDER import LIMIT_ORDER
from data.fixed.ARRANGEMENT import ARRANGEMENT
from data.fixed.CONFIRM import confirm
import datetime, calendar, sys
"""============================================================================#
12/3
	- 建立主架構
12/4
	- 建立POOL
12/6
    - main function
    - 在tool中建立製作WEEK_of_DAY的函數
12/8
    -ABLE函數完成
    -檔名修改成英文(與solver同步)
============================================================================#"""

#=======================================================================================================#
#====================================================================================================#
#=================================================================================================#
# 請大家把自己的函數放在 data/fixed/ (和tool.py同一個位置)
# 再將自己的函數引進這裡 (這樣主程式的版本比較好控管)
#=================================================================================================#
#====================================================================================================#
#=======================================================================================================#



#=======================================================================================================#
#====================================================================================================#
#=================================================================================================#
# import data
#=================================================================================================#
#====================================================================================================#
#=======================================================================================================#
#讀檔路徑import data
try:
    f = open('path.txt', "r")
    dir_name = f.read().replace('\n', '')
except:
    f = './data/'   #預設資料路徑：./data/

#=============================================================================#
#每月更改的資料
#=============================================================================#
#year/month
date = pd.read_csv(dir_name + 'per_month/Date.csv', header = None, index_col = 0)
year = int(date.iloc[0,0])
month = int(date.iloc[1,0])

#指定排班
M_t = tl.readFile(dir_name + 'per_month/Assign.csv')
M_t[0] = [ str(x) for x in M_t[0] ]           #強制將ID設為string
#進線需求預估
DEMAND_t = pd.read_csv(dir_name+"per_month/Need.csv", header = 0, index_col = 0, engine='python').T
DATES = [ int(x) for x in DEMAND_t.index ]    #所有的日期 - 對照用

#employees data
EMPLOYEE_t = pd.read_csv(dir_name+"per_month/Employee.csv", header = 0) 
E_NAME = list(EMPLOYEE_t['Name_English'])       #E_NAME - 對照名字與員工index時使用
E_ID = [ str(x) for x in EMPLOYEE_t['ID'] ]     #E_ID - 對照ID與員工index時使用
E_SENIOR_t = EMPLOYEE_t['Senior']
E_POSI_t = EMPLOYEE_t['Position']
E_SKILL_t = EMPLOYEE_t[ list(filter(lambda x: re.match('skill-',x), EMPLOYEE_t.columns)) ]  #抓出員工技能表


#=============================================================================#
####NM 及 NW 從人壽提供之上個月的班表裡面計算
if month>1:
    lastmonth = pd.read_csv(dir_name + 'per_month/Schedule_'+str(year)+'_'+str(month-1)+'.csv', engine='python')
else:
    lastmonth = pd.read_csv(dir_name + 'per_month/Schedule_'+str(year-1)+'_1.csv', engine='python')
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
P_t = pd.read_csv(dir_name + 'parameters/weight_p1-4.csv', header = None, index_col = 0, engine='python') #權重
SKset_t = pd.read_csv(dir_name + 'parameters/skills_classes.csv', header = None, index_col = 0, engine='python')   #class set for skills
L_t = tl.readFile(dir_name + "parameters/lower_limit.csv")                          #指定日期、班別、職位，人數下限
U_t = tl.readFile(dir_name + "parameters/upper_limit.csv")                          #指定星期幾、班別，人數上限
Ratio_t = tl.readFile(dir_name + "parameters/senior_limit.csv")                     #指定年資、星期幾、班別，要占多少比例以上
try:    # 下面的try/except都是為了因應條件全空時
    SENIOR_bp = Ratio_t[3]
except:
    SENIOR_bp = []
try:
    timelimit = pd.read_csv(dir_name + "parameters/time_limit.csv", header = 0, engine='python')
except:
    timelimit = 300 #預設跑五分鐘
nightdaylimit = EMPLOYEE_t['night_perWeek']


#=============================================================================#
#固定參數：班別總數與時間
#=============================================================================#
Kset_t = pd.read_csv(dir_name + 'fixed/fix_classes.csv', header = None, index_col = 0) #class set
A_t = pd.read_csv(dir_name + 'fixed/fix_class_time.csv', header = 0, index_col = 0)




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
nK = 19                             #班別種類數
nT = 24                             #總時段數
nR = 5                              #午休種類數
nW = tl.get_nW(year,month)          #總週數
# nPOSI =  len(set(E_POSI_t))     #職稱數量 (=擁有特定職稱的總員工集合數
# nSKILL = len(SKILL_NAME)     #nVA技能數量 (=擁有特定技能的總員工集合數

#-------Basic-------#
CONTAIN = A_t.values.tolist()      #CONTAIN_kt - 1表示班別k包含時段t，0則否

DEMAND = DEMAND_t.values.tolist()  #DEMAND_jt - 日子j於時段t的需求人數
ASSIGN = []                        #ASSIGN_ijk - 員工i指定第j天須排班別k，形式為 [(i,j,k)]

for c in range(M_t.shape[0]):
    e = tl.Tran_t2n(M_t.iloc[c,0], E_ID)
    d = tl.Tran_t2n(M_t.iloc[c,1], DATES)
    k = tl.Tran_t2n( str(M_t.iloc[c,2]) )
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
P4 = P_t[1]['P4']    	 		#目標式中的調整權重(complement)

#-----排班特殊限制-----#
LOWER = L_t.values.tolist()       	#LOWER - 日期j，班別集合ks，職位p，上班人數下限
for i in range(len(LOWER)):
    d = tl.Tran_t2n( LOWER[i][0], DATES)
    LOWER[i][0] = d
UPPER = U_t.values.tolist()		   	#UPPER - 員工i，日子集合js，班別集合ks，排班次數上限
PERCENT = Ratio_t.values.tolist()	#PERCENT - 日子集合，班別集合，要求占比，年資分界線

#============================================================================#
#Sets
EMPLOYEE = [tmp for tmp in range(nEMPLOYEE)]    #EMPLOYEE - 員工集合，I=1,…,nI 
DAY = [tmp for tmp in range(nDAY)]              #DAY - 日子集合，J=0,…,nJ-1
TIME = [tmp for tmp in range(nT)]               #TIME - 工作時段集合，T=1,…,nT
BREAK = [tmp for tmp in range(nR)]              #BREAK - 午休方式，R=1,…,nR
WEEK = [tmp for tmp in range(nW)]               #WEEK - 週次集合，W=1,…,nW
SHIFT = [tmp for tmp in range(nK)]              #SHIFT - 班別種類集合，K=1,…,nK ;0代表休假
 
#-------員工集合-------#
E_POSITION = tl.SetPOSI(E_POSI_t)                                #E_POSITION - 擁有特定職稱的員工集合，POSI=1,…,nPOSI
E_SKILL = tl.SetSKILL(E_SKILL_t)                                 #E_SKILL - 擁有特定技能的員工集合，SKILL=1,…,nSKILL
E_SENIOR = [tl.SetSENIOR(E_SENIOR_t,tmp) for tmp in SENIOR_bp]   #E_SENIOR - 達到特定年資的員工集合    

#-------日子集合-------#
month_start = tl.get_startD(year,month)         #本月第一天是禮拜幾 (Mon=0, Tue=1..)
D_WEEK = tl.SetDAYW(month_start+1,nDAY,nW)  	#D_WEEK - 第 w 週中所包含的日子集合
DAYset = tl.SetDAY(month_start, nDAY)     		#DAYset - 通用日子集合 [all,Mon,Tue...]

WEEK_of_DAY = tl.SetWEEKD(month_start+1,nDAY,nW) #WEEK_of_DAY - 日子j所屬的那一週

#-------班別集合-------#
S_NIGHT = [11, 12, 13]                                          #S_NIGHT - 所有的晚班
nS_NIGHT = 3
S_BREAK = [[11,12],[1,7,14,15],[2,8,16,18],[3,9,17],[4,10]]     #Kr - 午休方式為 r 的班別 

SHIFTset= {}                                                    #SHIFTset - 通用的班別集合，S=1,…,nS
for ki in range(len(Kset_t)):
    SHIFTset[Kset_t.index[ki]] = [ tl.Tran_t2n(x) for x in Kset_t.iloc[ki].dropna().values ]

SKILL_NAME = []                                             #SKILL_NAME - 技能的種類
for ki in range(len(SKset_t)):
    SKILL_NAME.append(SKset_t.index[ki])

K_skill = {}                                                #K_skill - 各技能的優先班別
for ki in range(len(SKset_t)):
    K_skill[SKset_t.index[ki]] = [ tl.Tran_t2n(x) for x in SKset_t.iloc[ki].dropna().values ]       #各個技能的優先班別

K_skill_not = {}                                                #K_skill_not - 各技能的優先班別的補集
for ki in range(len(SKset_t)):
    K_skill_not[SKset_t.index[ki]] = list(set(range(0,nK)).difference(set(tl.Tran_t2n(x) for x in SKset_t.iloc[ki].dropna().values)))  #各個技能的非優先班別

#============================================================================#
#Variables

work = {}  #work_ijk - 1表示員工i於日子j值班別為k的工作，0 則否 ;workij0=1 代表員工i在日子j休假
for i in range(nEMPLOYEE):
    for j in range(nDAY):
        for k in range(nK):
            work[i, j, k] = False  
           
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


complement =  0  #complement - 擁有特定員工技能的員工集合va的員工排非特定班別數的最大值


#============================================================================#

"""============================================================================#
新變數
CAPACITY_NIGHT[i,j]: 1表示員工i在日子j能排晚班，0則否
ALREADY[i,j]: 1表示員工i在日子已經排班，0則否
CURRENT_DEMAND[j,t]: 日子j時段t的剩餘需求人數
WEEK_of_DAY[j]: 日子j所屬的那一週
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
    def __init__(self, result, df_x, df_y, df_percent_day, df_percent_time, df_nightcount, df_resttime, df_result_x, df_result_y):
        #result: 目標式結果
        self.result = result
        #df_x : 員工班表
        self.df_x = df_x
        #df_y: 缺工人數表
        self.df_y =  df_y
        #df_percent_day: 每天缺工百分比表
        self.df_percent_day = df_percent_day 
        #df_percent_time: 每個時段缺工百分比表
        self.df_percent_time = df_percent_time
        #df_nightcount: 員工本月晚班次數
        self.df_nightcount = df_nightcount
        #df_resttime: 員工休息時間表
        self.df_resttime = df_resttime
        #df_result_x: 排班結果
        self.df_result_x = df_result_x
        #df_result_y: 冗員與缺工人數
        self.df_result_y = df_result_y
	


#========================================================================#
# Global Variables
#========================================================================#
year = 2019
month = 4

# 產生親代的迴圈數
parent = 100	# int

# 生成Initial pool的100個親代
INITIAL_POOL = []


#=======================================================================================================#
#====================================================================================================#
#=================================================================================================#
# 函數 (工作分配)
#=================================================================================================#
#====================================================================================================#
#=======================================================================================================#


#========================================================================#
# LIMIT_ORDER(): 生成多組限制式 matrix 的函數 (林亭)
#========================================================================#



#========================================================================#
# CSR_ORDER(): 排序員工沒用度的函數 (碩珉)
#========================================================================#





#========================================================================#
# ABLE(i,j,k): 確認員工i在日子j是否可排班別k (嬿鎔)
#========================================================================#
def ABLE(this_i,this_j,this_k):
    ans = True
    
    #only one work a day
    for k in SHIFT:
        if( work[this_i,this_j,k] == 1 and k!=this_k):    #!!!報錯：KeyError: ('phone', 0, 0)
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
        #非第一天
        if(this_j!=0):
            for tmp in S_NIGHT:
                if(work[this_i,this_j-1,tmp] == 1):
                    ans = False
                    return ans
        
        #第一天
        else:
            if(FRINIGHT[this_i] == 1):
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
        if(this_j in DAYset[item[0]] and this_k in SHIFTset[item[1]]):
            tmpcount = 0
            for people in EMPLOYEE:
                for tmp in  SHIFTset[item[1]]:
                    if(work[people,this_j,tmp]==1):
                        if(people == this_i and tmp == this_k):
                            tmpcount+=0
                        else:
                            tmpcount+=1
            if(tmpcount>=item[2]):
                ans = False
                return ans
    return ans                 
                    
#========================================================================#
# ARRANGEMENT(): 安排好空著的班別的函數 (星宇)
#========================================================================#


#========================================================================#
# CONFIRM(): 確認解是否可行的函數 (學濂)
#========================================================================#
#需檢查變數不為負數


#========================================================================#
# GENE(): 切分並交配的函數 (星宇)
#========================================================================#
def GENE(avaliable_sol, fix, nDAY, nEMPLOYEE, gen):
	return gen.gene_alg(avaliable_sol, fix, nDAY, nEMPLOYEE, gen)






#=======================================================================================================#
#====================================================================================================#
#=================================================================================================#
#  main function
#=================================================================================================#
#====================================================================================================#
#=======================================================================================================#

LIMIT_MATRIX = LIMIT_ORDER(LOWER,UPPER,PERCENT,DEMAND,E_POSITION,E_SENIOR,DAYset,SHIFTset, DATES, CONTAIN) #生成多組限制式matrix
#print(LIMIT_MATRIX)
sequence = 0 #限制式順序
char = 'a' #CSR沒用度順序
fix = [] #存可行解的哪些部分是可以動的

#產生100個親代的迴圈
for p in range(parent):
    print(p)
    #擷取上個月的資料
    LMNIGHT_p = {}
    FRINIGHT_p = {}
    nightdaylimit_p = {}
    for i in EMPLOYEE:
        LMNIGHT_p[i] = LMNIGHT[i]
        FRINIGHT_p[i] = FRINIGHT[i]
        for w in range(nW):
            nightdaylimit_p[i, w] = nightdaylimit[i] #nightdaylimit_p: 員工i第w週可排的晚班次數
    
    #晚班資訊更新
    CAPACITY_NIGHT = {}
    for i in EMPLOYEE:
        for j in DAY:
            CAPACITY_NIGHT[i,j] = True
    
    for i in EMPLOYEE:
        if LMNIGHT_p[i] > 0:
            nightdaylimit_p[i, 0] = nightdaylimit_p[i, 0] - LMNIGHT_p[i]
            if nightdaylimit_p[i, 0] <= 0:
                for j in D_WEEK[0]:
                    CAPACITY_NIGHT[i, j] = False
        elif FRINIGHT_p[i] == 1:
            CAPACITY_NIGHT[i, j] = False

    #確定每個人已經上班的日子
    ALREADY = {}
    for i in EMPLOYEE:
        for j in DAY:
            ALREADY[i, j] = False
    
    #動態需工人數
    CURRENT_DEMAND = DEMAND
    
    #指定班別
    for c in ASSIGN:
        work[c[0],c[1],c[2]] = True
        ALREADY[c[0],c[1]] = True
        if c[2] != 0: #非指定休假
            for t in range(nT):
                if CONTAIN[c[2]][t] == 1:
                    CURRENT_DEMAND[c[1]][t] -= 1
        for n in range(nS_NIGHT): #指定晚班
            if c[2] == S_NIGHT[n]:
                CAPACITY_NIGHT[c[0], c[1]] = False
                CAPACITY_NIGHT[c[0], c[1]-1] = False
                CAPACITY_NIGHT[c[0], c[1]+1] = False
                w = WEEK_of_DAY[c[1]]
                nightdaylimit_p[c[0], w] -= 1
                if nightdaylimit_p[c[0], w] <= 0:
                    for d in D_WEEK[w]:
                        CAPACITY_NIGHT[c[0], d] = False
                break
    
    #特定技能CSR排優先班別
    for j in DAY:
        for skill in SKILL_NAME:
            for k in K_skill[skill]: 
                for i in E_SKILL[skill]:       
                    if ABLE(i, j, k) == True:
                        work[i, j, k] = True
                        ALREADY[i, j] = True
                        for n in range(nS_NIGHT):
                            if k == S_NIGHT[n]:
                                CAPACITY_NIGHT[i, j] = False
                                CAPACITY_NIGHT[i, j-1] = False
                                CAPACITY_NIGHT[i, j+1] = False
                                w = WEEK_of_DAY[j]
                                nightdaylimit_p[i, w] -= 1
                                if nightdaylimit_p[i, w] <= 0:
                                    for d in D_WEEK[w]:
                                        CAPACITY_NIGHT[i, d] = False
                                break
                        for t in range(nT):
                            if CONTAIN[k][t] == 1:            
                                CURRENT_DEMAND[j][t] -= 1
                    else: 
                        continue
    
    #瓶頸排班
    LIMIT_LIST = LIMIT_MATRIX[sequence] #一組限制式排序
    LIMIT = [] #一條限制式
    CSR_LIST = [] #可排的員工清單
    BOUND = [] #限制人數
    for l in range(len(LIMIT_LIST)):
        LIMIT = LIMIT_LIST[l]
        CSR_LIST = CSR_ORDER(char, LIMIT[0], LIMIT[1], EMPLOYEE_t) #員工沒用度排序
        for j in LIMIT[2]:
            BOUND = LIMIT[4]
            for i in CSR_LIST:
                if BOUND <= 0:
                    break
                for k in LIMIT[3]:  #抓出來會是list，是個班別集合
                    if BOUND <= 0:
                        break
                    elif ABLE(i, j, k) == True:
                        work[i, j, k] = True
                        ALREADY[i, j] = True
                        for n in range(nS_NIGHT):
                            if k == S_NIGHT[n]:
                                CAPACITY_NIGHT[i, j] = False
                                CAPACITY_NIGHT[i, j-1] = False
                                CAPACITY_NIGHT[i, j+1] = False
                                w = WEEK_of_DAY[j]
                                nightdaylimit_p[i, w] -= 1
                                if nightdaylimit_p[i, w] <= 0:
                                    for d in D_WEEK[w]:
                                        CAPACITY_NIGHT[i, d] = False
                                break
                        for t in range(nT):
                            if CONTAIN[k][t] == 1:            #報錯：k為list，不能當index  
                                CURRENT_DEMAND[j][t] -= 1
                        BOUND -= 1
                    else:
                        continue
    #sequence += 1
    if char == 'a':
        char = 'b'
    elif char == 'b':
        char = 'c'
    elif char == 'c':
        char = 'd'
    elif char == 'd':
        char = 'e'
    elif char == 'e':
        sequence += 1
        char = 'a'
    if sequence >= len(LIMIT_MATRIX):
        sequence = 0

    #=================================================================================================#
    #安排空班別
    #=================================================================================================#
    work, fix_temp = ARRANGEMENT(work, nEMPLOYEE, nDAY, nK)
    fix.append(fix_temp)



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
        for j in DAY:
            for k in S_NIGHT:
                if work[i, j, k] == True:
                    nightCount_temp[i] += 1
                    break
        if nightCount_temp[i] > nightCount:
            nightCount = nightCount_temp[i]
    
    for i in EMPLOYEE:
        for w in WEEK:
            for j in D_WEEK[w]:
                for r in BREAK:
                    for k in S_BREAK[r]:
                        if work[i, j, k] == True:
                            breakCount[i,w,r] = True
    
    
    for ii in E_SKILL:      #type(E_SKILL)=dict，要兩步驟取出裡面每項的list
        i_set = E_SKILL[ii]
        if len(i_set) <= 0: continue        #沒有人持有此技能時，略過
        k_set = K_skill_not[ii]
        if len(k_set) >= nK: continue   #技能沒有設定優先班別時，略過
        for i in i_set:
            for j in DAY:
                for k in k_set:
                    if work[i, j, k] == True:
                        complement += 1
    
    #=================================================================================================#
    # 輸出
    #=================================================================================================#
    #Dataframe_x
    K_type = ['O','A2','A3','A4','A5','MS','AS','P2','P3','P4','P5','N1','M1','W6','CD','C2','C3','C4','OB']


    employee_name = E_NAME
    which_worktime = []
    for i in EMPLOYEE:
        tmp = []
        for j in DAY:
            for k in SHIFT:
                if(work[i,j,k]==True):
                    tmp.append(K_type[k])
                    break
            else:
                print('CSR ',E_NAME[i],' 在',DATES[j],'號的排班發生錯誤。')
                print('請嘗試讓程式運行更多時間，或是減少限制條件。\n')
        which_worktime.append(tmp)
            

    df_x = pd.DataFrame(which_worktime, index = employee_name, columns = DATES)


    #Dataframe_y
    T_type = ['09:00','09:30','10:00','10:30','11:00','11:30','12:00','12:30','13:00','13:30','14:00','14:30'
            ,'15:00','15:30','16:00','16:30','17:00','17:30','18:00','18:30','19:00','19:30','20:00','20:30']

    lesspeople_count = []
    for j in DAY:
        tmp = []
        for t in TIME:
            tmp.append(int(lack[j,t]))
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
    #print("\n所有天每個時段人數與需求人數的差距中的最大值 = "+str(int(surplus))+"\n")



    #晚班次數dataframe
    night_work_total = []
    for i in EMPLOYEE:
        count = 0
        for j in DAY:
            for k in range(11,14):
                if(work[i,j,k]==True):
                    count+=1
        night_work_total.append(count)


    df_nightcount = pd.DataFrame(night_work_total, index = employee_name, columns = ['NW_count'])
    #print("\n員工中每人排晚班總次數的最大值 = "+str(int(nightCount))+"\n")



        
    #休息時間 Dataframe_z
    R_type = ['11:30','12:00','12:30','13:00','13:30']     
    which_week = [tmp+1 for tmp in WEEK] 
    which_resttime = []     
    for i in EMPLOYEE:
        tmp = []
        for w in WEEK:
            tmp2 = []
            for r in BREAK:
                if(breakCount[i,w,r]==True):
                    tmp2.append(R_type[r])
            tmp.append(tmp2)
        which_resttime.append(tmp)


    df_resttime = pd.DataFrame(which_resttime, index=employee_name, columns=which_week)


    #print("Final MIP gap value: %f" % m.MIPGap)
    #print("\n目標值 = "+str(m.objVal) + "\n")


    """#============================================================================#
    #輸出其他資訊
    #============================================================================#
    with pd.ExcelWriter(result) as writer:
        df_x.to_excel(writer, sheet_name="員工排班表")
        df_nightcount.to_excel(writer, sheet_name="員工本月晚班次數")
        df_percent_time.to_excel(writer, sheet_name="每個時段缺工百分比表")
        df_percent_day.to_excel(writer, sheet_name="每天缺工百分比表")
        df_nightcount.to_excel(writer, sheet_name="員工本月晚班次數")
        df_y.to_excel(writer, sheet_name="缺工人數表")
        df_resttime.to_excel(writer, sheet_name="員工每週有哪幾種休息時間")
    """

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
            new[date_name[i]] = df_x[i+1].values.tolist()
    #print('check point 2\n')
    new['id']=output_id
    new.set_index("id",inplace=True)
    #new.to_csv(result_x, encoding="utf-8_sig")
    #print(new)

    #============================================================================#
    #輸出冗員與缺工人數表
    #============================================================================#
    K_type_dict = {0:'',1:'O',2:'A2',3:'A3',4:'A4',5:'A5',6:'MS',7:'AS',8:'P2',9:'P3',10:'P4',11:'P5',12:'N1',13:'M1',14:'W6',15:'CD',16:'C2',17:'C3',18:'C4',19:'OB'}
    try:
        x_nb = np.vectorize({v: k for k, v in K_type_dict.items()}.get)(np.array(which_worktime))
    except:
        print('無法輸出缺工冗員表：排班班表不完整，請嘗試讓程式運行更多時間。')
        try:
            sys.exit(0)     #出錯的情況下，讓程式退出
        except:
            print('\n程式已結束。')


    people = np.zeros((nDAY,24))
    for i in range(0,nEMPLOYEE):
        for j in range(0,nDAY):
            for k in range(0,24):
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
            new_2[date_name[i]]=output_people[j]
            j = j + 1
    new_2['name']=T_type
    new_2.set_index("name",inplace=True)
    #new_2.to_csv(result_y, encoding="utf-8_sig")
    # print(new_2.T)
    
    #=================================================================================================#
    #確認解是否可行
    #=================================================================================================#
    confirm(df_x, ASSIGN, S_NIGHT, D_WEEK, nightdaylimit, LOWER, SHIFTset, E_POSITION, UPPER, DAYset, E_SENIOR)



    #====================================================================================================#
    #計算目標式
    #====================================================================================================#
    i_nb = np.vectorize({v: k for k, v in K_type_dict.items()}.get)(np.array(df_x))

    #計算人力情形
    people = np.zeros((nDAY,24))
    for i in range(0,nEMPLOYEE):
        for j in range(0,nDAY):
            for k in range(0,24):
                people[j][k] = people[j][k] + A_t.values[i_nb[i][j]-1][k]
    output_people = (people - DEMAND).tolist()
    lack_t = 0
    for i in output_people:
        for j in i:
            if j < 0:
                lack_t = -j + lack_t

    surplus_t = surplus

    nightcount_t = []
    for i in i_nb:
        count = 0
        for j in i:
            if j == 12 or j == 13 or j == 14:
                count = count + 1
        nightcount_t.append(count)
    nightcount_t = max(nightcount_t)

    date = datetime.datetime.strptime(str(year)+'-'+str(month)+'-'+str(1), "%Y-%m-%d")
    weekday = date.weekday()
    if weekday == 5 or weekday == 6:
        weekday = 0

    breakCount_t = np.ones((nEMPLOYEE,nW,5))
    for i in range(nEMPLOYEE):
        for j in range(nDAY):
            w_d = int((j+weekday)/5)
            if i_nb[i][j]!=1:
                for k in range(5):
                    if A_t.values[i_nb[i][j]-1][k+5]==1:
                        breakCount_t[i][w_d][k]=0
    breakCount_t = int(sum(sum(sum(breakCount_t))))

    df_a = EMPLOYEE_t.drop(['Name_English', 'Name_Chinese', 'ID', 'Senior', 'Position', 'NM','NW'],axis = 1).values
    df_c = np.zeros((nEMPLOYEE,nK))
    for i in range(nEMPLOYEE):
        if sum(df_a[i]) > 0:
            for j in range(nDAY):
                df_c[i][i_nb[i][j]-1]=df_c[i][i_nb[i][j]-1]+1

    complement_t = int(max(max(df_c.reshape(1,nEMPLOYEE*nK))))

    result = P0 * lack_t + P1 * surplus_t + P2 * nightcount_t + P3 * breakCount_t + P4 * complement_t


    #====================================================================================================#
    #將結果放入INITIAL_POOL中
    #====================================================================================================#
    INITIAL_POOL.append(Pool(result, df_x, df_y, df_percent_day, df_percent_time, df_nightcount, df_resttime, new, new_2))
    print(INITIAL_POOL[p].result)
    for i in range(nEMPLOYEE):
        for j in range(nDAY):
            for k in range(nK):
                work[i, j, k] = False
    
    for j in range(nDAY):
        for t in range(nT):
            lack[j, t] = 0
    
    surplus = 0
    nightCount = 0

    for i in range(nEMPLOYEE):
        for w in range(nW):
            for r in range(nR):
                breakCount[i, w, r] = False
    
    complement =  0

    lack_t = 0
    surplus_t = 0
    nightCount_t = []
    breakCount_t = 0
    complement_t =  0


    #====================================================================================================#
    #====================================================================================================#



    



#=======================================================================================================#
#====================================================================================================#
#=================================================================================================#
#  切分並交配
#=================================================================================================#
#====================================================================================================#
#=======================================================================================================#
GENE(avaliable_sol, fix, nDAY, nEMPLOYEE, gen)





#========================================================================#
# program end
#========================================================================#
print('\n\n*** Done ***')
