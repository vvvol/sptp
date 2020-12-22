from math import *
import pandas as pd


class SptpData:
    def __init__(self, name, path2a_csv, path2b_csv, path2C_csv, path2P_csv):
        """
         :param name: name of the dataset;
         :path2a_csv: path to CSV with Assets
         :path2b_csv: path to CSV with Requirements
         :path2C_csv: path to CSV with Costs
         :path2P_csv: path to CSV with P
        """
        self.name = name

        self.aVec = pd.read_csv(path2a_csv, index_col=0)
        self.bVec = pd.read_csv(path2b_csv, index_col=0)
        self.cMat = pd.read_csv(path2C_csv, index_col=0)
        self.pMat = pd.read_csv(path2P_csv, index_col=0)

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
        iBuf = len(self.pMat.index)
        if iBuf != self.M:
            raise ValueError('M of rows in P [%d] != length of Assets list [%d]' % (iBuf, self.M) )
        iBuf = len(self.pMat.columns.values.tolist())
        if iBuf != self.N:
            raise ValueError('N of columns in P [%d] != length of Requirements list [%d]' % (iBuf, self.N) )
        # ====================================

    def getC(self, i, j):
        return self.cMat.loc[i][j]

    def getA(self, i):
        return self.aVec.loc[i]['Units']

    def getB(self, j):
        return self.bVec.loc[j]['Amount']

    def getX2A(self, i, j):
        return 1.

    def getX2B(self, i, j):
        return self.pMat.loc[i][j]

    def getInitX(self, i, j):
        return 0.

    def mayBeFeasible(self):
        return (sum(self.getA(i) for i in self.I) >= sum(self.getB(j) for j in self.J))

    def isXinteger(self, i, j):
        if self.getA(i) <= 5000:
            return True
        else:
            return False