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

This page will break down the keys available in each section and what they provide.


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

<!-- NOTE: how to transition this into the scheduler specifics?  enumerate everything here even scheduler specific ones? -->
<!--       may want references to how-to guide here for the numerous parallel run modes/options users can invoke -->


<br/>

## `study`
----

The `metadata` section contains informatation that can be used to identify a study
and provide a user information about the intent of the study, who created the study,
and other high level information. Required and best practice keys are as follows:

**Key**       | **Required?** | **Type**        | **Description** |
     :-:      |      :-:      |    :-:          | :-          |
`name`        |      Yes      |    str          | Name of the study that is easily identifiable |
`description` |      Yes      |    str          | A short overview/sentence about what the study intends to achieve |


``` yaml
study:
  name: study_name
  description: A sample block for the metadata study block.
  project: Maestro
  team:
    Francesco Di Natale:
      email: frank.dinatale1988@gmail.com
      github: frankd412
      roles:
        - author
        - maintainer
```

<br/>

## `environment`
----

The `environment` section of a specification is where a user defines fixed values and other items that are expected to be present as prerequisites to executing a study's workflow. The subsections of the `environment` are as follows:

|     **Subsection**           | **Description** |
|          :-:                 | :-              |
|[variables](#variables)       | Static values that are substituted into steps ahead of all other values |
|[dependencies](#dependencies) | Items that must be "acquired" before the workflow can proceed |


### Study Keywords

Maestro has a number of keywords that

### `variables`

Variables represent static, one time, substitutions into the steps that make a workflow. Variables are great for encouraging consistency throughout a workflow, and are useful for things like propagating fixed settings or setting control logic flags. Variables most often contain strings or integers set to fixed values; however, it is possible to have a variable refer to another variable. Maestro will attempt to resolve the value, raising an exception if the value cannot be resolved after a maximum number of recursive attempts at substitutions.

``` yaml
environment:
  variables:
    VAR1: value1
    VAR2: value2
    VAR3: $[VAR1]/$[VAR2]
    VAR4: $[VAR1]_$[PARAM1]
```

!!! note
    `$[PARAM1]` is representative of a parameter, which we will discuss [below](#parameters). Maestro will always substitute/resolve variables first; they are the most static entities in a study, representing generally fixed values. Any parameters that are found in variables are ignored and simply substituted later in the study expansion phase.

### `dependencies`

Maestro supports a number of dependencies that can be acquired or checked before execution of a workflow, allowing a workflow to be aborted if its fundamental dependencies are not met. All dependencies are defined under the `environment` sub-section `dependencies` as follows, where `DEPEND1` and `DEPEND2` take the form of one of the types of dependencies below:

``` yaml
environment:
  dependencies:
    DEPEND1:
      ...

    DEPEND2:
      ...
```

<br/>

#### Paths

Paths are used to define external paths outside of a study. Maestro will run a basic existence check to verify that the specified path is accessible and throw an exception otherwise.

``` yaml
PATH1:
  type: path
  path: /filesystem/path/to/directory/or/file
```

The path definition above specifies `PATH1` as a path dependency using the `type: path` key. When the monikor `$[PATH1]` is used in workflow steps, `/filesystem/path/to/directory/or/file` will automatically be substituted.

!!! info
    A path dependency will only check for the path that has been specified. This is useful for directories that contain large sets of reference inputs; however, Maestro will not be able to verify any sub-paths or subdirectories.

<br/>

#### Git

Git dependencies are used to clone remotely hosted items to located at the URL specified by the `url` key to be stored at the location specified by `path`. There are a few optional keys:

| **Key** | **Description** |
|   :-:   | :-              |
|  `branch` | A valid branch name of the repository to checkout after cloning |
|   `tag`   | A valid tag that's been marked in the remote repository         |
|  `commit` | A specific commit hash to check out once the repository is cloned |

You specify the various `git` type dependency as follows:

=== "Latest Main Branch"
    ``` yaml
    REPO1:
      type: git
      url:  git@github.com:org/repo.git
      path: $[OUTPUT_PATH]
    ```

=== "Custom Branch"
    ``` yaml
    REPO1:
      type: git
      url:  git@github.com:org/repo.git
      path: $[OUTPUT_PATH]
      branch: branch_name
    ```

=== "Tagged Version"
    ``` yaml
    REPO1:
      type: git
      url:  git@github.com:org/repo.git
      path: $[OUTPUT_PATH]
      tag: tag_name
    ```

=== "Commit Hash"
    ``` yaml
    REPO1:
      type: git
      url:  git@github.com:org/repo.git
      path: $[OUTPUT_PATH]
      commit: commit_hash
    ```

!!! note
    The `branch`, `tag`, and `commit` options are mutually exclusive options -- only one of the keys can be specified at a time.

The `git` type dependency will attempt to clone the specified remote repository, and on success continue onto the next step in the launch process; however, if the clone fails then the process will throw an exception without launching any part of the workflow. In order to refer to the cloned repository in the workflow, use the specified key (in the YAML above `$[REPO1]`).

<br/>

#### Binaries

Binaries are at their core similar to the [path](#paths) dependency, except for one subtle difference; they can be used to force the study to use a specific version of a binary. The  `binary` dependency adds two (mutually exclusive) keys that can provide either an md5 hash of a binary or a version number alongside the path. Before execution the study's workflow, Maestro will perform one of the following depending what option is specified:

- Perform an md5hash of the binary at the specified path and compare to the one documented, throwing an exception if the hash does not match the specification.
- Call the binary with the `-v` option and regex match for the specified version number, throwing an exception if the version obtained does not match the specification.

Just as you would refer to a `path` or `git` dependency, you refer to a `binary` type dependency by using the `BIN1` key by the moniker `$[BIN1]`.
You specify a `binary` dependency as follows:

=== "Versioned Binary"
    ``` yaml
    BIN1:
      type:    binary
      path:    /path/to/binary/executable
      version: 0.0.0
    ```

=== "Hashed Binary"
    ``` yaml
    BIN1:
      type:    binary
      path:    /path/to/binary/executable
      md5hash: md5hash
    ```

<br/>

#### File Lists

The `filelist` dependency is another extension of the `path` type dependency that allows for the specification of a set of files. Each file's existence will be checked, and if any one of the specified paths does not exist, then an exception is thrown.

``` yaml
FILELIST:
  type: filelist
  paths:
    FILE1: /path/to/file/1
    FILE2: /path/to/file/2
```

You can reference individual files within the workflow by calling the moniker `$[FILELIST](FILE1)` (or any other defined file in the list).

<br/>

#### Registering Dependencies

To register dependencies ahead of time, see our [documentation](./index.md#env) on the `env` sub-comamnd.

## `workflow`


```yaml
workflow:
  step1:
    decription: A short description of what this workflow step is intended to accomplish
    execution:
      command: |
        echo "starting workflow step..." > output.log
        sleep 10m
        echo "ending workflow step..." >> output.log
      data:
        - output.log
      depends: []
    iterations: 1
    scheduler:
      type: slurm
      queue: batch
      bank: science
    resources:
      nodes: 1
      cores: 1
      cores per task: 1
      tasks: 1
      bank: bank1
      host: host1
      walltime:
        hours: 1
        minutes: 0
        seconds: 0
```

<br/>

## `parameters`
----
stub


<br/>

## Putting it all together
----

``` yaml
study:
  name: lulesh_proxy_test
  description: A simple specification for building and running a paremeter sweep of LULESH.
  project: Maestro
  team:
    Francesco Di Natale:
      email: frank.dinatale1988@gmail.com
      github: frankd412
      roles:
        - author
        - maintainer

environment:
  OUTPUT_PATH: ./sample_output/lulesh

  variables:
    OUTFILE: $[SIZE.label].$[ITERATIONS.label].log

  dependencies:
      LULESH:
        type: git
        url: $(OUTPUT_PATH)
        branch: https://github.com/LLNL/LULESH.git

workflow:
  make_lulesh:
    description: Build the MPI enabled version of LULESH.
    execution:
      command: |
        cd $(LULESH)
        mkdir build
        cd build
        cmake -WITH_MPI=Off -WITH_OPENMP=Off ..
        make
      data:
        in: []
        out: []
      depends: []

  run_lulesh:
    description: Run a parameterized instance of LULESH.
    execution:
      command: |
        $[LULESH]/build/lulesh2.0 -s $[SIZE] -i $[ITERATIONS] -p > $[OUTFILE]
      data:
        in: [$[LULESH]/build/lulesh2.0]
        out: []
      depends: [make_lulesh]

parameters:
  SIZE:
    values: [100, 200, 300]
    type: x-product
    label: SIZE.%%
  ITERATIONS:
    values: [ 10, 20, 30 ]
    type: x-product
    label: ITER.%%
```
