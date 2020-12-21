from math import *

class SptpData:
    def __init__(self, name, M, N):

        self.name = name

        self.M = M
        self.I = [i for i in range(1,M+1)]
        self.N = N
        self.J = [j for j in range(1,N+1)]

        self.A = [ int(2 + 20*abs(sin(2*i))) for i in self.I]
        self.B = [ int(1 + 2*abs(sin(2*j))) for j in self.J]

        self.C = [[] for i in self.I]
        for i in self.I:
            self.C[i-1] = [ (1 + 10*abs(sin(2*i)) + 10*abs(cos(3*j))) for j in self.J]

    def getC(self, i, j):
        return self.C[i-1][j-1]

    def getA(self, i):
        return self.A[i-1]

    def getB(self, j):
        return self.B[j-1]

    def getX2A(self, i, j):
        return 1.

    def getX2B(self, i, j):
        return 1.

    def getInitX(self, i, j):
        return 0.

    def mayBeFeasible(self):
        return ( sum(a for a in self.A) >= sum(b for b in self.B))