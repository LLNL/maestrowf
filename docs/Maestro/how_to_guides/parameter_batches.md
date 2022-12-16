# Processing large numbers of parameters in batches
---

Scaling up the numbers of parameter combinations in studies can run into a few road blocks:

* **File system overloading**

    The current version of Maestro builds a single level tree in the step workspaces, with parameter combinations expanded flatly under the step root.  This design can slow down other file system operations such as `rm` and `ls`, with impacts varying with specific file systems.
    
    Additionally, there are inode and disk space limits (or potentially per user quotas on shared systems) that when hit can bring a study to a halt until things are cleaned up.
    
* **HPC scheduler overloading**

    Some HPC schedulers can run into scaling issues with large studies as most of the [script/scheduler adapters](../scheduling.md) treat each instance of a step (one parameter combination applied to a step) as discrete batch jobs.  Thus naively launching studies with thousands or more parameter combinations can quickly swamp the scheduler.
    
    There are a few solutions to this problem depending on the specific study, including use of the `throttle` argument to the run command to limit the number of jobs to submit to the scheduler queue, or if jobs are quick running and/or small, use the [flux](../scheduling.md#flux) adapter to pack many jobs into an allocation.  However, this still leaves open the issue of swamping the file system.


An alternative that can be used to address both concerns is to insert gaps in the execution by processing large numbers of parameter sets in batches across multiple studies.  This batched execution allows cleanup of each batch's outputs before the next begins, freeing up precious file system space and avoiding deadlocks when that space/quota is reached.  As a simple model problem we will use [`pgen`](../parameter_specification.md#parameter-generator-pgen) to provide command line control of the number of parameters to read out of a csv file in each executed study in this batched execution option.  

!!! note

    This can also use data sources other than csv, including networked sources such as a database with minimal changes.


## Generating the parameter set
---

This example will be working with the following set of parameters found in the `params.csv` file
in the batched\_parameters samples folder.  The parameter set was generated using the `csv_generator.py` included here (and in the samples folder), facilitating experiments with alternate
parameter naming/counts.  In this example there's an index column `param_combo`, which gets ignored
in the `pgen` calls later on.  The csv file is all lower cased, but the Maestro tokens are uppercased
to make them distinct in the study specification as shown inside the brackets (`[ ]`) in the column names below.

<!-- add link to github's samples/how_to_guide/batched_parameters folder in here -->
=== "params.csv"
    <!-- NOTE: make a custom superfence for reading these in later -->
    
    | param\_combo  | param1 [`$(PARAM1)`]  | param2 [`$(PARAM2)`]  | param3 [`$(PARAM3)`]  |
    |:--|:--|:--|:--|
    |  0  | 94  | 71  | 72  |
    |  1  | 48  | 18  | 60  |
    |  2  | 45  | 56  | 23  |
    |  3  |  0  | 30  | 95  |
    |  4  | 77  |  8  | 34  |
    |  5  | 99  | 44  | 99  |
    |  6  | 19  | 62  | 52  |
    |  7  | 89  | 14  | 26  |
    |  8  | 82  |  6  | 24  |
    |  9  | 32  | 80  | 83  |
    | 10  | 68  | 58  | 65  |
    | 11  | 13  | 45  | 13  |
    | 12  | 65  | 99  | 70  |
    | 13  | 44  | 94  | 86  |
    | 14  | 50  | 35  | 50  |
    | 15  | 89  | 53  | 65  |
    | 16  | 28  | 97  | 47  |
    | 17  | 98  | 93  | 86  |
    | 18  | 24  | 17  | 97  |
    | 19  | 39  | 50  | 83  |
    
=== "csv_generator.py"

    ``` python
    --8<-- "samples/how_to_guide/batched_parameters/csv_generator.py"
    ```

## Study specification
---

The sample specification for this is a very simple single step study that echoe's the input parameters and their
values.

<!-- Expand to templated version -> csv generator also populates this template to ensure param names match up? -->

``` yaml
--8<-- "samples/how_to_guide/batched_parameters/batched_parameters_demo.yaml"

```

## Running a subset of parameters
---

All of the control of which parameters get run in a given study go through [`pgen` via it's `pagrgs`](../parameter_specification.md#pgen-arguments-pargs).  The `batched_demo_pgen.py` custom generator has 5 available pargs that control the csv parsing and parameter outputs:

* `CSV`: name/path of csv file to read parameters from

* `NROWS`: number of parameter sets/combinations to read in for this instance of the study

* `START`: optional row offset to start reading parameters from (i.e. for additional instances of the study)

* `INDEX`: optional name of the index column.  This column is not treated as a parameter to be used in the study. 

* `DEBUG`: optional flag to add debugging output during study initialization.  If any string is added here then the pgen will print out all parameter names and values read from the csv file.


``` python
--8<-- "samples/how_to_guide/batched_parameters/batched_demo_pgen.py"
```

Running an instance with the first 3 rows of parameter combos from the csv is as simple as:

``` console
maestro run --dry batched_parameters_demo.yaml --pgen batched_demo_pgen.py --pargs "INDEX:param_combo" --pargs "CSV:params.csv" --pargs "DEBUG:true" --pargs "NROWS:3"
```

We can then verify the workspace is as expected, with three directories under the `echo-params` step for the three parameter combintations selected from the csv input

![Batched Parameters First Three Workspace](../../assets/images/examples/how_to_guides/batched_parameters/batched_params_first_three_workspace.svg)

## Next steps
---

The next step in this 'how-to' is left up to the reader.  At this point we have a study and parameter generator that can be used to process large numbers of parameter combinations in batches.  Managing the disk-space/inode concerns can now be addressed between parameter batches.  Potential options could include:

* Extracting the necessary data and uploading into an external database, either offline or as subsequent steps in the study executed by Maestro directly. The entire study workspace can then be deleted upon success (what determines success being highly workflow dependent)

* Tar up the outputs.  This could be as simple as tarring up the whole Maestro study workspace for later processing, or more targetting tarring of each step's outputs to compress the contents of each step/parameter workspace to a single file to conserve inodes by deleting the originals.

* Archive the outputs to some other file system, either with or without tarring

* ...
