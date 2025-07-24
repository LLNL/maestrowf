# Study Specification

The study specification is the main definition of work and is the main record of
a user specified workflow. A complete specification is made up of the following
components:

**Key**                           |  **Required?** | **Description** |
    :-                            |   :-:          |  :-             |
[`description`](#description)     | Yes            | General information about a study and its high-level purpose |
[`batch`](#batch)                 | No             | Settings for submission to batch systems |
[`env`](#environment)             | No             | Fixed constants and other values that are globally set and referenced |
[`study`](#workflow)              | Yes            | Tasks that the study is composed of and are executed in a defined order |
[`global.parameters`](#parameters)| No             | Parameters that are user varied and applied to the workflow |

This page will break down the keys available in each section and what they provide.  But first, a look at the DSL embedded in the specification that appears in multiple sections.

<br/>

## Tokens: Maestro's Minimal Workflow DSL
----

Maestro takes a minimalist approach to it's workflow language features that are available in the study specification.  All of this is contained in the token replacement hooks available in the [`study`](#workflow) and [`env`](#environment) blocks.  These tokens are referenced using the `$(TOKEN_NAME)` syntax, with the `$( )` encapsulating this minimal dsl.

!!! note

    These tokens are currently limited to simple data types owing to the initial design being aimed at injecting values onto command lines.  This means array and dict types are supported in the current version of this DSL.

### Default Tokens
---

There are a few special tokens that are always available:

 **Name** |  **Description**  |  **Notes**  |
  :- |      :-           |     :-      |
`$(SPECROOT)`              | This defines the base path of the study specification | This provides a portable relative path to use with associated dependencies and supporting scripts/tools |
 `$(OUTPUT_PATH)`           | This is the path to the current study instance | OUTPUT_PATH can be specified in the env block's `variables` group providing a way to group the timestamped instance directories instead of polluting the $(SPECROOT) path |
 `$(LAUNCHER)`              | Abstracts HPC scheduler specific job launching wrappers such as srun (SLURM) | Primary mechanism for making study steps system agnostic and portable |
 `$(WORKSPACE)`             | Can be used in a step to reference the current step path | |
| <span style="white-space:nowrap;">`$(<step_name>.workspace)`</span> | Can be used in a step to reference path to other previous step workspaces | `<step-name>` is the `name` key in each study step |

The following example shows use of the first two to help with study inputs and outputs.  This uses `$(SPECROOT)` to access a supporting tool that lives alongside the study specification and then writes all instances of this study (timestamped directories) into a `SAMPLE_STUDY_OUTPUTS` directory to prevent pollution of the directory the study is invoked from.

``` yaml
env:
    variables:
        SUPPORTING_TOOL1: my_helper_tool.py
    labels:
        SUPPORTING_TOOL1_PATH: $(SPECROOT)/SUPPORTING_TOOL1
        
study:
    - name: sample-step-1
      description: sample study step
      run:
          cmd: |
            cp $(SUPPORTING_TOOL1_PATH) .
            
            # Run the tool
            python $(SUPPORTING_TOOL1) -o sample_output.yaml

```

<!-- Add workspace diagram (enable mock output structures from yaml from filesystem tree drawing tool -->
### Environment Tokens
---

In the `env` block every key in the `variables` and `labels` blocks can be referenced as a token.  Additionally, the dependencies entries can be referenced via tokens, with the tokens being the `name` keys in each one.

``` yaml
env:
    variables:
        VAR1: value1
        VAR2: value2
        MODEL1: my_model.input
      
    labels:
        PATH1: /dev/$(VAR2)
        
    dependencies:
        paths:
            - name: CODE
              path: /path/to/simulation/code
 
        git:
            - name: MODEL_REPO
              path: $(OUTPUT_PATH)
              url: https://your.git.host/models.git
              tag: 2.9.15
      
study:
    - name: step1
      description: just a sample step
      run:
          cmd: |
            echo "The value of 'VAR1' is $(VAR1)"
            echo "And this is the value of 'PATH1': $(PATH1)"
            
            cp $(MODEL_REPO)/$(MODEL1) .
            
            $(LAUNCHER) $(CODE) -in $(MODEL1)
            
          procs: 1
          nodes: 1
          walltime: "00:01:00"
```

### Parameter Tokens
---

Parameters follow the convention in the `env`'s `variables` and `labels` blocks where the token name is the key in the `global.parameters` block (or the `pgen` equivalent).  The big difference with substitution of parameter tokens is that only single values are replaced.  The expansion process will create one step per value in these tokens, and so using them in your steps/labels is akin to working with a single instance.  Additionally parameters have a string formatted representation in the `label` key which can be accessed similar to step workspaces: `(PARAM1.label)`.  In the below example this is combined with the `OUTPUTNAME` label to include the parameter label in the steps generated output files in place of a more generic single name for all instances of the step.  Three files will be output by the model in this case: `MODEL_OUTPUT_PARAM1.1.out`, `MODEL_OUTPUT_PARAM1.2.out`, and `MODEL_OUTPUT_PARAM1.3.out`.

``` yaml
env:
    variables:
        VAR1: value1
        VAR2: value2
        MODEL1: my_model.input
      
    labels:
        PATH1: /dev/$(VAR2)  # (1)
        OUTPUTNAME: MODEL_OUTPUT_$(PARAM1.label).out #(2)

    dependencies:
        paths:
            - name: CODE
              path: /path/to/simulation/code
 
        git:
            - name: MODEL_REPO
              path: $(OUTPUT_PATH)
              url: https://git-url.llnl.gov/models.git
              tag: 2.9.15
      
study:
    - name: step1
      description: just a sample step
      run:
          cmd: |
            echo "The value of 'VAR1' is $(VAR1)"
            echo "And this is the value of 'PATH1': $(PATH1)"
            
            cp $(MODEL_REPO)/$(MODEL1) .
            
            $(LAUNCHER) $(CODE) -in $(MODEL1) -out $(OUTPUTNAME)
            
          procs: 1
          nodes: 1
          walltime: "00:01:00"
          
global.parameters:
    PARAM1:
        values: [1, 2, 3]
        label: PARAM1.%%
```

1. Build a label by substituting in the value of the `$(VAR2)` variable
2. Build a label by substituting in the label string of the `$(PARAM1)` parameter: happens at study/parameter expansion time

<!-- Use workspace rendering tool to demo this examples outputs? -->

<br/>

## Description: `description`
----

This section is meant primarily for documentation purposes, providing a general
overview of what this study is meant to achieve.  This is both an important part
of the provenance of the instantiated studies (via the workspace copy) and to
enhance the shareability of the study with other users.

**Key**       |   **Required?**  | **Type**  |  **Description**                                                    |
:-            |        :-:       |   :-:     |      :-                                                             |
`name`        |       Yes        |   str     | Name of the study that is easily identifiable/indicative of purpose |
`description` |       Yes        |   str     | A short overview/description of what this study intends to achieve  |

``` yaml
description:
    name: lulesh_sample1
    description: | 
      A sample LULESH study that downloads, builds, and runs a parameter study
      of varying problem sizes and iterations.

```

!!! note

    You can add other keys to this block for custom documentation.  Maestro
    currently only verifies the presence of the required set enumerated above.


<br/>

## Environment: `env`
----

The environment block is where items describing the study's environment are
defined. This includes static information that the study needs to know about
and dependencies that the workflow requires for execution.  This is a good
place for global parameters that aren't varying in each step.

!!! note

    This block isn't strictly required as a study may not depend on anything.


**Key/Subsection**            | **Description** |
:-                            | :-              |
[variables](#variables)       | Static values that are substituted into steps ahead of all other values |
[labels](#labels)             | Static values that can contain variables and parameters which, like variables, can be substituted into all steps |
[dependencies](#dependencies) | Items that must be "acquired" before the workflow can proceed |


### Variables: `variables`

Variables represent static, one-time substitutions into the steps that make a
study. Variables are great for encouraging consistency throughout a workflow,
and are useful for things like propagating fixed settings or setting control
logic flags. These are similar in concept to Unix environment variables, but are
more portable.

``` yaml
env:
  variables:
    VAR1: value1
    VAR2: value2
    OUTPUT_PATH: ./sample_output/lulesh
```

There are some special tokens/variables available in Maestro specifications, the first of which is shown above: `OUTPUT_PATH`.  This is a keyword variable that Maestro looks for in order to set a custom output path for concrete study instance workspaces.  These workspaces are usually timestamped folder names based on the [`name`](#description-description) in the description block, stored inside `OUTPUT_PATH`.  The `OUTPUT_PATH` can use relative pathing semantics, as shown above, where the `./` is starting from the same parent directory as the study specification is read from. 

!!! note
    
    If not specified `OUTPUT_PATH` is assumed to be the path where Maestro was launched from.
    
!!! note

    If the '-o' flag is specified for the run subcommand, `OUTPUT_PATH` will be taken from there and will not generate a timestamped path.


### Labels: `labels`

Labels are similar to variables, representing static, one-time substitutions into steps. The difference from variables is that they support variable and parameter substitution.  This functionality can be useful for enforcing fixed formatting on output files, or fixed formatting of components of steps.

``` yaml
env:
  labels:
    outfile: $(SIZE.label).$(ITERATIONS.label).log # (1)
    
...

global.parameters:
    SIZE:
        values: [10, 20, 30]
        label: SIZE.%%
    ITERATIONS:
        values: [100, 200, 300]
        label: ITERATIONS.%%

```

1. Dynamic label construction based on parameter values.  Each step/parameter combo will also have a corresponding label

<!-- NOTE: come up with some better examples of labels/variables? -->

### Dependencies: `dependencies`

Dependencies represent external artifacts that should be present before a workflow can run.  This includes things such as acquirable inputs from a directory or version control system/repository, e.g. input files for programs, code, data, etc...  They can be used in steps via Maestro's token syntax using each dependencies `name` key as the token name.  Labels and variables
can also be used in the definition of these dependencies, as shown in the example

There are currently two types of dependencies:

* `paths`: verifies the existence of the specified path before execution.  This is a list of (`-` prefixed) dictionaries of paths to acquire.  If a path's existence cannot be verified, then Maestro will throw an exception and halt the study launching process.

    | **Key** |   **Required?**  | **Type**  |  **Description**                                                           |
    |  :-     |        :-:       |   :-:     |      :-                                                                    |
    | `name`  |       Yes        |   str     | Unique name for the identifying/referring to the path dependency           |
    | `path`  |       Yes        |   str     | Path to acquire and make available for substitution into string data/steps |

    !!! info
        
        A path dependency will only check for the exact path that is specified.  Maestro will not attempt to verify any sub-paths or sub-directories underneath that path.

* `git`: clones the specified repository before excution of the study.  This is a list of (`-` prefixed) dictionaries of repositories to clone

    | **Key** |   **Required?**  | **Type**  |  **Description**                                                   |
    |  :-     |        :-:       |   :-:     |      :-                                                            |
    | `name`  |       Yes        |   str     | Unique name for the identifying/referring to repository dependency |
    | `path`  |       Yes        |   str     | Parent path in which to clone the repo to                          |
    | `url`   |       Yes        |   str     | Url/path to repo to clone                                          |
    | `tag`   |        No        |   str     | Optional git tag to checkout after cloning                         |

    <!-- NOTE: can using abs path enable clones shared across study instances instead of one clone per study? -->
    <!-- NOTE: add comments about permissions -> will maestro prompt for password for protected repo, or is ssh key the way to enable? -->
    <!-- NOTE: tag/add link to full example below for using tokens to refer to dependencies -->
    <!-- NOTE: update schema to enable the hash/branch features too -->
    
``` yaml
env:
  dependencies:
    git:
      - name: LULESH
        path: $(OUTPUT_PATH)
        url: https://github.com/LLNL/LULESH.git
```

The `git` type dependency will attempt to clone the specified remote repository, and on success continue onto the next step in the launch process; however, if the clone fails then the process will throw an exception without launching any part of the workflow. 


<br/>

## Batch: `batch`
----

The `batch` block is an optional block that enables specification of HPC scheduler information to enable writing steps that are decoupled from particular machines and thus more portable/reusable.  The base/general keys that show up in this block are shown below.  Each scheduler type may have some unique keys, and further discussion will be in <!-- NOTE: add link to hpc sections describing each scheduler -->

|  **Key**      |  **Required**  | **Type** | **Description** |
|    :-         |      :-:       |    :-:   |       :-        |
|  `type`       |      Yes        |   str    | Type of scheduler managing execution.  Currently one of: {`local`, `slurm`, `lsf`, `flux`} |
|  `shell`      |      No        |   str    | Optional absolute path to the shell to use for execution (e.g., `"/bin/bash"`). Note: On non-Linux systems, this path may differ or `/bin/bash` may not exist. |
| `bank` (1)        |      Yes       |   str    | Account to charge computing time to |
| `host`        |      Yes       |   str    | The name of the cluster to execute this study on |
| `queue` (2)       |      Yes       |   str    | Scheduler queue/partition to submit jobs (study steps) to |
| `nodes`       |      No        |   int    | Number of compute nodes to be reserved for jobs: note this is also a per step key |
| `reservation` |      No        |   str    | Optional reserved allocation to submit jobs to |
| `qos`         |      No        |   str    | Quality of service specification -> i.e. run in standby mode to use idle resources when user priority is low/job limits already reached |
| `gpus`        |      No        |   str    | Optional reservation of gpu resources for jobs |
| `procs`       |      No        |   int    | Optional number of tasks in batch allocations: note this is also a per step key |
| `flux_uri`    |      Yes*      |   str    | Uri of flux instance to schedule jobs to: only required with `type`=`flux` |
| `version`     |      No        |   str    | Optional version of flux scheduler; for accomodating api changes |
| `args`        |      No        |   dict   | Optional additional args to pass to scheduler; keys are arg names, values are arg values |


=== "Slurm"
    ``` yaml
    batch:
        type        : slurm
        host        : quartz
        bank        : baasic
        queue       : pbatch
        reservation : test_reservation
    ```
    
=== "Flux"
    ``` yaml
    batch:
        type        : flux
        host        : quartz
        bank        : baasic
        queue       : pbatch
        flux_uri    : ƒ8RmSm8mYW3 # optional sample flux job id based uri; uri can take other forms too
    ```

=== "LSF"
    ``` yaml
    batch:
        type        : lsf
        host        : lassen
        bank        : baasic
        queue       : pdebug
    ```

<!-- NOTE: flux lulesh sample is missing the supposedly required uri key -->


<br/>

!!! note "Flux behaviors"

    1.  Flux brokers may not always have a bank, in which case this will have no effect
    2.  Flux brokers may not always have named queues (nested allocations).
	
	See [queues and banks](how_to_guides/running_with_flux.md#queues-and-banks) section in the how-to guide on running with flux for more discussion.

## Study: `study`
----

The `study` block is where the steps to be executed in the Maestro study are defined.  This section represents the unexpanded set of tasks that the study is composed of.  Here, unexpanded means no parameter substitution; the steps only contain references to the parameters.  Steps are given as a list (`-` prefixed) dictionaries of keys:

|  **Key**       |  **Required?** | **Type** | **Description**                                               |
|    :-          |       :-:      |   :-:    |       :-:                                                     |
|  `name`        |       Yes      |   str    | Unique name for identifying and referring to a task           |
|  `description` |       Yes      |   str    | A general description of what this step is intended to do     |
|  `run`         |       Yes      |   dict   | Properties that describe the actual specification of the task |


!!! note

    Unlike the previous blocks, almost every key in the study section can accept parameter tokens.  The primary benefit
    of this is in the resource specification keys, allowing easy parameterization of numbers of tasks, cores, nodes,
    walltime, etc on a per step basis.


### `run`:
----

The `run` key contains several other keys that define what a task does and how it relates to other tasks.  This is where you define the concrete shell commands the task needs to execute, any `parameter` or `env` tokens to inject, and step/task dependencies that dictate the topology of the study task graph.

|  **Key**       |  **Required?** | **Type** | **Description**                                               |
|    :-          |       :-:      |   :-:    |       :-                                                      |
|  `cmd`         |       Yes      |   str    | The actual task (shell commands) to be executed           |
|  `depends`     |       Yes      |   list   | List of other tasks which must successfully execute before this task can be executed |
|  `restart`     |       No       |   str    | Similar to `cmd`, providing optional alternate commands to run upon restarting, e.g. after a scheduler timeout |

There are also a number of optional keys for describing resource requirements to pass to the scheduler and associated `$(LAUNCHER)` tokens used to execute applications on HPC systems.  Presence of the `nodes` and/or `procs` keys have particular importance here: they tell Maestro that this step needs to be scheduled and not run locally on login nodes.

|  **Key**       |  **Required?** | **Type** | **Description**                                               |
|    :-          |       :-:      |   :-:    |       :-                                                      |
|  `nodes`       |       No       |   str    | Number of nodes to reserve for executing this task            |
|  `procs`       |       No       |   str    | Number of processors needed for task execution: primarily used by `$(LAUNCHER)` expansion |
|  `walltime`    |       No       |   str    | Specifies maximum amount of time to reserve HPC resources for |
|  `reservation` |       No       |   str    | Reservation to schedule this step to; overrides batch block |
|  `qos`         |       No       |   str    | Quality of service options for this step; overrides batch block |


<!-- NOTE: how to transition this into the scheduler specifics?  enumerate everything here even scheduler specific ones? -->
<!--       may want references to how-to guide here for the numerous parallel run modes/options users can invoke -->

Additionally there are more fine grained resource/scheduler control enabled by the various schedulers.

!!! note

    The remaining keys have been gradually appended and thus are not uniform across schedulers.
    Version 2.0 of the study specification will be refactoring these into a uniform/portable set.
    Full documentation/explanation of the resource keys can be seen in the scheduler specific
    sections: [Local](../scheduling/#local), [SLURM](../scheduling/#slurm), [Flux](../scheduling/#flux), [LSF](../scheduling/#lsf)


The following keys are all optional and get into scheduler specific features.  See the respective sections
before using them: 

|  **Key**         | **Type**     | **Description**                                               |
|    :-            |   :-:        |       :-                                                      |
| `cores per task` |   str/int    | Number of cores to use for each task        |
|  `exclusive`     |   str        | Flag for ensuring batch job has exclusive access to it's requested resources |
|  `gpus`          |   str/int    | Number of gpus to allocate with this step |
|  `tasks per rs`  |   str/int    | Number of tasks per resource set (LSF/jsrun) |
|  `rs per node`   |   str/int    | Number of resource sets per node |
|  `cpus per rs`   |   str/int    | Number of cpus in each resource set |
|  `bind`          |   str        | Controls binding of tasks in resource sets |
|  `bind gpus`     |   str        | Controls binding of gpus in resource sets |


## Parameters: `global.parameters`
----

The `global.parameters` block of the specification contains all of the things that you are going to vary in the
study; this is where we setup the parameter tokens and values that get substituted into the study steps.  This
block is optional, and when present the defined study steps get expanded into one concrete instance per parameter
combination specified in this block. These parameter combinations are defined as a set of keys that are the
parameter names (for use in steps via the `$(PARAM)` token syntax), and then dictionaries defining the list of
values in each parameter combination and a format string for constructing labels from those values.

Parameter keys:

|  **Key**  | **Required?** |  **Type**  |  **Description** |
|    :-     |      :-:      |     :-:    |     :-           |
|  `values` |      Yes      |    list    |  List of values in each parameter combination used to expand the study |
|  `label`  |      Yes      |    str     |  Format string for constructing labels from the values list |


In the example below we are generating three parameters with the tokens `$(TRIAL)`, `$(SIZE)`, and `$(ITERATIONS)`
that can reference them in study steps and the environments' labels block.  We are also constructing 9 parameter
combinations, meaning that steps that use these variables will have 9 instances, one for each parameter combination.

The label format syntax is currently limited to simple `str(param)` type formatting that injects the string form of
the parameter values in place of the `%%` placeholder, with the parameter name prefix here being a user settable
string.  For `TRIAL`, the paramters block below will create the following labels: `TRIAL.1, TRIAL.2, TRIAL.3, 
TRIAL.4, TRIAL.5, TRIAL.6, TRIAL.7, TRIAL.8, TRIAL.9`.  These labels get used in naming of the directories created
for each steps' outputs as well as in the logging.

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

For more programmatic creation of these parameter combinations, see the section on the `pgen` functionality <!-- ADD LINK -->.  This alternate mode acts like an override of the `global.parameters` block and is injected at run time rather
than being baked into the study specification.

## Full Example
----

Finally, we can pull all of this together into a complete example.  This and other versions of the lulesh study
specification and other problems can be found in the samples directory in the repo: [samples](https://github.com/LLNL/maestrowf/tree/develop/samples)

=== "Local"

    ``` yaml title="lulesh_sample1_unix.yaml"
    --8<-- "samples/lulesh/lulesh_sample1_unix.yaml"
    
    ```
    
=== "Slurm"

    ``` yaml title="lulesh_sample1_unix_slurm.yaml"
    --8<-- "samples/lulesh/lulesh_sample1_unix_slurm.yaml"
    
    ```
    
=== "LSF"

    ``` yaml title="lulesh_sample1_unix_lsf.yaml"
    --8<-- "samples/lulesh/lulesh_sample1_unix_lsf.yaml"
    
    ```
    
=== "Flux"

    ``` yaml title="lulesh_sample1_unix_flux.yaml"
    --8<-- "samples/lulesh/lulesh_sample1_unix_flux.yaml"
    
    ```
