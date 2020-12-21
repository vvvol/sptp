import pyomo.environ
from pyomo.core import ComponentUID
from pyomo.opt import ProblemFormat
# use fast version of pickle (python 2 or 3)
from six.moves import cPickle as pickle

NL_EXT = '.nl'


def write_nl(model, nl_filename, **kwds):
    """
    Writes a Pyomo model in NL file format and stores
    information about the symbol map that allows it to be
    recovered at a later time for a Pyomo model with
    matching component names.
    see [write] function from /usr/local/lib/python2.7/dist-packages/pyomo/opt/problem/ampl.py
    calls [convert_problem] from /usr/local/lib/python2.7/dist-packages/pyomo/opt/base/convert.py
    """
    symbol_map_filename = nl_filename + ".symbol_map.pickle"

    # write the model and obtain the symbol_map
    _, smap_id = model.write(nl_filename,
                             format=ProblemFormat.nl,
                             io_options=kwds)
    symbol_map = model.solutions.symbol_map[smap_id]

    # save a persistent form of the symbol_map (using pickle) by
    # storing the NL file label with a ComponentUID, which is
    # an efficient lookup code for model components (created
    # by John Siirola)
    tmp_buffer = {} # this makes the process faster
    symbol_cuid_pairs = tuple(
        (symbol, ComponentUID(var_weakref(), cuid_buffer=tmp_buffer))
        for symbol, var_weakref in symbol_map.bySymbol.items())
    with open(symbol_map_filename, "wb") as f:
        pickle.dump(symbol_cuid_pairs, f)

    return symbol_map_filename

def write_nl_smap(model, nl_filename, **kwds):
    """
    Writes a Pyomo model in NL file format and stores
    information about the symbol map that allows it to be
    recovered at a later time for a Pyomo model with
    matching component names.
    """

    # Remove possible suffix '.nl' if any
    if nl_filename.endswith(NL_EXT): nl_filename = nl_filename[:-len(NL_EXT)]

    symbol_map_filename = nl_filename+".symbol_map.pickle"

    # write the model and obtain the symbol_map
    nlFile, smap_id = model.write(nl_filename + ".nl",
                             format=ProblemFormat.nl,
                             io_options=kwds)
    symbol_map = model.solutions.symbol_map[smap_id]

    # save a persistent form of the symbol_map (using pickle) by
    # storing the NL file label with a ComponentUID, which is
    # an efficient lookup code for model components (created
    # by John Siirola)
    tmp_buffer = {} # this makes the process faster
    symbol_cuid_pairs = tuple(
        (symbol, ComponentUID(var_weakref(), cuid_buffer=tmp_buffer))
        for symbol, var_weakref in symbol_map.bySymbol.items())
    with open(symbol_map_filename, "wb") as f:
        pickle.dump(symbol_cuid_pairs, f)

    return nlFile, symbol_map_filename

def write_nl_only(model, nl_filename, **kwds):
    """
    Writes a Pyomo model in NL file format only and returns
    the symbol map that allows it to be
    recovered at a later time for a Pyomo model with
    matching component names.
    The function DOES NOT WRITE SYMBOL MAP TO FILE
    see [write] function from /usr/local/lib/python2.7/dist-packages/pyomo/opt/problem/ampl.py
    calls [convert_problem] from /usr/local/lib/python2.7/dist-packages/pyomo/opt/base/convert.py
    """
    # Remove possible suffix '.nl' if any
    if nl_filename.endswith(NL_EXT): nl_filename = nl_filename[:-len(NL_EXT)]

    # symbol_map_filename = nl_filename+".symbol_map.pickle"

    # write the model and obtain the symbol_map
    nlFile, smap_id = model.write(nl_filename + ".nl",
                             format=ProblemFormat.nl,
                             io_options=kwds)
    # symbol_map = model.solutions.symbol_map[smap_id]

    # # save a persistent form of the symbol_map (using pickle) by
    # # storing the NL file label with a ComponentUID, which is
    # # an efficient lookup code for model components (created
    # # by John Siirola)
    # tmp_buffer = {} # this makes the process faster
    # symbol_cuid_pairs = tuple(
    #     (symbol, ComponentUID(var_weakref(), cuid_buffer=tmp_buffer))
    #     for symbol, var_weakref in symbol_map.bySymbol.items())
    # with open(symbol_map_filename, "wb") as f:
    #     pickle.dump(symbol_cuid_pairs, f)

    return nlFile

def get_smap_var(model):
    """
    Writes a Pyomo model in NL file format only and returns
    the symbol map that allows it to be
    recovered at a later time for a Pyomo model with
    matching component names.
    The function DOES NOT WRITE SYMBOL MAP TO FILE
    see [write] function from /usr/local/lib/python2.7/dist-packages/pyomo/opt/problem/ampl.py
    calls [convert_problem] from /usr/local/lib/python2.7/dist-packages/pyomo/opt/base/convert.py
    """
    # Remove possible suffix '.nl' if any
    # if nl_filename.endswith(NL_EXT): nl_filename = nl_filename[:-len(NL_EXT)]

    # symbol_map_filename = nl_filename+".symbol_map.pickle"

    # write the model and obtain the symbol_map
    nlFile, smap_id = model.write('/dev/null',
                             format=ProblemFormat.nl, io_options={})
    symbol_map = model.solutions.symbol_map[smap_id]

    # # save a persistent form of the symbol_map (using pickle) by
    # # storing the NL file label with a ComponentUID, which is
    # # an efficient lookup code for model components (created
    # # by John Siirola)
    # tmp_buffer = {} # this makes the process faster
    # symbol_cuid_pairs = tuple(
    #     (symbol, ComponentUID(var_weakref(), cuid_buffer=tmp_buffer))
    #     for symbol, var_weakref in symbol_map.bySymbol.items())
    # with open(symbol_map_filename, "wb") as f:
    #     pickle.dump(symbol_cuid_pairs, f)

    return symbol_map



if __name__ == "__main__":
    from script import create_model

    model = create_model()
    nl_filename = "example.nl"
    nlFile, symbol_map_filename = write_nl_smap(model, nl_filename, symbolic_solver_labels=True)
    print("        NL File: %s" % (nlFile))
    print("Symbol Map File: %s" % (symbol_map_filename))
