import pandas as pd

aVec = pd.read_csv('data/collateral_optimization_data_v2/a_vector_v2.csv', index_col=0)
bVec = pd.read_csv('data/collateral_optimization_data_v2/b_vector_v2.csv', index_col=0)
cMat = pd.read_csv('data/collateral_optimization_data_v2/c_matrix_v2.csv', index_col=0)
pMat = pd.read_csv('data/collateral_optimization_data_v2/p_matrix_v2.csv', index_col=0)

I = aVec.index
print(len(I), I)
J = bVec.index
print(len(J), J)

print('rows in C: ', len(cMat.index))
print('cols in C: ', len(cMat.columns.values.tolist()))

i = 'US Government Bonds 3'
print("A[%s] = %d"%(i, aVec.loc[i]['Units']))

quit()
sBuf = 0
for i in I:
    for j in J:
        c = cMat.loc[i][j]
        if c < 1.e-05:
            print('!!! [', i, ',', j, ']=', c)
        sBuf = sBuf + c

print('sum C = ', sBuf)
#
# print(type(aFr))
# print(aTab.index)
# print(aTab.info)
# # print(aTab.values)

# print(aTab)
# print(aTab.loc['EUR']['Units'])
# print(aTab.loc['US Government Bonds (TIPS) 60']['Units'])

