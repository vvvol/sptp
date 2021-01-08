from math import *
import pandas as pd


class SptpData_4:
    def __init__(self, name, path2a_csv="", path2b_csv="", path2C_csv="", path2D_csv="", path2P_csv="", path2S_csv="", debug=False):
        """
         :param name: name of the dataset;
         :path2a_csv: path to CSV with Available Assets (vector, i)
         :path2b_csv: path to CSV with Minimal Requirements (vector, j)
         :path2C_csv: path to CSV with Internal Costs of Lots (matrix, [ij])
         :path2D_csv: path to CSV with maximum cost of requirement j that can be satisfied with asset i (matrix, [ij])
         :path2P_csv: path to CSV with External costs of Lots (matrix, [ij])
         :path2S_csv: path to CSV with Lots' Sizes
         :xIntThreshold: SEE def isXinteger(self, i, j) !!!!
        """
        self.name = name

        self.aVec = pd.read_csv(path2a_csv, index_col=0)
        self.bVec = pd.read_csv(path2b_csv, index_col=0)
        self.cMat = pd.read_csv(path2C_csv, index_col=0)
        self.dMat = pd.read_csv(path2D_csv, index_col=0)
        self.pMat = pd.read_csv(path2P_csv, index_col=0)
        self.sMat = pd.read_csv(path2S_csv, index_col=0)
        # self.xIntThreshold =xIntThreshold

        self.I = self.aVec.index
        self.M = len(self.I)

        self.J = self.bVec.index
        self.N = len(self.J)


        # Check data integrity
        iBuf = len(self.cMat.index)
        if iBuf != self.M:
            raise ValueError('M of rows in C [%d] != length of Assets list [%d]' % (iBuf, self.M) )
        iBuf = len(self.cMat.columns.values.tolist())
        if iBuf != self.N:
            raise ValueError('N of columns in C [%d] != length of Requirements list [%d]' % (iBuf, self.N) )

        iBuf = len(self.dMat.index)
        if iBuf != self.M:
            raise ValueError('M of rows in D [%d] != length of Assets list [%d]' % (iBuf, self.M))
        iBuf = len(self.dMat.columns.values.tolist())
        if iBuf != self.N:
            raise ValueError('N of columns in D [%d] != length of Requirements list [%d]' % (iBuf, self.N))

        iBuf = len(self.pMat.index)
        if iBuf != self.M:
            raise ValueError('M of rows in P [%d] != length of Assets list [%d]' % (iBuf, self.M) )
        iBuf = len(self.pMat.columns.values.tolist())
        if iBuf != self.N:
            raise ValueError('N of columns in P [%d] != length of Requirements list [%d]' % (iBuf, self.N) )

        iBuf = len(self.sMat.index)
        if iBuf != self.M:
            raise ValueError('M of rows in S [%d] != length of Assets list [%d]' % (iBuf, self.M) )
        iBuf = len(self.sMat.columns.values.tolist())
        if iBuf != self.N:
            raise ValueError('N of columns in S [%d] != length of Requirements list [%d]' % (iBuf, self.N) )
        # ====================================

    def getC(self, i, j):
        return self.cMat.loc[i][j]

    def getA(self, i):
        return self.aVec.loc[i]['Units']

    def getB(self, j):
        return self.bVec.loc[j]['Amount']

    def getS(self, i, j):
        return self.sMat.loc[i][j]
    def getX2A(self, i, j):
        return self.getS(i, j) #self.sMat.loc[i][j]

    def getP(self, i, j):
        return self.pMat.loc[i][j]
    def getX2B(self, i, j):
        return self.getP(i, j) #self.pMat.loc[i][j]

    def getD(self, i, j):
        return self.dMat.loc[i][j]

    def getInitX(self, i, j):
        return 0.

    def checkFeasible(self, debug=False):
        checkDict = {}
        for j in self.J:
            if self.getB(j) > sum(self.getD(i,j) for i in self.I):
                checkDict[j] = False
                if debug:
                    print('checkFeasible: ', j, ' FALSE')
            else:
                checkDict[j] = True
        return checkDict

    # !!! All non-currency x_{ij} ARE INTEGER
    def isXinteger(self, i, j):
        if len(str(i)) > 3:
            return True
        else:
            return False