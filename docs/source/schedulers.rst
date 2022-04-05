Scheduling Studies (a.k.a. the Batch Block)
===========================================

The batch block is an optional component of the workflow specification that enables
job submission and management on remote clusters.  The block contains a handful of
keys for specifying system level information that's applicable to all scheduled
steps:

.. list-table:: Batch block keys

   * - Key
     - Description
   * - type
     - Select scheduler adapter to use. Currently supported are ``slurm``, ``lsf``, and
       ``flux``, ``local``.  Default is ``local``, non-scheduled job steps.
   * - host
     - Name of cluster being run on
   * - queue
     - Machine partition to schedule jobs to.  '--partition' for slurm systems, '-q' for
       lsf systems, ...
   * - bank
     - Account which runs the job; this is used for computing job priority on the cluster.
       '--account' on slurm, '-G' on lsf, ...
   * - reservation
     - Name of any prereserved machine partition to submit jobs to
   * - qos
     - Optional quality of service options (slurm only)
   * - flux_uri
     - Flux specific reservation functionality

The information in this block is used to populate the step specific batch scripts with the appropriate
header comment blocks (e.g. '#SBATCH --partition' for slurm).  Additional keys such as step specific
resource requirements (number of nodes, cpus/tasks, gpus, ...) get added here when processing
individual steps; see subsequent sections for scheduler specific details.  Note that job steps will
run locally unless at least the ``nodes`` or ``procs`` key in the step is populated.

LOCAL
*****

Stub

SLURM
*****

Stub

FLUX
****

Stub

LSF: a Tale of Two Launchers
****************************

The LSF scheduler has multiple options for the parallel launcher commands:

* `lsrun <https://www.ibm.com/docs/en/spectrum-lsf/10.1.0?topic=jobs-run-interactive-tasks>`_
* `jsrun <https://www.ibm.com/docs/en/spectrum-lsf/10.1.0?topic=SSWRJV_10.1.0/jsm/jsrun.html>`_

Maestro currently supports only the jsrun version, which differs from slurm
via a more flexible specification of resources available for each task.  In
addition to the `procs`, `cores per task`, and `gpu` keys, there are also
`tasks_per_rs` and `rs_per_node`.  `jsrun` describes things in terms of resource
sets, with several keywords controlling these resource sets and mapping them to
the actual machine/node allocations:

.. list-table:: Mapping of LSF args to Maestro step keys

   * - LSF (jsrun)
     - Maestro
     - Description
     - Default setting
   * - -n, --nrs
     - procs
     - number of resource sets
     - 1
   * - -a, --tasks_per_rs
     - tasks per rs
     - Number of MPI tasks (ranks) in a resource
     - 1
   * - -c, --cpu_per_rs
     - cores per task
     - Number of physical CPU cores in a resource set
     - 1
   * - -g, --gpu_per_rs
     - gpus
     - Number of GPU's per resource set
     - 0
   * - -b, --bind
     - bind
     - Controls binding of tasks in a resource set
     - 'rs'
   * - -B, --bind_gpus
     - bind gpus
     - Controls binding of tasks to GPU's in a resource set
     - 'none'
   * - -r, --rs_per_host
     - rs per node
     - Number of resource sets per node
     - 1
     

.. note::

   ``bind_gpus`` is new in lsf 10.1 and may not be available on all systems
   
Now for a few examples of how to map these to Maestro's resource specifications.
Note the `node` key is not directly used for any of these, but is still used for
the reservation itself.  The rest of the keys serve to control the per task resources
and then the per node packing of resource sets.  Consider a few examples:

* 1 resource set per gpu on a cluster with 4 gpus per node with an application requesting
  8 gpus.  This will consume 2 full nodes of the cluster with 1 MPI rank associated with
  each gpu and having 1 cpu each.

  .. code-block:: bash

     jsrun -nrs 8 -a 1 -c 1 -g 1 -r 4 --bind rs my_awesome_gpu_application

  And the corresponding maestro step that generates it

  .. code-block:: yaml

     study:
         - name: run-my-app
           description: launch the best gpu application.
           run:
             cmd: |
                 $(LAUNCHER) my_awesome_gpu_application

             procs: 8
             nodes: 2
             gpus:  1
             rs_per_node: 4
             tasks_per_rs: 1
             cores per task: 1
  
  Note that `procs` here maps more to the tasks/resource set concept in lsf/jsrun, and
  nodes is a multiplier on `rs_per_node` which yields the `nrs` jsrun key

* 1 resource set per cpu, with no gpus, and using all 44 cpus on the node

  .. code-block:: bash

     jsrun -nrs 44 -a 1 -c 1 -g 0 -r 44 --bind rs my_awesome_mpi_cpu_application

  .. code-block:: yaml

     study:
         - name: run-my-app
           description: launch a pure mpi-cpu application.
           run:
             cmd: |
                 $(LAUNCHER) my_awesome_mpi_cpu_application

             procs: 44
             nodes: 1
             gpus:  0
             rs_per_node: 44
             tasks_per_rs: 1
             cores per task: 1

     Again, note that `procs` is a multiple of `rs_per_node`.
  
* Several multithreaded mpi ranks per node, with no gpus

  .. code-block:: bash

     jsrun -nrs 4 -a 1 -c 11 -g 0 -r 4 --bind rs my_awesome_omp_mpi_cpu_application

  .. code-block:: yaml

     study:
         - name: run-my-app
           description: launch an application using mpi and omp
           run:
             cmd: |
                 $(LAUNCHER) my_awesome_omp_mpi_cpu_application

             procs: 4
             nodes: 1
             gpus:  0
             rs_per_node: 4
             tasks_per_rs: 1
             cores per task: 11

* Several multithreaded mpi ranks per node with one gpu per rank, spanning multiple
  nodes having 4 gpu's each

  .. code-block:: bash

     jsrun -nrs 8 -a 1 -c 11 -g 1 -r 4 --bind rs my_awesome_all_the_threads_application

  .. code-block:: yaml

     study:
         - name: run-my-app
           description: Use all the threads!
           run:
             cmd: |
                 $(LAUNCHER) my_awesome_all_the_threads_application

             procs: 8
             nodes: 2
             gpus:  1
             rs_per_node: 4
             tasks_per_rs: 1
             cores per task: 11


* An mpi application that needs lots of memory per rank

  .. code-block:: bash

     jsrun -nrs 2 -a 1 -c 1 -g 0 -r 1 --bind rs my_memory_hungry_application

  .. code-block:: yaml

     study:
         - name: run-my-app
           description: Use all the memory for single task per node
           run:
             cmd: |
                 $(LAUNCHER) my_memory_hungry_application

             procs: 2
             nodes: 2
             gpus:  0
             rs_per_node: 1
             tasks_per_rs: 1
             cores per task: 1
