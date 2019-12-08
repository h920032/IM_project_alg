#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import data.fixed.tool as tl
import data.fixed.gene_alg as gen
# import datetime, calendar, sys

"""============================================================================#
input：
	LOWER 		- 日期j，班別集合ks，職位p，上班人數下限
	UPPER 		- 員工i，日子集合js，班別集合ks，排班次數上限
	PERCENT		- 日子集合，班別集合，要求占比，年資分界線
	DEMAND		- 日子j於時段t的需求人數
	E_POSITION 	- 擁有特定職稱的員工集合，POSI=1,…,nPOSI
	E_SENIOR 	- 達到特定年資的員工集合    
	DAYset 		- 通用日子集合 [all,Mon,Tue...]
	SHIFTset	- 通用的班別集合 [all,morning,noon,night...]

output：
[	'upper'/'lower'/'ratio',
	i_set,		#employee
	j_set,		#date
	k_set,		#work class
	n 			#umber
]	
============================================================================#"""



#=============================================================================#
#
 
def LIMIT_ORDER(L, U, S, Need, POSI, SENIOR, DAY, K):
	limits = []
	#upper limit: (all), j_set, k_set, n
	for i in U:
		print('in U:')
		print(i)
		limits.append([ 'upper', POSI['任意'], DAY[i[0]], K[i[1]], int(i[2]) ])

	#lower limit: j, k_set, i(position), n
	for i in L:
		limits.append([ 'lower', POSI[i[2]], [int(i[0])], K[i[1]], int(i[3]) ])

	#senior limit: j_set, k_set, n, i(senior) 
	for i in S:
		limits.append([ 'ratio', SENIOR[i[3]], DAY[i[0]], K[i[1]], float(i[2]) ])

	#change order

	#return
	print(limits)
	return limits