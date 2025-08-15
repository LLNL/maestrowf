# Scheduling Studies (a.k.a. the Batch Block)
----

The batch block is an optional component of the workflow specification that enables
job submission and management on remote clusters.  The block contains a handful of
keys for specifying system level information that's applicable to all scheduled
steps:

<!-- There a way to add a title to a table? -->
**Batch block keys**

|  **Key**      | **Required?**  | **Type** | **Description** |
|    :-         |      :-:       |    :-:   |       :-        |
|  `type`       |      Yes        |   str    | Select scheduler adapter to use.  Currently supported are: {`local`, `slurm`, `lsf`, `flux`} |
|  `shell`      |      No        |   str    | Optional specification path to shell to use for execution.  Defaults to `"/bin/bash"` |
| `bank` (1)        |      Yes       |   str    | Account which runs the job; this is used for computing job priority on the cluster. '--account' on slurm, '-G' on lsf, ...|
| `host`        |      Yes       |   str    | The name of the cluster to execute this study on |
| `queue` (2)       |      Yes       |   str    | Scheduler queue/machine partition to submit jobs (study steps) to |
| `nodes`       |      No        |   int    | Number of compute nodes to be reserved for jobs: note this is also a per step key |
| `reservation` |      No        |   str    | Optional prereserved allocation/partition to submit jobs to |
| `qos`         |      No        |   str    | Quality of service specification -> i.e. run in standby mode to use idle resources when user priority is low/job limits already reached |
| `gpus`        |      No        |   str    | Optional reservation of gpu resources for jobs |
| `procs`       |      No        |   int    | Optional number of tasks in batch allocations: note this is also a per step key |
| `flux_uri`    |      Yes*      |   str    | URI of the Flux instance to schedule jobs to. * Only used with `type`=`flux`. NOTE: It is recommended to rely on environment variables instead, as URIs are very ephemeral and may change frequently.|
| `version`     |      No        |   str    | Optional version of flux scheduler; for accommodating api changes |
| :warning: `args`        |      No        |   dict   | Optional additional args to pass to scheduler; keys are arg names, values are arg values |
| `allocation_args` | No  | dict | Optional scheduler specific options/flags to add to allocations :material-information-slab-circle: flux only in :material-tag:`1.1.12` |
| `launcher_args` | No  | dict | Optional scheduler specific options/flags to add to launcher commands :material-information-slab-circle: flux only in :material-tag:`1.1.12` |

!!! warning "`args` deprecated"

    `args` has been marked deprecated in :material-tag: `1.1.12` in favor of the more flexible `allocation_args` and `launcher_args`

