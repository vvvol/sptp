from __future__ import print_function
from future.utils import iteritems

import os
import sys
import argparse

from write import write_nl_only
from write import get_smap_var
from read import read_sol_smap_var

# import ssop_config
from ssop_session import *

import ssop_config
from sptpmodel import *
from SptpDataDemo import *

def makeParser():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-pr', '--problem', default="testSPTP", help='problem name')
    parser.add_argument('-a', '--action', type=str, default='nl', choices=['nl', 'sol'],
                        help='Make NL or import SOL')
    # parser.add_argument('-int', '--integer', action='store_true', help='variables are integer')
    parser.add_argument('-inthld', '--integerthreshold', type=int, default=0,
                        help='Is X_ij Integer by its upper bound threshold, the more the value the more integers')
    parser.add_argument('-wd', '--workdir', default=ssop_config.SSOP_DEFAULT_WORKING_DIR, help='working directory')
    parser.add_argument('-s', '--solver', default='scip', choices=['ipopt', 'scip'], help='solver to use')
    parser.add_argument('-cf', '--cleanfiles', action='store_true', help='clean working directory')
    parser.add_argument('-cj', '--cleanjobs', action='store_true', help='clean jobs from server')
    parser.add_argument('-x', '--extra', action='store_true', help='extra tests')
    return parser

def makeIpoptOptionsFile(workdir, optFileName):
    # see https://coin-or.github.io/Ipopt/OPTIONS.html
    with open(workdir + "/" + optFileName, 'w') as f:
        f.write("linear_solver ma57\n")
        f.write("max_iter 10000\n")
        f.write("constr_viol_tol 0.0001\n")
        f.write("warm_start_init_point yes\n")
        f.write("warm_start_bound_push 1e-06\n")
        f.write("print_level 4\n")
        f.write("print_user_options yes\n")
        f.close()
    return

def makeScipOptionsFile(workdir, optFileName):
    # https://scip.zib.de/doc-6.0.2/html/PARAMETERS.php
    with open(workdir + "/" + optFileName, 'w') as f:
        f.write('display/freq = 100\n')
        f.write('display/verblevel = 4\n')
        f.write('limits/gap = 1e-06\n')
        f.write('limits/memory = 28000\n')
        f.close()
    return

def makeNlFile(theModel, workdir, **params):
    # theModel = SPTPmodel(SptpData(M, N), isInteger=True)
    nlName = write_nl_only(theModel.model, workdir + '/' + theModel.name,  symbolic_solver_labels=True)
    return nlName

def checkResults(theModel, workdir):
    smap = get_smap_var(theModel.model)
    results = read_sol_smap_var(theModel.model, workdir + "/" + theModel.name, smap)
    theModel.model.solutions.load_from(results)
    # solution have been loaded to the model
    print("Solution of ", theModel.name)

    with open(workdir + "/" + theModel.name + '.sol.txt', 'w') as f:
        sBuf = ('Optimal cost: %.3f' % (theModel.model.obj()))
        print(sBuf)
        f.write(sBuf + '\n')

        sBuf = 'i, j, x_ij (>1.e-6)'
        print(sBuf)
        f.write(sBuf + '\n')

        for i in theModel.model.I:
            for j in theModel.model.J:
                if theModel.model.x[i,j]() > 1.e-6:
                    sBuf = ("%s, %s, %.2f" % (str(i), str(j), theModel.model.x[i,j]()))
                    print(sBuf)
                    f.write(sBuf+'\n')
        f.close()

    return

