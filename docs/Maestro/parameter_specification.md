#  Specifying Study Parameters
---

Maestro supports parameterization as a means of iterating over steps in a study with varying information.  Maestro uses [token replacement](specification.md#tokens-maestros-minimal-workflow-dls) to define variables in the study specification to be replaced when executing the study.  Token replacement can be used in various contexts in Maestro; however Maestro implements specific features for managing parameters.

Maestro makes no assumptions about how parameters are defined or used in a study, enabling flexibility in regards to how a study may be configured with parameters.

There are two ways Maestro supports parameters:

  * Directly in the study specification as the `global.parameters` block

  * Through the use of a user created Python function called [pgen](#parameter-generator-pgen)


## Maestro Parameter Block
---

The quickest and easiest way to setup parameters in a Maestro study is by defining a ``global.parameters`` block directly in the specification

``` yaml
global.parameters:
    TRIAL:
        values  : [1, 2, 3, 4, 5, 6, 7, 8, 9]
        label   : TRIAL.%%

    SIZE:
        values  : [10, 10, 10, 20, 20, 20, 30, 30, 30]
        label   : SIZE.%%

    ITERATIONS:
        values  : [10, 20, 30, 10, 20, 30, 10, 20, 30]
        label   : ITER.%%
```

The above example defines the parameters ``TRIAL``, ``SIZE``, and ``ITERATIONS``. Parameters can be used in study steps to vary information. When a parameter is defined in a study, Maestro will automatically detect the usage of a parameter moniker and handle the substitution automatically in the study expansion. This ensures that each set of parameters are run as part of the study.

The ``label`` key in the block specifies the pattern to use for the directory name when the workspace is created. By default, Maestro constructs a unique workspace for each parameter combination.

Defining multiple parameters in the parameter block will share a 1:1 mapping. Maestro requires all combinations be resolved when using the parameter block. The combinations in the above example will be expanded as follows:

  * TRIAL.1.SIZE.10.ITERATIONS.10

  * TRIAL.2.SIZE.10.ITERATIONS.20

  * TRIAL.3.SIZE.10.ITERATIONS.30

  * ...

Maestro does not do any additional operations on parameters such as Cartesian products. If more complex methodologies are required to define parameters then the use of Maestro's [`pgen`](#parameter-generator-pgen) is recommended.

!!! note

    Even when using the pgen functionality from the command line, Maestro will still initially verify that the provided specification is valid as if it planned to use it entirely (without pgen). If you are using the ``global.parameters`` block solely as documentation, we recommend that you comment out the ``global.parameters`` block. This lets the validator ignore it.

Defined parameters can be used in steps directly:

``` yaml title="parameterized run-lulesh step"
   - name: run-lulesh
     description: Run LULESH.
     run:
         cmd: |
             $(LULESH)/lulesh2.0 -s $(SIZE) -i $(ITERATIONS) -p > $(outfile)
         depends: [make-lulesh]
```

Even though this is defined in Maestro as a single step, Maestro will automatically run this step with each parameter combinations. This makes it very easy to setup studies and apply parameters to be run.

!!! note

    Maestro will only use parameters if they've been defined in at least one step

In addition to direct access to parameter values, a parameter label can be used in steps by appending the ``.label`` moniker to the name (as seen below with ``$(ITERATIONS.label)``):

``` yaml title="run-lulesh step using parameter labels"
   - name: run-lulesh
     description: Run LULESH.
     run:
         cmd: |
             echo "Running case: $(SIZE.label), $(ITERATIONS.label)"
             $(LULESH)/lulesh2.0 -s $(SIZE) -i $(ITERATIONS) -p > $(outfile)
         depends: [make-lulesh]
```

<!-- Add sample expanded/concrete steps scripts here? -->

## What can be Parameterized in Maestro?
---

A common use case for Maestro is to use the parameter block to specify values to iterate over for a simulation parameter study; however, Maestro does not make any assumptions about what these values are. This makes the use of Maestro's parameter block very flexible. For example, Maestro does not require the parameter variations to be numeric.

``` yaml title="single parameter study"
study:
    - name: run-simulation
      description: Run a simulation.
      run:
          cmd: |
              $(CODE) -in $(SPECROOT)/$(INPUT)
          depends: []

global.parameters:
    INPUT:
        values: [input1.in, input2.in, input3.in]
        label: INPUT.%%
```

The above example highlights a partial study spec that defines a parameter block of simulation inputs that will be varied when the study runs. The ``run-simulation`` step  will run three times, once for each defined input file.

``` yaml title="multi-parameter study"
study:
    - name: run-simulation
      description: Run a simulation.
      run:
          cmd: |
              $(CODE_PATH)/$(VERSION)/code.exe -in $(SPECROOT)/$(INPUT)
          depends: []

global.parameters:
    INPUT:
        values  : [input1.in, input2.in, input3.in, input1.in, input2.in, input3.in]
        label   : INPUT.%%
    VERSION:
        values  : [4.0.0, 4.0.0, 4.0.0, 5.0.0, 5.0.0, 5.0.0]
        label   : VERSION.%%
```

This example parameterizes the inputs and the version of the code being run.  Maestro will run each input with the different code version.  The above example assumes that all the code versions share a base path, ``$(CODE_PATH)`` which is inserted via the token replacment mechanism from the env block to yeild the full paths (e.g. /usr/gapps/code/4.0.0/code.exe).

## Where can Parameters be used in Study Steps?
---

Maestro uses monikers to reference parameters in study steps, and will automatically perform token replacement on used parameters when the study is run. The page Maestro Token Replacement goes into detail about how token replacement works in Maestro.

<!-- add maestro token replacement section reference -->

Maestro is very flexible in the way it manages token replacement for parameters and as such tokens can be used in a variety of ways in a study.

### Cmd block
---

Parameters can be defined in the Maestro ``cmd`` block in the study step. Everything in Maestro's ``cmd`` block will be written to a bash shell or batch script (if batch is configured). Any shell commands should be valid in the ``cmd`` block. A common way to use parameters is to pass them in via arguments to a code, script, or tool.

``` yaml
...

    - name: run-simulation
      description: Run a simulation.
        run:
            cmd: |
                /usr/gapps/code/bin/code -in input.in -def param $(PARAM)
            depends: []

...
```

The specific syntax for using a parameter with a specific code, script, or tool will depend on how the application supports command line arguments.

### Batch Configuration
---

Step based batch configurations can also be parameterized in Maestro. This provides an easy way to configure scaling studies or to manage studies where batch settings are dependent on the parameter values.

``` yaml
study:
    - name: run-simulation
      description: Run a simulation.
      run:
        cmd: |
            $(CODE_PATH)/$(VERSION)/code.exe -in input.in -def RES $(RES)
        procs: $(PROC)
        nodes: $(NODE)
        walltime: $(WALLTIME)
        depends: []

global.parameters:
    RES:
        values  : [2, 4, 6, 8]
        label   : RES.%%
    PROC:
        values  : [8, 8, 16, 32]
        label   : PROC.%%
    NODE:
        values  : [1, 1, 2, 4]
        label   : NODE.%%
    WALLTIME:
        values  : ["00:10:00", "00:15:00", "00:30:00", "01:00:00"]
        label   : PROC.%%
```

<!-- Add some dag graphs in here at some point? -->

### Parameter Generator (pgen)
---

Maestro's Parameter Generator (**pgen**) supports setting up more flexible and complex parameter generation.  Maestro's **pgen** is a user supplied python file that contains the parameter generation logic, overriding the ``global.parameters`` block in the yaml specification file.  To run a Maestro study using a parameter generator just pass in the path to the **pgen** file to Maestro on the command line when launching the study, such as this example where the study specification file and **pgen** file live in the same directory:

``` console

   $ maestro run study.yaml --pgen pgen.py
   
```

The minimum requirements for making a valid pgen file is to make a function called `get_custom_generator`, which returns a Maestro [ParameterGenerator][maestrowf.datastructures.core.parameters.ParameterGenerator] object as demonstrated in the simple example below:

``` python
   from maestrowf.datastructures.core import ParameterGenerator

   def get_custom_generator(env, **kwargs):
       p_gen = ParameterGenerator()
       params = {
           "COUNT": {
               "values": [i for i in range(1, 10)],
               "label": "COUNT.%%"
           },
       }

       for key, value in params.items():
           p_gen.add_parameter(key, value["values"], value["label"])

       return p_gen
```

<!-- add link to global.parameters section of spec? -->
The object simply builds the same nested key:value pairs seen in the ``global.parameters`` block available in the yaml specification.

For this simple example above, this may not offer compelling advantages over writing out the flattened list in the yaml specification directly.  This programmatic approach becomes preferable when expanding studies to use hundreds of parameters and parameter values or requiring non-trivial parameter value distributions.  The following examples will demonstrate these scenarios using both standard python library tools and additional 3rd party packages from the larger python ecosystem.

### Example: Lulesh Itertools

  Using Python's [itertools](https://docs.python.org/3/library/itertools.html?highlight=itertools) package from the standard library to perform a Cartesian Product of parameters in the lulesh example specification.

``` python linenums="1", title="lulesh_itertools_pgen"
--8<-- "samples/parameterization/lulesh_itertools_pgen.py"
```

This results in the following set of parameters, matching the lulesh sample workflow:

<table style="border-collapse: collapse; width: 100%;"><colgroup><col style="width: 10.0324%;"><col style="width: 10.0324%;"><col style="width: 10.0324%;"><col style="width: 10.0324%;"><col style="width: 10.0324%;"><col style="width: 10.0324%;"><col style="width: 10.0324%;"><col style="width: 10.0324%;"><col style="width: 10.0324%;"><col style="width: 9.78964%;"></colgroup>
<tbody>
<tr>
<td>Parameter</td>
<td colspan="9", style="text-align: center; verticla-align:middle;">Values</td>
</tr>
<tr>
<td>TRIAL</td>
<td style="text-align: center; vertical-align: middle;">0</td>
<td style="text-align: center; vertical-align: middle;">1</td>
<td style="text-align: center; vertical-align: middle;">2</td>
<td style="text-align: center; vertical-align: middle;">3</td>
<td style="text-align: center; vertical-align: middle;">4</td>
<td style="text-align: center; vertical-align: middle;">5</td>
<td style="text-align: center; vertical-align: middle;">6</td>
<td style="text-align: center; vertical-align: middle;">7</td>
<td style="text-align: center; vertical-align: middle;">8</td>
</tr>
<tr>
<td>SIZE</td>
<td style="text-align: center; vertical-align: middle;">10</td>
<td style="text-align: center; vertical-align: middle;">10</td>
<td style="text-align: center; vertical-align: middle;">10</td>
<td style="text-align: center; vertical-align: middle;">20</td>
<td style="text-align: center; vertical-align: middle;">20</td>
<td style="text-align: center; vertical-align: middle;">20</td>
<td style="text-align: center; vertical-align: middle;">30</td>
<td style="text-align: center; vertical-align: middle;">30</td>
<td style="text-align: center; vertical-align: middle;">30</td>
</tr>
<tr>
<td>ITER</td>
<td style="text-align: center; vertical-align: middle;">1</td>
<td style="text-align: center; vertical-align: middle;">2</td>
<td style="text-align: center; vertical-align: middle;">3</td>
<td style="text-align: center; vertical-align: middle;">4</td>
<td style="text-align: center; vertical-align: middle;">5</td>
<td style="text-align: center; vertical-align: middle;">6</td>
<td style="text-align: center; vertical-align: middle;">7</td>
<td style="text-align: center; vertical-align: middle;">8</td>
<td style="text-align: center; vertical-align: middle;">9</td>
</tr>
</tbody>
</table>

``` mermaid
flowchart TD;
    A(study root) --> COMBO1;
    subgraph COMBO1 [Combo #1]
      subgraph run-simulation1 [run-simulation]
        B("TRIAL: 0\n SIZE: 10\n ITER: 1")
      end
    end
    style B text-align:justify
    A --> COMBO2
    subgraph COMBO2 [Combo #2]
      subgraph run-simulation2 [run-simulation]
        C("TRIAL: 1\n SIZE: 10\n ITER: 2")
      end
    end
    style C text-align:justify
    A --> COMBO3
    subgraph COMBO3 [Combo #3]
      subgraph run-simulation3 [run-simulation]
        D("TRIAL: 2\n SIZE: 10\n ITER: 3")
      end
    end
    style D text-align:justify
    A --> COMBO4
    subgraph COMBO4 [Combo #4]
      subgraph run-simulation4 [run-simulation]
        E("TRIAL: 3\n SIZE: 20\n ITER: 4")
      end
    end
    style E text-align:justify
    A --> COMBO5
    subgraph COMBO5 [Combo #5]
      subgraph run-simulation5 [run-simulation]
        F("TRIAL: 4\n SIZE: 20\n ITER: 5")
      end
    end
    style F text-align:justify
    A --> COMBO6
    subgraph COMBO6 [Combo #6]
      subgraph run-simulation6 [run-simulation]
        G("TRIAL: 5\n SIZE: 20\n ITER: 6")
      end
    end
    style G text-align:justify
    A --> COMBO7
    subgraph COMBO7 [Combo #7]
      subgraph run-simulation7 [run-simulation]
        H("TRIAL: 6\n SIZE:  30\n ITER:   7")
      end
    end
    style H text-align:justify
    A --> COMBO8
    subgraph COMBO8 [Combo #8]
      subgraph run-simulation8 [run-simulation]
        I("TRIAL: 7\n SIZE: 30\n ITER: 8")
      end
    end
    style I text-align:justify
    A --> COMBO9
    subgraph COMBO9 [Combo #9]
      subgraph run-simulation9 [run-simulation]
        J("TRIAL: 8\n SIZE: 30\n ITER: 9")
      end
    end
    style J text-align:justify
```
<!-- Why doesn't justify actually work?  seems to fall back to left and eats extra spaces inside the lines too...-->

## Pgen Arguments (pargs)
----------------------

There is an additional [`pgen`](#parameter-generator-pgen) feature that can be used to make them more dynamic.  The above example generates a fixed set of parameters, requiring editing the [lulesh\_itertools\_pgen](#example-lulesh-itertools) file to change that.  Maestro supports passing arguments to these generator functions on the command line:


``` console

$ maestro run study.yaml --pgen itertools_pgen_pargs.py --pargs "SIZE_MIN:10" --pargs "SIZE_STEP:10" --pargs "NUM_SIZES:4"

```

Each argument is a string in ``key:value`` form, which can be accessed in the parameter generator function as shown below:

``` python linenums="1", title="Itertools parameter generator with pargs (itertools_pgen_pargs.py)"

   from maestrowf.datastructures.core import ParameterGenerator
   import itertools as iter

   def get_custom_generator(env, **kwargs):
       p_gen = ParameterGenerator()

       # Unpack any pargs passed in
       size_min = int(kwargs.get('SIZE_MIN', '10'))
       size_step = int(kwargs.get('SIZE_STEP', '10'))
       num_sizes = int(kwargs.get('NUM_SIZES', '3'))

       sizes = range(size_min, size_min+num_sizes*size_step, size_step)
       iterations = (10, 20, 30)

       size_values = []
       iteration_values = []
       trial_values = []

       for trial, param_combo in enumerate(iter.product(sizes, iterations)):
           size_values.append(param_combo[0])
           iteration_values.append(param_combo[1])
           trial_values.append(trial)

       params = {
           "TRIAL": {
               "values": trial_values,
               "label": "TRIAL.%%"
           },
           "SIZE": {
               "values": size_values,
               "label": "SIZE.%%"
           },
           "ITER": {
               "values": iteration_values,
               "label": "ITER.%%"
           },
       }

       for key, value in params.items():
           p_gen.add_parameter(key, value["values"], value["label"])

       return p_gen
```

Passing the **pargs** ```SIZE_MIN:10'``, ``'SIZE_STEP:10'``, and ``'NUM_SIZES:4'`` then yields the expanded parameter set:

<table style="border-collapse: collapse; width: 100%;"><colgroup><col style="width: 10.0324%;"><col style="width: 10.0324%;"><col style="width: 10.0324%;"><col style="width: 10.0324%;"><col style="width: 10.0324%;"><col style="width: 10.0324%;"><col style="width: 10.0324%;"><col style="width: 10.0324%;"><col style="width: 10.0324%;"><col style="width: 9.78964%;"></colgroup>
<tbody>
<tr>
<td>Parameter</td>
<td colspan="12", style="text-align: center; verticla-align:middle;">Values</td>
</tr>
<tr>
<td>TRIAL</td>
<td style="text-align: center; vertical-align: middle;">0</td>
<td style="text-align: center; vertical-align: middle;">1</td>
<td style="text-align: center; vertical-align: middle;">2</td>
<td style="text-align: center; vertical-align: middle;">3</td>
<td style="text-align: center; vertical-align: middle;">4</td>
<td style="text-align: center; vertical-align: middle;">5</td>
<td style="text-align: center; vertical-align: middle;">6</td>
<td style="text-align: center; vertical-align: middle;">7</td>
<td style="text-align: center; vertical-align: middle;">8</td>
<td style="text-align: center; vertical-align: middle;">9</td>
<td style="text-align: center; vertical-align: middle;">10</td>
<td style="text-align: center; vertical-align: middle;">11</td>
</tr>
<tr>
<td>SIZE</td>
<td style="text-align: center; vertical-align: middle;">10</td>
<td style="text-align: center; vertical-align: middle;">10</td>
<td style="text-align: center; vertical-align: middle;">10</td>
<td style="text-align: center; vertical-align: middle;">20</td>
<td style="text-align: center; vertical-align: middle;">20</td>
<td style="text-align: center; vertical-align: middle;">20</td>
<td style="text-align: center; vertical-align: middle;">30</td>
<td style="text-align: center; vertical-align: middle;">30</td>
<td style="text-align: center; vertical-align: middle;">30</td>
<td style="text-align: center; vertical-align: middle;">40</td>
<td style="text-align: center; vertical-align: middle;">40</td>
<td style="text-align: center; vertical-align: middle;">40</td>
</tr>
<tr>
<td>ITER</td>
<td style="text-align: center; vertical-align: middle;">10</td>
<td style="text-align: center; vertical-align: middle;">20</td>
<td style="text-align: center; vertical-align: middle;">30</td>
<td style="text-align: center; vertical-align: middle;">10</td>
<td style="text-align: center; vertical-align: middle;">20</td>
<td style="text-align: center; vertical-align: middle;">30</td>
<td style="text-align: center; vertical-align: middle;">10</td>
<td style="text-align: center; vertical-align: middle;">20</td>
<td style="text-align: center; vertical-align: middle;">30</td>
<td style="text-align: center; vertical-align: middle;">10</td>
<td style="text-align: center; vertical-align: middle;">20</td>
<td style="text-align: center; vertical-align: middle;">30</td>
</tr>
</tbody>
</table>

Notice that using the pgen input method makes it trivially easy to add 1000's of parameters, something which would be cumbersome via manual editing of the ``global.parameters`` block in the study specification file.

There are no requirements to cram all of the logic into the `get_custom_generator` function.  The next example demonstrates using 3rd party libraries and breaking out the actual parameter generation algorithm into separate helper functions that the `get_custom_generator` function uses to get some more complicated distributions.  The only concerns with this approach will be to ensure the library is installed in the same virtual environment as the Maestro executable you are using.  The simple parameter distribution demoed in here is often encountered in polynomial interpolation applications and is designed to suppress the Runge phenomena by sampling the function to be interpolated at the Chebyshev nodes.

### Example: Parameterized Chebyshev Sampling with `pargs`
  Using [numpy](https://numpy.org/) to calculate a sampling of a function at the Chebyshev nodes.

``` python linenums="1", title="np_cheb_pgen_pargs.py"
--8<-- "samples/parameterization/np_cheb_pgen_pargs.py"
```

Running this parameter generator with the following pargs

``` console

$ maestro run study.yaml --pgen np_cheb_pgen.py --pargs "X_MIN:0" --pargs "X_MAX:3" --pargs "NUM_PTS:11"
   
```

results in the 1D distribution of points for the ``X`` parameter shown by the orange circles:

![Numpy Chebyshev Parameter Distribution](../assets/images/examples/pgen/cheb_map.png)


Referencing Values from a Specification's Env Block
---------------------------------------------------

In addition to command line arguments via [`pargs`](#pgen-arguments-pargs), the variables defined in the [`env` block](specification.md#environment-env) in the workflow specification file can be accessed inside the [ParameterGenerator][maestrowf.datastructures.core.parameters.ParameterGenerator] objects, which is passed in to the user defined `get_custom_generator` function as the first argument.  The lulesh sample specification can be extended to store the default values for the [`pgen`](#parameter-generator-pgen), enhancing the reproducability of the generator.  The following example makes use of an optional ``seed`` parameter which can be added to the [`env` block](specification.md#environment-env) or set via [`pargs`](#pgen-arguments-pargs) to make a repeatable study specification, while omitting it can enable fully randomized workflows upon every instantiation.  The variables are accessed via the [StudyEnvironment][maestrowf.datastructures.core.studyenvironment.StudyEnvironment] objects'  [`find()`][maestrowf.datastructures.core.studyenvironment.StudyEnvironment.find] function, which will return ``None`` if the variable is not defined in the study specification.

``` python linenums="1", title="lulesh_montecarlo_args.py", hl_lines="16 21 22 23 24 25"
--8<-- "samples/parameterization/lulesh_montecarlo_args.py"
```
