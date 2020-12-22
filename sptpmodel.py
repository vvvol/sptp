# coding=utf-8
import os
from timeit import default_timer as timer
# import argparse
import numpy as np


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
sum{j in J} x2a[i,j]*x[i,j] <= a[i] {i in I};
sum{i in I} x2b[i,j]*x[i,j] >= b[j] {j in J};
x[i,j] in Z (or in R)

"""
class SPTPmodel:

    def __init__(self, sptpData, isInteger=True, debug=False, options=None, model_options=None):
        """
        :param sptpData: structure containing all data
             .name (The Name of the dataset)
             .I (n-list with IDs of assets), .
             .J (m-list with IDs of requirements),
             .getC(i,j) = c_ij: i in I, j in J (costs),
             .getA(i)   = a_i: i in I (available units of assets)
             .getB(j)   = b_j: j in J (min amounts to satisfy requirements}
             .getX2A(i,j) = x2a_ij: i in I, j in J (coefficients to scale assets, =1 by default)
             .getX2B(i,j) = x2b_ij: i in I, j in J (coefficients to scale requirements, =1 by default)
             .isXinteger(i,j) returns True iff x_ij MUST BE Integer
             .getInitX(i,j) returns initial solution x_ij; =0 by default
        :param isInteger: if True then all x_ij are NonNegativeIntegers, else - NonNegativeReals
        :param debug: reserved
        :param options: reserved, e.g. to modify NL-generation
        :param model_options: reserved, to modify constraints
        """
        self.name = sptpData.name
        self.M = len(sptpData.I)
        self.N = len(sptpData.J)
        self.name = sptpData.name + '_sptp' + '_M_' + str(self.M) + '_N_' + str(self.N)

        self.model = ConcreteModel(self.name)

        # Declaration and settings of sets I, J and parameters A, B, C
        def initI(model):
            return (i for i in sptpData.I)
        self.model.I = Set(initialize=initI)

        def initJ(model):
            return (j for j in sptpData.J)
        self.model.J = Set(initialize=initJ)

        def initA(model, i):
            return sptpData.getA(i)
        self.model.A = Param(self.model.I, initialize=initA, within=NonNegativeReals)

        def initB(model, j):
            return sptpData.getB(j)
        self.model.B = Param(self.model.J, initialize=initB, within=NonNegativeReals)

        def initC(model, i, j):
            return sptpData.getC(i,j)
        self.model.C = Param(self.model.I, self.model.J, initialize=initC, within=NonNegativeReals)

        # Declaration of variables
        # Detect upper bound on x_ij
        upX = 10 # min( (sptpData.getA(i)/sum(sptpData.getX2A(i,j) for j in sptpData.J)) for i in sptpData.I )
        def initX(model, i, j):
            return int(sptpData.getInitX(i,j))
        def XijDomain_rule(model, i, j):
            if sptpData.isXinteger(i,j):
                return NonNegativeIntegers
            else:
                return NonNegativeReals
        self.model.x = Var(self.model.I, self.model.J, domain=XijDomain_rule, bounds=(0, upX), initialize=initX)

        # if isInteger:
        #     self.model.x = Var(self.model.I, self.model.J, domain=XijDomain_rule, bounds=(0, upX), initialize=initX)
        # else:
        #     self.model.x = Var(self.model.I, self.model.J, within=NonNegativeReals, bounds=(0, upX),
        #                        initialize=initX)

        # Constraints
        # sum{j in J} x2a[i,j]*x[i,j] <= a[i] {i in I};
        def cons_Assets_rule(model, i):
            return( sum(sptpData.getX2A(i,j)*model.x[i,j] for j in model.J) <= model.A[i])
        self.model.cons_Assets = Constraint(self.model.I, rule = cons_Assets_rule)

        # sum{i in I} x2b[i,j]*x[i,j] >= b[j] {j in J};
        def cons_Requirements_rule(model, j):
            return( sum(sptpData.getX2B(i,j)*model.x[i,j] for i in model.I) >= model.B[j])
        self.model.cons_Requirements = Constraint(self.model.J, rule = cons_Requirements_rule)

        ## Objective
        # minimize  sum{i in I, j in J} c[i,j] * x[i,j]
        def obj_rule(model):
            return (sum(model.C[i,j]*model.x[i,j] for i in model.I for j in model.J))
        self.model.obj = Objective(rule=obj_rule, sense=minimize)

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
    def makeDir(self, dirName):
        fullDirName = self.fullName + '/' + dirName
        if os.path.isdir(fullDirName): return fullDirName
        try:
            os.makedirs(fullDirName)
            return fullDirName
        except OSError:
            pass

    def makeDdFixedSets(self, Kdd, UPKdd=16):
        if Kdd > UPKdd:
            raise ValueError('Kdd(' + str(Kdd) + ') > up limit (' + str(UPKdd) + ')')

        print('Kdd = ', Kdd)
        s = '{:0' + str(Kdd) + 'b}'
        res = []
        for n in range(0, 2 ** Kdd):
            temp = s.format(n)  # get boolean representation of n
            temp = list(temp)  # boolean -> to list of boolean digits 0|1
            tempList = [int((int(c))) for c in temp]  # 0 -> -1; 1 -> 1
            res.append(tempList)
        return res

    def makePartDdNls(self, Kdd, FirstIJ, partSetOf01, printModel=False, do_symbolic_labels=False):
        print('makePartDdNls for ' + self.rowName)
        print(partSetOf01)
        # quit()
        for s01 in partSetOf01:
            ij_x_fixed = OrderedDict()
            for k in range(Kdd):
                ij_x_fixed[FirstIJ[k]] = s01[k]
            self.makeDdNl(ij_x_fixed, printModel=printModel, do_symbolic_labels=do_symbolic_labels)

    def makeAllDdNls(self, Kdd, printModel=False):
        # print '===================================='
        # print 'In makeAllDdNls: printModel=', printModel
        # print '===================================='
        setsOf01 = self.makeDdFixedSets(Kdd) # set (sequence) of binary values 0|1
        FirstIJ = self.getIJminD(Kdd)
        start_dd = timer()
        for s01 in setsOf01:
            ij_x_fixed = OrderedDict()
            for k in range(Kdd):
                ij_x_fixed[FirstIJ[k]] = s01[k]
            self.makeDdNl(ij_x_fixed, printModel=printModel, do_symbolic_labels=True)
        stop_dd = timer()
        print('makeAllDdNls(%s, Kdd = %i) took: %g s' % (self.name, Kdd, stop_dd - start_dd))

    # Make Domain decomposition by explicit fixing of variables
    def makeDdNlFix(self, ij_fixed_vals, printModel=False, do_symbolic_labels=True, nl_only=True):
        # print '===================================='
        # print 'In makeDdNl: printModel=', printModel
        # print '===================================='

        print('ij_fixed_vals: [', ij_fixed_vals, ']')
        K = len(ij_fixed_vals)
        # Keep nl-file name
        fileName_bak = self.fileName
        nlDdDir = self.makeDir('nl/dd' + str(K))
        logDdDir = self.makeDir('log/dd' + str(K))
        self.fileName = self.fileName + '_fxd' + str(K) + '_'
        for v in ij_fixed_vals.values():
            self.fileName = self.fileName + str(v)

        ij_fixed = ij_fixed_vals.keys()
        # Delete INDICES of fixed x_ij
        if self.model.find_component('fixedIJ') != None:
            self.model.del_component('fixedIJ')
        # Add UPDATED INDICES of fixed x_ij
        self.model.fixedIJ = Set(dimen=2, initialize=ij_fixed)

        # Delete CONSTRAINTS fixing x_ij
        if self.model.find_component('cons_fixed_xij') != None:
            self.model.del_component('cons_fixed_xij')
        # Add UPDATED CONSTRAINTS fixing x_ij
        def cons_fixed_ij_rule(m, i, j):
            return (m.x[i, j] == ij_fixed_vals[(i,j)])
        self.model.cons_fixed_xij = Constraint(self.model.fixedIJ, rule=cons_fixed_ij_rule)

        print('=========================')
        print ('file name:[' + nlDdDir + '/' + self.fileName + ']')
        print('=========================')
        if nl_only:
            nlFile = write_nl_only(self.model, nlDdDir + '/' + self.fileName,
                                             symbolic_solver_labels=do_symbolic_labels)
            print('nl: [', nlFile, ']')
        else:
            nlFile, smapFile = write_nl_smap(self.model, nlDdDir + '/' + self.fileName,
                                             symbolic_solver_labels=do_symbolic_labels)
            print('nl: [', nlFile, '], smap: [' + smapFile + ']')
            # self.model.pprint()
        if printModel:
            with open(logDdDir + '/' + self.fileName + '.model.log.txt', 'w') as f:
                self.model.pprint(ostream=f)
                f.close()
        # Restore NL-file name
        self.fileName = fileName_bak

    def makeDdNl(self, ij_fixed_vals, printModel=False, do_symbolic_labels=True, nl_only=True):
        # print '===================================='
        # print 'In makeDdNl: printModel=', printModel
        # print '===================================='

        print('ij_fixed_vals: [', ij_fixed_vals, ']')
        K = len(ij_fixed_vals)
        # Keep nl-file name
        fileName_bak = self.fileName
        nlDdDir = self.makeDir('nl/dd' + str(K))
        logDdDir = self.makeDir('log/dd' + str(K))
        self.fileName = self.fileName + '_d' + str(K) + '_'
        for v in ij_fixed_vals.values():
            self.fileName = self.fileName + str(v)

        ij_fixed = ij_fixed_vals.keys()
        # Delete INDICES of fixed x_ij
        if self.model.find_component('fixedIJ') != None:
            self.model.del_component('fixedIJ')
        # Add UPDATED INDICES of fixed x_ij
        self.model.fixedIJ = Set(dimen=2, initialize=ij_fixed)

        # Delete CONSTRAINTS fixing x_ij
        if self.model.find_component('cons_fixed_xij') != None:
            self.model.del_component('cons_fixed_xij')
        # Add UPDATED CONSTRAINTS fixing x_ij
        def cons_fixed_ij_rule(m, i, j):
            return (m.x[i, j] == ij_fixed_vals[(i,j)])
        self.model.cons_fixed_xij = Constraint(self.model.fixedIJ, rule=cons_fixed_ij_rule)

        print('=========================')
        print ('file name:[' + nlDdDir + '/' + self.fileName + ']')
        print('=========================')
        if nl_only:
            nlFile = write_nl_only(self.model, nlDdDir + '/' + self.fileName,
                                             symbolic_solver_labels=do_symbolic_labels)
            print('nl: [', nlFile, ']')
        else:
            nlFile, smapFile = write_nl_smap(self.model, nlDdDir + '/' + self.fileName,
                                             symbolic_solver_labels=do_symbolic_labels)
            print('nl: [', nlFile, '], smap: [' + smapFile + ']')
            # self.model.pprint()
        if printModel:
            with open(logDdDir + '/' + self.fileName + '.model.log.txt', 'w') as f:
                self.model.pprint(ostream=f)
                f.close()
        # Restore NL-file name
        self.fileName = fileName_bak

    def makeSmap(self):
        # theModel = TammesModel(problemName, args.npoints, chirality=args.chirality, suffix=args.suffix)
        # nlDir = self.makeDir('nl')
        # logDir = self.makeDir('log')
        # print('|||||||||||||||||||||||||')
        # print ('file name:[' + nlDir + '/' + self.fileName + ']')
        # print('|||||||||||||||||||||||||')

        smap = get_smap_var(self.model)

        return smap

    def readSol(self, smap=None):
        nlDir = self.makeDir('nl')
        if smap is None:
            results = read_sol_smap(self.model, nlDir  + '/' + self.fileName, nlDir  + '/' + self.fileName)  # theTamModel.fullName)
        else:
            results = read_sol_smap_var(self.model, nlDir + '/' + self.fileName, smap )
        self.model.solutions.load_from(results)
        sol = self.model
        # Print x[i,j]
        # Print #k 1  2  3  4
        sBuf = '    '
        for k in sol.N:
            sBuf = sBuf + ('%4d' % (k))
        print(sBuf)
        for i in sol.N:
            sBuf = '%4d' % (i)
            for j in (j for j in sol.N if (i > j)):
                sBuf = sBuf + ('%4d' % (int(round(sol.x[i,j].value))))
            sBuf = sBuf + ' 99 ' #for [i, i]
            for j in (j for j in sol.N if (j > i)):
                sBuf = sBuf + ('%4d' % (int(round(sol.x[j,i].value))))
            print(sBuf)

    def readSolDraw(self, sptpData, smap=None):
        nlDir = self.makeDir('nl')
        if smap is None:
            results = read_sol_smap(self.model, nlDir  + '/' + self.fileName, nlDir  + '/' + self.fileName)  # theTamModel.fullName)
        else:
            results = read_sol_smap_var(self.model, nlDir + '/' + self.fileName, smap )
        self.model.solutions.load_from(results)
        sol = self.model
        print("Opt length:", sol.obj())

        fig = plt.figure()
        ax = fig.gca()
        plt.suptitle('TSP ' + sptpData.NAME + ' opt. path length: ' + str(self.model.obj()), fontsize=20)

        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        textOffset = 1./50
        ax.scatter(sptpData.NODE_COORD[:,0], sptpData.NODE_COORD[:,1], s=30, marker='o', c='r')
        for i in range(self.Dimension):
            ax.text(sptpData.NODE_COORD[i,0] + textOffset, sptpData.NODE_COORD[i,1], str(i+1), fontsize=15)

        for (i,j) in self.model.E:
            if int(round(self.model.x[i,j]())) == 1:
                (xi,yi) = sptpData.NODE_COORD[i-1]
                (xj,yj) = sptpData.NODE_COORD[j-1]
                ax.plot([xi, xj], [yi, yj], color='grey', alpha=1)

        plt.axis('equal')
        plt.grid(b=True, which='major', color='#666666', linestyle='-')

        plt.show()

    def getIJminD(self, K): # return list of the first K pairs (i,j) ordered in C[i,j] ascending
        IJD = {}
        for (i, j) in self.model.E:
            IJD[(i, j)] = self.model.C[i, j]

        # print IJD
        SortedIJD = OrderedDict(sorted(IJD.items(), key=lambda ij_d: ij_d[1]))
        # print SortedIJD
        listSortedKeys = list(SortedIJD.keys())
        return [listSortedKeys[k] for k in range(K)]
