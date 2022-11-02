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

Maestro takes a minimalist approach to it's workflow language features that are available in the study specification.  All of this is contained in the token replacement hooks available in the [`study`](#workflow) and [`env`](#environment) blocks.  These tokens are referenced using the `$(TOKEN_NAME)` syntax, with the `$( )` encapsulating this minimal dsl.  First, a few special tokens that are always available:

 **Name** |  **Description**  |  **Notes**  |
  :- |      :-           |     :-      |
`$(SPECROOT)`              | This defines the pase path of the study specification | This provides a portable relative path to use with associated dependencies and supporting scripts/tools |
 `$(OUTPUT_PATH)`           | This is the path to the current study instance | OUTPUT_PATH can be specified in the env block's `variables` group providing a way to group the timestamped instance directories instead of polluting the $(SPECROOT) path |
 `$(LAUNCHER)`              | Abstracts HPC scheduler specific job launching wrappers such as srun (SLURM) | Primary mechanism for making study steps system agnostic and portable |
 `$(WORKSPACE)`             | Can be used in a step to reference the current step path | |
| <span style="white-space:nowrap;">`$(<step_name>.workspace)`</span> | Can be used in a step to reference path to other previous step workspaces | `<step-name>` is the `name` key in each study step |

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
    outfile: $(SIZE.label).$(ITERATIONS.label).log

```

<!-- NOTE: come up with some better examples of labels/variables? -->

### Dependencies: `dependencies`

Dependencies represent external artifacts that should be present before a workflow can run.  This includes things such as acquirable inputs from a directory or version control system/repository, e.g. input files for programs, code, data, etc...  They can be used in steps via Maestro's token syntax using each dependencies `name` key as the token name.  Labels and variables
can also be used in the definition of these dependencies, as shown in the example

There are currently two types of dependencies:

* `path`: verifies the existence of the specified path before execution.  This is a list of (`-` prefixed) dictionaries of paths to acquire.  If a path's existence cannot be verified, then Maestro will throw an exception and halt the study launching process.

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
|  `shell`      |      No        |   str    | Optional specification path to shell to use for execution.  Defaults to `"/bin/bash"` |
| `bank`        |      Yes       |   str    | Account to charge computing time to |
| `host`        |      Yes       |   str    | The name of the cluster to execute this study on |
| `queue`       |      Yes       |   str    | Scheduler queue/partition to submit jobs (study steps) to |
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
        flux_uri    : <!-- WHAT DOES THIS LOOK LIKE? -->
    ```

<!-- NOTE: flux lulesh sample is missing the supposedly required uri key -->


<br/>

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
    --8<-- "../samples/lulesh/lulesh_sample1_unix.yaml"
    
    ```
    
=== "Slurm"

    ``` yaml title="lulesh_sample1_unix_slurm.yaml"
    --8<-- "../samples/lulesh/lulesh_sample1_unix_slurm.yaml"
    
    ```
    
=== "LSF"

    ``` yaml title="lulesh_sample1_unix_lsf.yaml"
    --8<-- "../samples/lulesh/lulesh_sample1_unix_lsf.yaml"
    
    ```
    
=== "Flux"

    ``` yaml title="lulesh_sample1_unix_flux.yaml"
    --8<-- "../samples/lulesh/lulesh_sample1_unix_flux.yaml"
    
    ```
