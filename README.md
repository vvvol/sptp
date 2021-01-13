# sptp
# SPecial Transportation Problem.
To test solving of transportation problems by SCIP and other solvers.

Final version of model and data processing are in:

SptpData_5.py, sptpmodel_5.py, demoSptp_5.py

Example of run to create NL-file (and ROW-, COL-files as well):

`$ python demoSptp_5.py -a nl -pr dv5 -wd ./temp`

In the above command relative path to the working folder is set by `-wd` option's value (full name `--workdir`)