The information in this block is used to populate the step specific batch scripts with the appropriate
header comment blocks (e.g. '#SBATCH --partition' for slurm).  Additional keys such as step specific
resource requirements (number of nodes, cpus/tasks, gpus, ...) get added here when processing
individual steps; see subsequent sections for scheduler specific details.  Note that job steps will
run locally unless at least the ``nodes`` or ``procs`` key in the step is populated.  The keys attached to the study steps also get used to construct the parallel launcer (e.g. `srun` for [SLURM](#SLURM)).  The following subsections describe the options in the currently supported scheduler types.

!!! note "Flux behaviors"

    1.  Flux brokers may not always have a bank, in which case this will have no effect
    2.  Flux brokers may not always have named queues (nested allocations).
	
	See [queues and banks](how_to_guides/running_with_flux.md#queues-and-banks) section in the how-to guide on running with flux for more discussion.

### Extra Arguments
---

There are new groups in the batch block in :material-tag:`1.1.12` that facilitate adding custom options to both allocations and the `$(LAUNCHER)` invocations independently.  These are grouped into two dictionaries in the batch block which are meant to enable passing in options that Maestro cannot abstract across schedulers more generally:

* `allocation_args` for the allocation target (batch directives such as `#Flux: --setopt=foo=bar`)
* `launcher_args` for the `$(LAUNCHER)` target (`flux run --setopt=foo=bar`)

These are ~structured mappings which are designed to mimic cli usage for intuitive mapping from raw scheduler usage to Maestro.  Each of these dictionaries' keys correspond to a scheduler specific CLI argument/option or flag.  The serialization rules are as follows, with specific examples here shown for the initial implementation in the flux adapter (other schedulers will yield prefix/separator rules specific to their implementation):

|  **Key Type**   | **CLI Prefix** | **Separator** | **Example YAML**    | **Example CLI Output** |
|    :-           | :-:            |     :-:       |    :-:              |       :-               |
|  Single letter  |  `-`           | space (`" "`) | `o: {bar: 42}`      | `-o bar=42`            |
|  Multi-letter   | `--`           |  `=`          | `setopt: {foo: bar} | `--setopt=foo=bar`     |
|  Boolean flag w/key   | as above       | as above      | `setopt: {foobar: } | `--setopt=foobar`      |
|  Boolean flag w/o key   | as above       | as above      | `exclusive: ` | `--exclusive`      |

Note in the boolean flag strategies, a space is required after the `:` after `foobar: ` or `exclusive`, otherwise yaml will fail to parse and assign the Null value used to tag a key as a boolean flag.  See [flux](#Flux) for special considerations fo the `allocation_args`


## LAUNCHER Token
---

The `LAUNCHER` token is a special token that has two forms for use in place of explicit scheduler specific commands in your study steps such as `srun ...` and `flux mini run ...`.

### Legacy style

`$(LAUNCHER)`

The original style simply reads in the step keys such as `nodes` and `procs` (see scheduler specific sections for full list of options).  Maestro then combines the step and [`batch`](specification#batch-block) block configuration when writing the step scripts to generate the appropriate parallel launcher invocation for the system, e.g.

=== "Maestro Step"

    ``` yaml title="Sample legacy style Launcher step"
    - name: run-two-apps
      description: Run two parallel apps
      run:
          cmd: |
            $(LAUNCHER) par_app_1
            $(LAUNCHER) par_app_2
          nodes: 2
          procs: 72
          exclusive   : True
          walltime: "00:10:00"
    ```

=== "Slurm script"

    ``` yaml title="Slurm script from legacy style Launcher"
    #!/bin/bash
    
    #SBATCH --nodes=2
    #SBATCH --partition=pbatch
    #SBATCH --account=baasic
    #SBATCH --time=00:10:00
    #SBATCH --job-name=run-two-apps
    #SBATCH --output=run-two-apps.out
    #SBATCH --error=run-two-apps.err
    #SBATCH --comment "Run two parallel apps"
    #SBATCH --exclusive
    
    srun -N 2 -n 72 par_app_1
    srun -N 2 -n 72 par_app_2
    ```

### New style

`$(LAUNCHER)[<n>n, <p>p]`

This updated variant allows more granular control of the launcher token to allocate resources differently on a per executable/command basis inside of a step.

- `<n>`: command specific number of nodes.  Must be less than or equal to steps' `nodes` setting.
- `<p>`: command specific number of tasks/procs.  Must be less than or equal to steps' `procs` setting.

!!! note

    You do not need both 'n' and 'p' with this syntax.  You can also allocate solely based on tasks (p) or nodes (n).

=== "Maestro Step"

    ``` yaml title="Sample new style Launcher step"
    - name: run-two-apps
      description: Run two parallel apps using different resource configs
      run:
          cmd: |
            $(LAUNCHER)[1n, 36p] par_app_1
            $(LAUNCHER)[2n, 36p] par_app_2
          nodes: 2
          procs: 72
          exclusive   : True
          walltime: "00:10:00"
    ```

=== "Slurm script"

    ``` yaml title="Slurm script from new style Launcher"
    #!/bin/bash
    
    #SBATCH --nodes=2
    #SBATCH --partition=pbatch
    #SBATCH --account=baasic
    #SBATCH --time=00:10:00
    #SBATCH --job-name=run-two-apps
    #SBATCH --output=run-two-apps.out
    #SBATCH --error=run-two-apps.err
    #SBATCH --comment "Run two parallel apps using different resource configs"
    #SBATCH --exclusive
    
    srun -N 1 -n 36 par_app_1
    srun -N 2 -n 36 par_app_2
    ```

## LOCAL
----

The LOCAL scheduler gets run by conductor directly where it was launched.  All tasks are currently  run sequentially.  There are no batch block arguments for it, and running a study specification that doesn't contain a batch block will default to this scheduler.


## SLURM
----

The SLURM scheduler uses the [`srun`](https://slurm.schedmd.com/srun.html) command to launch and allocate resources to tasks.  Maestro currently supports the following subset of srun arguments:

|  **SLURM (srun)**  |  **Maestro**  | **Block** |  **Description**  |  **Default**  |
|        :-          |      :-       |   :-      |   :-              |      :-       |
|  `-n`              |     `procs`   |  step, batch | Number of MPI tasks to allocate for the launched application  |  `1`  |
|  `-N`              |     `nodes`   |  step, batch | Number of nodes to allocate for the launched application |  `1`  |
|  `-c`              |   `cores per task` |  step | Number of physical CPU cores per task |  `1`  |
|  `-t`, `--time`    |  `walltime` | step | Limit on total run time of the job | N/A: Machine/system dependent |
|  `--exclusive`     |  `exclusive` | step | Grant job allocation excluive use of resources.  Useful for running on processor scheduled machines <!-- link to recipe -->.  NOTE: this behavior depends on system config | `False` |
| 


## Flux
----

The Flux scheduler uses the command [`flux run`](https://flux-framework.readthedocs.io/projects/flux-core/en/latest/man1/flux-run.html) to launch and allocate resources to tasks.  For adapter versions < 0.49.0 this will actually be the  [`flux mini run`](https://flux-framework.readthedocs.io/projects/flux-core/en/latest/man1/flux-mini.html) command which was recently deprecated.  Maestro provides keys for a subset of arguments to this command along with hooks for passing a comma separated list of additional arguments

|  **Flux**  |  **Maestro**  |  **Description**  |  **Default**  |
|    :-      |      :-       |        :-         |      :-       |
| `-n`       |    `procs`    |  Number of MPI tasks to allocate for the launched application |  `1`  |
| `-N`       |    `nodes`    |  Number of nodes to allocate for the launched application |  `1`  |
| `-c`       |   `cores per task` |  Number of physical CPU cores per task  |  `1`  |
| `-g`       |  `gpus`       | Number of gpus to allocate per task |  `0`  |
| `-o`       |           |  Comma separated list of additional args  | `None` |

Flux adapter also supports some keys that control batch job behavior instead of getting passed to the `flux mini run` or `flux run` commands:

| **Maestro** | **Description** | **Default** |
| :-          | :-              | :-          |
| `nested`    | Flag to control whether to run the step inside a nested flux instance.  This is usually the desired option. | True |
| `waitable` | Whether to mark a job as 'waitable'; this is restricted to owners of an instance, and thus cannot be used if scheduling to a system instance (i.e. not to a broker with a specific uri). Note: this option is likely only of interest if using the script adapters directly to build a custom tool. New flag as of 0.49.0 adapter. Let us know via [github issues](https://github.com/LLNL/maestrowf/issues) if you find a need/use for this in the spec. | False |

See the [flux framework](https://flux-framework.readthedocs.io/en/latest/index.html) for more information on flux.  Additionally, checkout the [flux-how-to-guides](how_to_guides/running_with_flux.md) for the options available for using flux with Maestro.  Also check out a [full example spec run with flux](specification.md#full-example).

!!! note "Flux batch block behaviors"

    1.  Flux brokers may not always have a bank, in which case this will have no effect
    2.  Flux brokers may not always have named queues (nested allocations).
	
	See [queues and banks](how_to_guides/running_with_flux.md#queues-and-banks) section in the how-to guide on running with flux for more discussion.

!!! danger

    The Flux scheduler itself and Maestro's flux adapter are still in a state of flux and may go through breaking changes more frequently than the Slurm and LSF scheduler adapters.
   

### Extra Flux Args
----

As of :material-tag:`1.1.12`, the flux adapter takes advantage of new argument pass through for scheduler options that Maestro cannot abstract away.  This is done via `allocation_args` and `launcher_args` in the batch block, which expand upon the previous `args` input which only applied to `$(LAUNCHER)`.  There are some caveat's here due to the way Maestro talks to flux.  The current flux adapters all use the python api's from Flux to build the batch jobs, with the serialized batch script being serialized separately instead of submitted directly as with the other schedulers.  A consequence of this is the `allocation_args` map to specific call points on that python api, and thus the option pass through is not quite arbitrary.  There are 4 currently supported options for allocations which cover a majority of usecases (open an issue and let us know if one you need isn't covered!):

* shell options: `-o/--setopt` prefixed arguments
* attributes: `-S/--setattr` prefixed arguments
* conf: `--conf` prefixed arguments
* exclusive flags: `-x, --exclusive` are used to set defaults, with step exclusive keys overriding

!!! warning

    All other flags will be allowed in `allocation_args`, but they will essentially be ignored when serializing the step scripts and submitting jobs
	
The `launcher_args` (`$(LAUNCHER)`) will pass through anything as it is a string generator just like other script adapters.  :warning: These are not validated!  Passing arguments that flux doesn't know what to do with may result in errors.

#### Example Batch Block
---

``` yaml
batch:
  type: flux
  host: machineA
  bank: guests
  queue: debug
  allocation_args:
    setopt:
      foo: bar
    o:
      bar: 42
    setattr:
      foobar: "whoops"
    conf:
      resource.rediscover: "true"  # Use string "true" for Flux compatibility, not "True" or bool True
  launcher_args:
    setopt:
      optiona:   # Boolean flag, no value needed
```

#### Example Batch Script
---
Assuming the step has keys `{procs: 1, nodes: 1, cores per task: 1, walltime: "5:00"}`:

``` console
#flux: -q debug
#flux: --bank=guests
#flux: -t 300s
#flux: --setopt=foo=bar
#flux: -o bar=42
#flux: --setattr=foobar=whoops
#flux: --conf=resource.rediscover=true

flux run -n 1 -N 1 -c 1 --setopt=optiona  myapplication
```

!!! note

    Using flux directives here to illustrate even though python api is used.  These directives will be in the step scripts, retaining repeatability/record of what was submitted and viewable with the dry run feature
   
## LSF: a Tale of Two Launchers
----

The LSF scheduler has multiple options for the parallel launcher commands:

* [`lsrun`](https://www.ibm.com/docs/en/spectrum-lsf/10.1.0?topic=jobs-run-interactive-tasks)
* [`jsrun`](https://www.ibm.com/docs/en/spectrum-lsf/10.1.0?topic=SSWRJV_10.1.0/jsm/jsrun.html)

Maestro currently supports only the jsrun version, which differs from slurm
via a more flexible specification of resources available for each task.  In
addition to the `procs`, `cores per task`, and `gpu` keys, there are also
`tasks_per_rs` and `rs_per_node`.  `jsrun` describes things in terms of resource
sets, with several keywords controlling these resource sets and mapping them to
the actual machine/node allocations:

**Mapping of LSF args to Maestro step keys**

|  **LSF (jsrun)**       |  **Maestro**   | **Description**  |  **Default**  |
|  :-                    |      :-       |       :-        |      :-       |
| `-n`, `--nrs`          |    `procs`     | Number of resource sets |    `1`   |
| `-a`, `--tasks_per_rs` | `tasks per rs` | Number of MPI tasks (ranks) in a resource set |   `1`   | 
| `-c`, `--cpu_per_rs`   | `cores per task` | Number of physical CPU cores in a resource set |  `1`  |
| `-g`, `--gpu_per_rs`   | `gpus`           | Number of GPU's per resource set |  `0`  |
| `-b`, `--bind`         | `bind`           | Controls binding of tasks in a resource set | `rs` |
| `-B`, `--bind_gpus`    | `bind gpus`      | Controls binding of tasks to GPU's in a resource set | `none` |
| `-r`, `--rs_per_host`  | `rs per node`    | Number of resource sets per node | `1` |

!!! warning

    `bind_gpus` is new in lsf 10.1 and may not be available on all systems

## Examples
----

Now for a few examples of how to map these to Maestro's resource specifications.
Note the `node` key is not directly used for any of these, but is still used for
the reservation itself.  The rest of the keys serve to control the per task resources
and then the per node packing of resource sets.  Consider a few examples run on the
LLNL Sierra architecture which has 44 cores and 4 gpus per node:


### Multiple tasks with single cpu and gpu per task
----

1 resource set per gpu on a cluster with 4 gpus per node with an application requesting
8 gpus.  This will consume 2 full nodes of the cluster with 1 MPI rank associated with
each gpu and having 1 cpu each.

``` bash title="Bash command line"

jsrun -nrs 8 -a 1 -c 1 -g 1 -r 4 --bind rs my_awesome_gpu_application

```

And the corresponding maestro step that generates it

``` yaml title="Maestro yaml specification"

study:
    - name: run-my-app
      description: launch the best gpu application.
      run:
        cmd: |
            $(LAUNCHER) my_awesome_gpu_application

        procs: 8
        nodes: 2
        gpus:  1
        rs per node: 4
        tasks per rs: 1
        cores per task: 1
```

Note that `procs` here maps more to the tasks/resource set concept in lsf/jsrun, and
nodes is a multiplier on `rs_per_node` which yields the `nrs` jsrun key

### Multiple tasks with single cpu and no gpus per task
----
1 resource set per cpu, with no gpus, and using all 44 cpus on the node

``` bash title="Bash command line"

jsrun -nrs 44 -a 1 -c 1 -g 0 -r 44 --bind rs my_awesome_mpi_cpu_application

```

``` yaml title="Maestro yaml specification"

study:
    - name: run-my-app
      description: launch a pure mpi-cpu application.
      run:
        cmd: |
            $(LAUNCHER) my_awesome_mpi_cpu_application

        procs: 44
        nodes: 1
        gpus:  0
        rs per node: 44
        tasks per rs: 1
        cores per task: 1
```

Again, note that `procs` is a multiple of `rs_per_node`.
  
### Multiple multithreaded mpi ranks/tasks per node, with no gpus
----

``` bash title="Bash command line"

jsrun -nrs 4 -a 1 -c 11 -g 0 -r 4 --bind rs my_awesome_omp_mpi_cpu_application

```

``` yaml title="Maestro yaml specification"

study:
    - name: run-my-app
      description: launch an application using mpi and omp
      run:
        cmd: |
            $(LAUNCHER) my_awesome_omp_mpi_cpu_application

        procs: 4
        nodes: 1
        gpus:  0
        rs per node: 4
        tasks per rs: 1
        cores per task: 11
```

### Multiple multithreaded mpi ranks/tasks per node with one gpu per rank, spanning multiple nodes
----

``` bash title="Bash command line"

jsrun -nrs 8 -a 1 -c 11 -g 1 -r 4 --bind rs my_awesome_all_the_threads_application

```

``` yaml title="Maestro yaml specification"

study:
    - name: run-my-app
      description: Use all the threads!
      run:
        cmd: |
            $(LAUNCHER) my_awesome_all_the_threads_application

        procs: 8
        nodes: 2
        gpus:  1
        rs per node: 4
        tasks per rs: 1
        cores per task: 11

```


### An mpi application that needs lots of memory per rank
----

``` bash title="Bash command line"

jsrun -nrs 2 -a 1 -c 1 -g 0 -r 1 --bind rs my_memory_hungry_application

```

``` yaml title="Maestro yaml specification"

study:
    - name: run-my-app
      description: Use all the memory for single task per node
      run:
        cmd: |
            $(LAUNCHER) my_memory_hungry_application

        procs: 2
        nodes: 2
        gpus:  0
        rs per node: 1
        tasks per rs: 1
        cores per task: 1

```
