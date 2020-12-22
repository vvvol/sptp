Utilities to write opt. models as NL-files and read solutions from SOL-files
=======================

Actually, there are modified examples from https://github.com/Pyomo/PyomoGallery/tree/master/asl_io.
The main purpose was to save NL-writing timespan at the expense of skipping 

`symbol_map = model.solutions.symbol_map[smap_id]`

See, `def write_nl_only(...)` in *write.py* and corresponding `def read_sol_smap(model,...)` in *read.py*.  
