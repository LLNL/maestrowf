# Study Specification

The study specification is the main definition of work and is the main record of
a user specified workflow. A complete specification is made up of the following
components:

**Key**       |  **Required?** | **Description** |
    :-:       |   :-:          |  :-             |
[`description`](#description)        | Yes | General information about a study and its high-level purpose |
[`batch`](#batch) | No | Settings for submission to batch systems |
[`env`](#environment)  | No  | Fixed constants and other values that a globally set and referenced |
[`study`](#workflow)        | Yes | Tasks that the study is composed of and are executed in a defined order |
[`global.parameters`](#parameters)    | No  | Parameters that are user varied and applied to the workflow |

This page will break down the keys available in each section and what they provide.

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
