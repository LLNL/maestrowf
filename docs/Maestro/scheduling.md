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
| `bank`        |      Yes       |   str    | Account which runs the job; this is used for computing job priority on the cluster. '--account' on slurm, '-G' on lsf, ...|
| `host`        |      Yes       |   str    | The name of the cluster to execute this study on |
| `queue`       |      Yes       |   str    | Scheduler queue/machine partition to submit jobs (study steps) to |
| `nodes`       |      No        |   int    | Number of compute nodes to be reserved for jobs: note this is also a per step key |
| `reservation` |      No        |   str    | Optional prereserved allocation/partition to submit jobs to |
| `qos`         |      No        |   str    | Quality of service specification -> i.e. run in standby mode to use idle resources when user priority is low/job limits already reached |
| `gpus`        |      No        |   str    | Optional reservation of gpu resources for jobs |
| `procs`       |      No        |   int    | Optional number of tasks in batch allocations: note this is also a per step key |
| `flux_uri`    |      Yes*      |   str    | Uri of flux instance to schedule jobs to. * only required with `type`=`flux` |
| `version`     |      No        |   str    | Optional version of flux scheduler; for accomodating api changes |
| `args`        |      No        |   dict   | Optional additional args to pass to scheduler; keys are arg names, values are arg values |


The information in this block is used to populate the step specific batch scripts with the appropriate
header comment blocks (e.g. '#SBATCH --partition' for slurm).  Additional keys such as step specific
resource requirements (number of nodes, cpus/tasks, gpus, ...) get added here when processing
individual steps; see subsequent sections for scheduler specific details.  Note that job steps will
run locally unless at least the ``nodes`` or ``procs`` key in the step is populated.  The keys attached to the study steps also get used to construct the parallel launcer (e.g. `srun` for [SLURM](#SLURM)).  The following subsections describe the options in the currently supported scheduler types.

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

    You do not need both 'n' and 'p' with this syntax.  You can also allocate soley based on tasks (p) or nodes (n).

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

The Flux scheduler uses the command [`flux mini run`](https://flux-framework.readthedocs.io/projects/flux-core/en/latest/man1/flux-mini.html) to launch and allocate resources to tasks.  Maestro provides keys for a subset of arguments to this command along with hooks for passing a comma separated list of additional arguments

|  **Flux**  |  **Maestro**  |  **Description**  |  **Default**  |
|    :-      |      :-       |        :-         |      :-       |
| `-n`       |    `procs`    |  Number of MPI tasks to allocate for the launched application |  `1`  |
| `-N`       |    `nodes`    |  Number of nodes to allocate for the launched application |  `1`  |
| `-c`       |   `cores per task` |  Number of physical CPU cores per task  |  `1`  |
| `-g`       |  `gpus`       | Number of gpus to allocate per task |  `0`  |
| `-o`       |           |  Comma separated list of additional args  | `None` |

!!! danger

   Flux examples are still under construction
   
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
LLNL Sierra architechture which has 44 cores and 4 gpus per node:


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
