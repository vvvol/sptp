# sptp
# SPecial Transportation Problem.
To test solving of transportation problems by SCIP and other solvers.

Final version of model and data processing are in:

`SptpData_5.py, sptpmodel_5.py, demoSptp_5.py`

Example of run to create NL-file (and ROW-, COL-files as well):

`$ python demoSptp_5.py -a nl -pr dv5 -wd ./temp`

In the above command relative path to the working folder is set by `-wd` option's value (full name `--workdir`).

Input data are read from 7 (seven) CSV-files, see leading comment in `SptpData_5.py` for details.

In the current demo-version user should put pathes (relative or absolute) to the arguments of SptpData_5 object constructor, [lines 110-116](https://github.com/vvvol/sptp/blob/8fd10342f288072efbdde4b03031e532d2fc22b2/demoSptp_5.py#L109) in demoSptp_5.py. 

On state-of-the-art desktop computer generation of desired \*.nl, \*.col, \*.row files may take about a minute. Above files should appear in working folder. 

Example to process SOL-file which is asumed to be placed to the same working folder

`$ python demoSptp_5.py -a sol -pr dv5 -wd ./temp`
