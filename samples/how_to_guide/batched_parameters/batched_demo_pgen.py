"""An example file that produces a custom parameters for the batched parameters demo"""

from maestrowf.datastructures.core import ParameterGenerator

import csv
import rich.pretty as rp

def get_custom_generator(env, **kwargs):
    """
    Create a custom populated ParameterGenerator.  Uses pargs to control
    reading of parameters from a pre-built csv file for chunked execution.

    pargs:
      CSV:   name of csv file to read parameters from
      NROWS: number of rows (param sets) to read out of the csv file
      START: optional row offest to start reading parameters from
      INDEX: optional name of index column (these are not parameters, just
             parameter set id's).  Default: no index column.
      DEBUG: optional debug flag for extra printouts of parameter reading.
             Any string turns this on.

    :params env: A StudyEnvironment object containing custom information.
    :params kwargs: A dictionary of keyword arguments this function uses.
    :returns: A ParameterGenerator populated with parameters.
    """
    p_gen = ParameterGenerator()

    # Check for the input keywords
    params_csv_file_name = kwargs.get('CSV').strip()
    num_params = int(kwargs.get('NROWS', '-1').strip())
    offset = int(kwargs.get('START', '0').strip())
    index_name = kwargs.get('INDEX', '').strip()
    debug = kwargs.get('DEBUG', '').strip()

    params_csv = []
    param_names = []
    with open(params_csv_file_name, 'r') as csvfile:
        csv_data = csv.DictReader(csvfile)

        if debug:
            rp.pprint("Reading csv:")

        for row in csv_data:
            if debug:
                rp.pprint(row)
            params_csv.append(row)

        param_names = csv_data.fieldnames

    # excluding optional first column: update name if calling it something
    # other than paramset, or leave out the pop and remove that column from the
    # csv input
    params = {}
    for param_name in param_names:
        # Skip the index in case an index column is specified in the csv
        if index_name and param_name == index_name:
            continue

        if debug:
            rp.pprint(f"Adding Param: {param_name}")

        p_gen.add_parameter(
            param_name.strip().upper(),  # key: strip it in case there was whitespace in the csv file
            [row[param_name].strip() for idx, row in enumerate(params_csv) if idx >= offset and (num_params > idx-offset or num_params < 0)],  # values
            f"{param_name.strip().upper()}.%%",  # label
        )

    if debug:
        rp.pprint(p_gen.parameters)
        rp.pprint(p_gen.names)

    return p_gen
