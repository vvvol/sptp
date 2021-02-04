# coding=utf-8
import os
from timeit import default_timer as timer
# import argparse
import numpy as np
import pandas as pd


# from pyomo.environ import *
import pyomo.environ as pyo

from pyomo.core.base.PyomoModel import *
from pyomo.core.base.param import *
from pyomo.core.base.var import *
from pyomo.core.base.sets import *
from pyomo.core.base.rangeset import *
from pyomo.core.base.objective import *
from pyomo.core.base.constraint import *
from pyomo.core.base.set_types import *

from pyomo.opt import *
from write import *

from read import read_sol_smap
from read import read_sol_smap_var

import matplotlib.pyplot as plt

from collections import OrderedDict
import threading # !!! Simplest way

""" 
"Special"  Transportation Problem
Pyomo model of the following problem
sum{i in I, j in J} c[i,j] * x[i,j]  ==> min by x[i,j], s.t.
sum{j in J} s[i,j]*x[i,j]        <= a[i] {i in I};
sum{i in I} p[i,j]*x[i,j]        >= b[j] {j in J};
sum{i in I} t[i,k]*x[i,j]*p[i,j] <= d[k,j] {k in K, j in J}
x[i,j] in Z (FOR i not in CASH) 

"""
class SPTPmodel_6_1:

    def __init__(self, sptpData, isInteger=True, debug=False, options=None, model_options=None):
        """
        :param sptpData: structure containing all data
             .name (The Name of the dataset)
             .I (n-list with IDs of assets), .
             .J (m-list with IDs of requirements),
             .K (KK-list of asset types)
             .getC(i,j) = c_ij: i in I, j in J (Internal Costs of Lots (matrix, [ij])),
             .getA(i)   = a_i: i in I (available units of assets)
             .getB(j)   = b_j: j in J (min amounts to satisfy requirements}
             .getS(i,j) = s_ij: i in I, j in J (Lots' Sizes)
             .getP(i,j) = p_ij: i in I, j in J (External costs of Lots)
             .getD(k,j) = d_kj maximum cost of requirement j that can be satisfied with assets of type k (matrix, [kj])
             .getT(i,k) = t_ik indicator of whether asset i has type k(0 or 1). There is exactly one 1 in each row (matrix, [ik])
             .isXinteger(i,j) returns True iff x_ij MUST BE Integer
             .getInitX(i,j) returns initial solution x_ij; =0 by default
        :param isInteger: if True then some x_ij will be NonNegativeIntegers (!!!???), else - NonNegativeReals
        :param debug: reserved
        :param options: reserved, e.g. to modify NL-generation
        :param model_options: reserved, to modify constraints
        """
        self.name = sptpData.name
        self.M = len(sptpData.I)
        self.N = len(sptpData.J)
        self.NK = sptpData.NK
        self.name = sptpData.name + '_M_' + str(self.M) + '_N_' + str(self.N) + '_K_' + str(self.NK) + "_v5"

        self.model = ConcreteModel(self.name)

        # Declaration and settings of sets I, J, K and parameters A, B, C, D, P, T
        def initI(model):
            return (i for i in sptpData.I)
        self.model.I = Set(initialize=initI)

        def initJ(model):
            return (j for j in sptpData.J)
        self.model.J = Set(initialize=initJ)

        def initK(model):
            return (k for k in sptpData.K)
        self.model.K = Set(initialize=initK)

        def initA(model, i):
            return sptpData.getA(i)
        self.model.A = Param(self.model.I, initialize=initA, within=NonNegativeReals)

        def initB(model, j):
            return sptpData.getB(j)
        self.model.B = Param(self.model.J, initialize=initB, within=NonNegativeReals)

        def initC(model, i, j):
            return sptpData.getC(i,j)
        self.model.C = Param(self.model.I, self.model.J, initialize=initC, within=NonNegativeReals)

        def initS(model, i, j):
            return sptpData.getS(i,j)
        self.model.S = Param(self.model.I, self.model.J, initialize=initS, within=NonNegativeReals)

        def initP(model, i, j):
            return sptpData.getP(i,j)
        self.model.P = Param(self.model.I, self.model.J, initialize=initP, within=NonNegativeReals)

        def initD(model, k, j):
            return sptpData.getD(k,j)
        self.model.D = Param(self.model.K, self.model.J, initialize=initD, within=NonNegativeReals)

        def initT(model, i, k):
            return sptpData.getT(i, k)
        self.model.T = Param(self.model.I, self.model.K, initialize=initT, within=Binary)
        
        def initmask(model, i, j):
            return sptpData.getmask(i, j)
        self.model.mask = Param(self.model.I, self.model.J, initialize=initmask, within=Binary)
        

        # Declaration of variables
        # Detect upper bound on x_ij
        # Is x_ij integer or not is defined by SptpData.isXinteger() function (ALL i except CASH !!!)
        def initX(model, i, j):
            return sptpData.getInitX(i, j)

        def XijDomain_rule(model, i, j):
            if sptpData.isXinteger(i,j) and isInteger:
                return NonNegativeIntegers
            else:
                return NonNegativeReals

        def XijBounds_rule(model, i, j):
            uBound = model.A[i]/model.S[i,j]
            if model.P[i,j] >= 1.e-6:
                for k in (k for k in model.K if model.T[i,k] > 0): # in (e for e in arr if e >= 0)
                    uBound = min(uBound, model.D[k, j]/model.P[i, j])
            return (0, uBound)

        self.model.x = Var(self.model.I, self.model.J, domain=XijDomain_rule, bounds=XijBounds_rule, initialize=initX)
        for i in self.model.I:
            for j in self.model.J:
                if self.model.mask[i, j] == 1:
                    self.model.x[i, j].fix(0)
        # Constraints
        # sum{j in J} s[i,j]*x[i,j] <= a[i] {i in I};
        def cons_Assets_rule(model, i):
            return( sum(model.S[i,j]*model.x[i,j] for j in model.J) <= model.A[i])
        self.model.cons_Assets = Constraint(self.model.I, rule = cons_Assets_rule)

        # sum{i in I} p[i,j]*x[i,j] <= b[j] {j in J};
        def cons_Requirements_rule(model, j):
            return( sum(model.P[i,j]*model.x[i,j] for i in model.I) <= model.B[j])
        self.model.cons_Requirements = Constraint(self.model.J, rule = cons_Requirements_rule)

        # sum{i in I} t[i,k]*x[i,j]*p[i,j] <= d[k,j] {k in K, j in J}
        # !!! Skip for if p[i,j] = ZERO !!!
        def cons_MaxCostReq_rule(model, k, j):
            # tmp = sum(model.T[i,k]*model.P[i,j] for i in model.I)
            if sum(model.T[i,k]*model.P[i,j] for i in model.I) <= 1.e-7:
                return Constraint.Skip
            return (sum(model.T[i,k]*model.x[i,j]*model.P[i,j] for i in model.I) <= model.D[k, j])
        self.model.cons_MaxCostReq = Constraint(self.model.K, self.model.J, rule = cons_MaxCostReq_rule)

        ## Objective
        # minimize  sum{i in I, j in J} c[i,j] * x[i,j]
        def obj_rule(model):
            return (sum(model.C[i,j]*model.x[i,j] for i in model.I for j in model.J))
        self.model.obj = Objective(rule=obj_rule, sense=maximize)

        if debug:
            self.model.pprint()

        # Fixed constraints
        # def cons_fixed_xij(model, ij, b):
        #     return (model.x[ij[0], ij[1]] == b)
        # if ij_to_be_fixed <> None and xij_fixed_values <> None:
        #     if len(ij_to_be_fixed) <> len(xij_fixed_values):
        #         raise ValueError('Fixed mismatch: len(xj)=' + str(len(ij_to_be_fixed)) + ' <> len(fix_values)=' + str(len(xij_fixed_values)) )
        #     self.model.fixedIJ = Set(dimen=2, initialize=ij_to_be_fixed)
        #     self.model.cons_fixed_xij = Constraint(self.model.fixedIJ)

    # ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
    # |||||||||||||||||||||||||| DO NOT USE BELOW FUNCTIONS ||||||||||||||||||||||||||||||||||||||||||
    # def makeDir(self, dirName):
    #     fullDirName = self.fullName + '/' + dirName
    #     if os.path.isdir(fullDirName): return fullDirName
    #     try:
    #         os.makedirs(fullDirName)
    #         return fullDirName
    #     except OSError:
    #         pass
    #
    # def makeDdFixedSets(self, Kdd, UPKdd=16):
    #     if Kdd > UPKdd:
    #         raise ValueError('Kdd(' + str(Kdd) + ') > up limit (' + str(UPKdd) + ')')
    #
    #     print('Kdd = ', Kdd)
    #     s = '{:0' + str(Kdd) + 'b}'
    #     res = []
    #     for n in range(0, 2 ** Kdd):
    #         temp = s.format(n)  # get boolean representation of n
    #         temp = list(temp)  # boolean -> to list of boolean digits 0|1
    #         tempList = [int((int(c))) for c in temp]  # 0 -> -1; 1 -> 1
    #         res.append(tempList)
    #     return res
    #
    # def makePartDdNls(self, Kdd, FirstIJ, partSetOf01, printModel=False, do_symbolic_labels=False):
    #     print('makePartDdNls for ' + self.rowName)
    #     print(partSetOf01)
    #     # quit()
    #     for s01 in partSetOf01:
    #         ij_x_fixed = OrderedDict()
    #         for k in range(Kdd):
    #             ij_x_fixed[FirstIJ[k]] = s01[k]
    #         self.makeDdNl(ij_x_fixed, printModel=printModel, do_symbolic_labels=do_symbolic_labels)
    #
    # def makeAllDdNls(self, Kdd, printModel=False):
    #     # print '===================================='
    #     # print 'In makeAllDdNls: printModel=', printModel
    #     # print '===================================='
    #     setsOf01 = self.makeDdFixedSets(Kdd) # set (sequence) of binary values 0|1
    #     FirstIJ = self.getIJminD(Kdd)
    #     start_dd = timer()
    #     for s01 in setsOf01:
    #         ij_x_fixed = OrderedDict()
    #         for k in range(Kdd):
    #             ij_x_fixed[FirstIJ[k]] = s01[k]
    #         self.makeDdNl(ij_x_fixed, printModel=printModel, do_symbolic_labels=True)
    #     stop_dd = timer()
    #     print('makeAllDdNls(%s, Kdd = %i) took: %g s' % (self.name, Kdd, stop_dd - start_dd))
    #
    # # Make Domain decomposition by explicit fixing of variables
    # def makeDdNlFix(self, ij_fixed_vals, printModel=False, do_symbolic_labels=True, nl_only=True):
    #     # print '===================================='
    #     # print 'In makeDdNl: printModel=', printModel
    #     # print '===================================='
    #
    #     print('ij_fixed_vals: [', ij_fixed_vals, ']')
    #     K = len(ij_fixed_vals)
    #     # Keep nl-file name
    #     fileName_bak = self.fileName
    #     nlDdDir = self.makeDir('nl/dd' + str(K))
    #     logDdDir = self.makeDir('log/dd' + str(K))
    #     self.fileName = self.fileName + '_fxd' + str(K) + '_'
    #     for v in ij_fixed_vals.values():
    #         self.fileName = self.fileName + str(v)
    #
    #     ij_fixed = ij_fixed_vals.keys()
    #     # Delete INDICES of fixed x_ij
    #     if self.model.find_component('fixedIJ') != None:
    #         self.model.del_component('fixedIJ')
    #     # Add UPDATED INDICES of fixed x_ij
    #     self.model.fixedIJ = Set(dimen=2, initialize=ij_fixed)
    #
    #     # Delete CONSTRAINTS fixing x_ij
    #     if self.model.find_component('cons_fixed_xij') != None:
    #         self.model.del_component('cons_fixed_xij')
    #     # Add UPDATED CONSTRAINTS fixing x_ij
    #     def cons_fixed_ij_rule(m, i, j):
    #         return (m.x[i, j] == ij_fixed_vals[(i,j)])
    #     self.model.cons_fixed_xij = Constraint(self.model.fixedIJ, rule=cons_fixed_ij_rule)
    #
    #     print('=========================')
    #     print ('file name:[' + nlDdDir + '/' + self.fileName + ']')
    #     print('=========================')
    #     if nl_only:
    #         nlFile = write_nl_only(self.model, nlDdDir + '/' + self.fileName,
    #                                          symbolic_solver_labels=do_symbolic_labels)
    #         print('nl: [', nlFile, ']')
    #     else:
    #         nlFile, smapFile = write_nl_smap(self.model, nlDdDir + '/' + self.fileName,
    #                                          symbolic_solver_labels=do_symbolic_labels)
    #         print('nl: [', nlFile, '], smap: [' + smapFile + ']')
    #         # self.model.pprint()
    #     if printModel:
    #         with open(logDdDir + '/' + self.fileName + '.model.log.txt', 'w') as f:
    #             self.model.pprint(ostream=f)
    #             f.close()
    #     # Restore NL-file name
    #     self.fileName = fileName_bak
    #
    # def makeDdNl(self, ij_fixed_vals, printModel=False, do_symbolic_labels=True, nl_only=True):
    #     # print '===================================='
    #     # print 'In makeDdNl: printModel=', printModel
    #     # print '===================================='
    #
    #     print('ij_fixed_vals: [', ij_fixed_vals, ']')
    #     K = len(ij_fixed_vals)
    #     # Keep nl-file name
    #     fileName_bak = self.fileName
    #     nlDdDir = self.makeDir('nl/dd' + str(K))
    #     logDdDir = self.makeDir('log/dd' + str(K))
    #     self.fileName = self.fileName + '_d' + str(K) + '_'
    #     for v in ij_fixed_vals.values():
    #         self.fileName = self.fileName + str(v)
    #
    #     ij_fixed = ij_fixed_vals.keys()
    #     # Delete INDICES of fixed x_ij
    #     if self.model.find_component('fixedIJ') != None:
    #         self.model.del_component('fixedIJ')
    #     # Add UPDATED INDICES of fixed x_ij
    #     self.model.fixedIJ = Set(dimen=2, initialize=ij_fixed)
    #
    #     # Delete CONSTRAINTS fixing x_ij
    #     if self.model.find_component('cons_fixed_xij') != None:
    #         self.model.del_component('cons_fixed_xij')
    #     # Add UPDATED CONSTRAINTS fixing x_ij
    #     def cons_fixed_ij_rule(m, i, j):
    #         return (m.x[i, j] == ij_fixed_vals[(i,j)])
    #     self.model.cons_fixed_xij = Constraint(self.model.fixedIJ, rule=cons_fixed_ij_rule)
    #
    #     print('=========================')
    #     print ('file name:[' + nlDdDir + '/' + self.fileName + ']')
    #     print('=========================')
    #     if nl_only:
    #         nlFile = write_nl_only(self.model, nlDdDir + '/' + self.fileName,
    #                                          symbolic_solver_labels=do_symbolic_labels)
    #         print('nl: [', nlFile, ']')
    #     else:
    #         nlFile, smapFile = write_nl_smap(self.model, nlDdDir + '/' + self.fileName,
    #                                          symbolic_solver_labels=do_symbolic_labels)
    #         print('nl: [', nlFile, '], smap: [' + smapFile + ']')
    #         # self.model.pprint()
    #     if printModel:
    #         with open(logDdDir + '/' + self.fileName + '.model.log.txt', 'w') as f:
    #             self.model.pprint(ostream=f)
    #             f.close()
    #     # Restore NL-file name
    #     self.fileName = fileName_bak
    #
    # def makeSmap(self):
    #     # theModel = TammesModel(problemName, args.npoints, chirality=args.chirality, suffix=args.suffix)
    #     # nlDir = self.makeDir('nl')
    #     # logDir = self.makeDir('log')
    #     # print('|||||||||||||||||||||||||')
    #     # print ('file name:[' + nlDir + '/' + self.fileName + ']')
    #     # print('|||||||||||||||||||||||||')
    #
    #     smap = get_smap_var(self.model)
    #
    #     return smap
    #
    # def readSol(self, smap=None):
    #     nlDir = self.makeDir('nl')
    #     if smap is None:
    #         results = read_sol_smap(self.model, nlDir  + '/' + self.fileName, nlDir  + '/' + self.fileName)  # theTamModel.fullName)
    #     else:
    #         results = read_sol_smap_var(self.model, nlDir + '/' + self.fileName, smap )
    #     self.model.solutions.load_from(results)
    #     sol = self.model
    #     # Print x[i,j]
    #     # Print #k 1  2  3  4
    #     sBuf = '    '
    #     for k in sol.N:
    #         sBuf = sBuf + ('%4d' % (k))
    #     print(sBuf)
    #     for i in sol.N:
    #         sBuf = '%4d' % (i)
    #         for j in (j for j in sol.N if (i > j)):
    #             sBuf = sBuf + ('%4d' % (int(round(sol.x[i,j].value))))
    #         sBuf = sBuf + ' 99 ' #for [i, i]
    #         for j in (j for j in sol.N if (j > i)):
    #             sBuf = sBuf + ('%4d' % (int(round(sol.x[j,i].value))))
    #         print(sBuf)
    #
    # def readSolDraw(self, sptpData, smap=None):
    #     nlDir = self.makeDir('nl')
    #     if smap is None:
    #         results = read_sol_smap(self.model, nlDir  + '/' + self.fileName, nlDir  + '/' + self.fileName)  # theTamModel.fullName)
    #     else:
    #         results = read_sol_smap_var(self.model, nlDir + '/' + self.fileName, smap )
    #     self.model.solutions.load_from(results)
    #     sol = self.model
    #     print("Opt length:", sol.obj())
    #
    #     fig = plt.figure()
    #     ax = fig.gca()
    #     plt.suptitle('TSP ' + sptpData.NAME + ' opt. path length: ' + str(self.model.obj()), fontsize=20)
    #
    #     ax.set_xlabel('X')
    #     ax.set_ylabel('Y')
    #     textOffset = 1./50
    #     ax.scatter(sptpData.NODE_COORD[:,0], sptpData.NODE_COORD[:,1], s=30, marker='o', c='r')
    #     for i in range(self.Dimension):
    #         ax.text(sptpData.NODE_COORD[i,0] + textOffset, sptpData.NODE_COORD[i,1], str(i+1), fontsize=15)
    #
    #     for (i,j) in self.model.E:
    #         if int(round(self.model.x[i,j]())) == 1:
    #             (xi,yi) = sptpData.NODE_COORD[i-1]
    #             (xj,yj) = sptpData.NODE_COORD[j-1]
    #             ax.plot([xi, xj], [yi, yj], color='grey', alpha=1)
    #
    #     plt.axis('equal')
    #     plt.grid(b=True, which='major', color='#666666', linestyle='-')
    #
    #     plt.show()
    #
    # def getIJminD(self, K): # return list of the first K pairs (i,j) ordered in C[i,j] ascending
    #     IJD = {}
    #     for (i, j) in self.model.E:
    #         IJD[(i, j)] = self.model.C[i, j]
    #
    #     # print IJD
    #     SortedIJD = OrderedDict(sorted(IJD.items(), key=lambda ij_d: ij_d[1]))
    #     # print SortedIJD
    #     listSortedKeys = list(SortedIJD.keys())
    #     return [listSortedKeys[k] for k in range(K)]
