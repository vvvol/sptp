from __future__ import print_function
from future.utils import iteritems

def printKwds(arg, **kwds):
    print("arg=", arg)
    print("kwds =", kwds)
    if kwds is not None:
        for key, value in kwds.items():
            print("%s == %s" % (key, value))

kwds = {}

printKwds(2)

# printKwds(kwds)

printKwds(3, key1=False, key2=True, aaa="bb")