if __name__ == "__main__":
    parser = makeParser()
    args = parser.parse_args()
    # vargs = vars(args)
    print('Arguments of the test')
    print('======================')
    for arg in vars(args):
        print(arg + ":", getattr(args, arg))
    print('======================')

    workdir = args.workdir
    solver = args.solver

    # Create opt/ model and write NL-file
    # Get SptpData somehow
    if args.action == "nl":
        print('Reading data and feasibility checking started...')
    if args.action == 'sol':
        print('Reading data...')
    start_read_check = timer()

    theData = SptpData(args.problem + '_iThld' + str(args.integerthreshold), \
                       'data/collateral_optimization_data_v3/a_vector.csv', \
                       'data/collateral_optimization_data_v3/b_vector.csv', \
                       'data/collateral_optimization_data_v3/c_matrix.csv', \
                       'data/collateral_optimization_data_v3/p_matrix.csv', xIntThreshold=args.integerthreshold)
    # Check necessary condition for feasibility
    if args.action == 'nl':
        checkDict = theData.checkFeasible(debug=True)
        for j in checkDict.keys():
            if not checkDict[j]:
                raise ValueError("Feasibility check failed for j = %s" % (str(j)))

    if args.action == "nl":
        print('Reading and feasibility checking took: %g sec' % (timer() - start_read_check))
    if args.action == 'sol':
        print('Reading took: %g sec' % (timer() - start_read_check))


    print('Model creating ...')
    start_model = timer()
    theModel = SPTPmodel(theData, isInteger=True, debug=False)
    # with open(workdir + '/' + theModel.name + '.mod.txt', 'w') as f:
    #     theModel.model.pprint(ostream=f)
    #     f.close()
    print('Model creating took: %g sec' % (timer() - start_model))

    # Write NL-files
    if args.action == 'nl':
        print('Writing NL-file')
        start_makeNl = timer()
        nlName = makeNlFile(theModel, workdir)
        nlNames = [nlName]
        stop_makeNl = timer()
        print('makeNl(%s, intThld = %d) took: %g sec' % (theModel.name, args.integerthreshold, stop_makeNl - start_makeNl))

        # Write options file
        if solver == "scip":
            optFile = 'scipdemo.set'
            # makeScipOptionsFile(workdir, optFile)
            makeSolverOptionsFile(workdir + "/" + optFile, solver="scip", \
                                  dictOptVal={"display/freq": 100, "display/verblevel": 5, \
                                              "limits/gap": 1e-06, "limits/memory": 28000}
                                  )
        if solver == "ipopt":
            optFile = 'ipopt.opt'
            # makeIpoptOptionsFile(workdir, optFile)
            makeSolverOptionsFile(workdir + "/" + optFile, solver="ipopt", \
                                  linear_solver="ma57", max_iter=10000, \
                                  constr_viol_tol=0.0001,
                                  warm_start_init_point="yes", warm_start_bound_push=1e-06, \
                                  print_level=4, print_user_options="yes")
        quit()

    # Write SOL-files
    if args.action == 'sol':
        print('Checking SOL-file')
        checkResults(theModel, workdir)
        quit()

    quit()


    # resources_list = [ssop_config.SSOP_RESOURCES["test-pool-scip-ipopt"]] #['']] #["vvvolhome2"]] # ["ui4.kiae.vvvol"]] 'hse'
    # theSession = SsopSession(name=args.problem, resources=resources_list, \
    #                          workdir=workdir, debug=False)
    # # theSession = SsopSession(name=args.problem, resources=[ssop_config.SSOP_RESOURCES["ui4.kiae.vvvol"]], \
    # #                          workdir=workdir, debug=False)
    #
    # # Variables declarations for Python 3.*
    # optFile = ""
    # solved = []
    # unsolved = []
    # jobId = ""
    #
    #
    # # Solve all problems by SSOP
    # if solver == "ipopt":
    #     solved, unsolved, jobId = theSession.runJob(nlNames, optFile) # by default solver = "ipopt"
    # if solver == "scip":
    #     solved, unsolved, jobId = theSession.runJob(nlNames, optFile, solver="scip")
    #
    # print("solved:   ", solved)
    # print("unsolved: ", unsolved)
    # print("Job %s is finished" % (jobId))
    #
    # # Check results
    # checkResults(theModel, workdir)
    #
    #
    # # Clean working directory to free disk space at local host, MAY BE
    # if args.cleanfiles:
    #     theSession.deleteWorkFiles([".nl", ".row", ".col", ".sol", ".zip", ".plan"])
    #
    # # Delete jobs created to save disk space at Everest server , MAY BE
    # if args.cleanjobs:
    #     theSession.deleteAllJobs()
    #
    # # CLOSE THE SESSION !!! MUST BE
    # theSession.session.close()
    #
    # print("Done")







