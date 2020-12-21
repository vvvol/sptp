import pyomo.environ
from pyomo.core import SymbolMap
from pyomo.opt import (ReaderFactory,
                       ResultsFormat)
# use fast version of pickle (python 2 or 3)
from six.moves import cPickle as pickle

SOL_EXT = '.sol'


def read_sol(model, sol_filename, symbol_map_filename, suffixes=[".*"]):
    """
    Reads the solution from the SOL file and generates a
    results object with an appropriate symbol map for
    loading it into the given Pyomo model. By default all
    suffixes found in the NL file will be extracted. This
    can be overridden using the suffixes keyword, which
    should be a list of suffix names or regular expressions
    (or None).
    """
    if suffixes is None:
        suffixes = []

    # parse the SOL file
    with ReaderFactory(ResultsFormat.sol) as reader:
        results = reader(sol_filename, suffixes=suffixes)

    # regenerate the symbol_map for this model
    with open(symbol_map_filename, "rb") as f:
        symbol_cuid_pairs = pickle.load(f)
    symbol_map = SymbolMap()
    symbol_map.addSymbols((cuid.find_component(model), symbol)
                          for symbol, cuid in symbol_cuid_pairs)

    # tag the results object with the symbol_map
    results._smap = symbol_map

    return results

def read_sol_smap(model, sol_filename, symbol_filename, suffixes=[".*"]):
    """
    Reads the solution from the SOL file and generates a
    results object with an appropriate symbol map for
    loading it into the given Pyomo model. By default all
    suffixes found in the NL file will be extracted. This
    can be overridden using the suffixes keyword, which
    should be a list of suffix names or regular expressions
    (or None).
    """
    if suffixes is None:
        suffixes = []

    # Remove possible suffix '.sol' if any, treating sol_filename as dir_sol/modelName, dir_sol/dataName
    if sol_filename.endswith(SOL_EXT): sol_filename = sol_filename[:-len(SOL_EXT)]
    symbol_map_filename = symbol_filename + ".symbol_map.pickle"
    sol_filename = sol_filename + ".sol"

    # parse the SOL file
    with ReaderFactory(ResultsFormat.sol) as reader:
        results = reader(sol_filename, suffixes=suffixes)

    # regenerate the symbol_map for this model
    with open(symbol_map_filename, "rb") as f:
        symbol_cuid_pairs = pickle.load(f)
    symbol_map = SymbolMap()
    symbol_map.addSymbols((cuid.find_component(model), symbol)
                          for symbol, cuid in symbol_cuid_pairs)

    # tag the results object with the symbol_map
    results._smap = symbol_map

    return results

def read_sol_smap_var(model, sol_filename, smap, suffixes=[".*"]):
    """
    Reads the solution from the SOL file and generates a
    results object with an appropriate symbol map (smap passed as variable!) for
    loading it into the given Pyomo model. By default all
    suffixes found in the NL file will be extracted. This
    can be overridden using the suffixes keyword, which
    should be a list of suffix names or regular expressions
    (or None).
    """
    if suffixes is None:
        suffixes = []

    # Remove possible suffix '.sol' if any, treating sol_filename as dir_sol/modelName, dir_sol/dataName
    if sol_filename.endswith(SOL_EXT): sol_filename = sol_filename[:-len(SOL_EXT)]
    # symbol_map_filename = symbol_filename + ".symbol_map.pickle"
    sol_filename = sol_filename + ".sol"

    # parse the SOL file
    with ReaderFactory(ResultsFormat.sol) as reader:
        results = reader(sol_filename, suffixes=suffixes)

    # # regenerate the symbol_map for this model
    # with open(symbol_map_filename, "rb") as f:
    #     symbol_cuid_pairs = pickle.load(f)
    # symbol_map = SymbolMap()
    # symbol_map.addSymbols((cuid.find_component(model), symbol)
    #                       for symbol, cuid in symbol_cuid_pairs)

    # tag the results object with the symbol_map passed as smap
    results._smap = smap

    return results

if __name__ == "__main__":
    from pyomo.opt import TerminationCondition
    from script import create_model

    model = create_model()
    sol_filename = "example.sol"
    symbol_map_filename = "example.nl.symbol_map.pickle"
    results = read_sol(model, sol_filename, symbol_map_filename)
    if results.solver.termination_condition != \
       TerminationCondition.optimal:
        raise RuntimeError("Solver did not terminate with status = optimal")
    model.solutions.load_from(results)
    print("Objective: %s" % (model.o()))
