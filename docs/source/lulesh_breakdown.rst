LULESH Specification Breakdown
===============================

Stub

Vanilla Unix/Linux Specification
++++++++++++++++++++++++++++++++

Stub

Parallel Specifications
+++++++++++++++++++++++

The next three variants of the Lulesh example make changes to enable running the steps
on HPC clusters using a variety of schedulers, as well as invoking the various parallel
options in Lulesh itself (MPI, OpenMP, ...).

Slurm Scheduled
---------------

Stub

Flux Scheduled
--------------

Stub

LSF Scheduled Parallel Specification
------------------------------------

This example is configured for running on LLNL's IBM/nVidia HPC machines which use the
LSF job scheduler to manage compute resources.  Due to variations in system setups this
may not work on all LSF installations and may require some tweaking to account for the
differences.  As with the other parallel specifications, adjust the machine name, bank,
and queue's to suit the system you run this spec on.


First change, the batch block to use the LSF scheduler to get appropriate batch submission
and parallel command injection working:

.. literalinclude:: ../../samples/lulesh/lulesh_sample1_unix_lsf.yaml
   :language: yaml
   :lines: 18-22
   :emphasize-lines: 2

We'll briefly skip ahead to the parameters block as there's multiple different parameters
used to specify all three modes of running.  ``TASKS`` specifies the mpi tasks, while
``CPUS_PER_TASK`` captures the openmp threads inside each task.  These can be nested
but here we are only showing the pure-mpi and pure-openmp modes of Lulesh:

.. literalinclude:: ../../samples/lulesh/lulesh_sample1_unix_lsf.yaml
   :language: yaml
   :lines: 80-99
   :emphasize-lines: 10-12, 14-16
                     

There are a few differences in the first step to deal with the llnl system where we are
using the lmod setup to select the mpi and compiler installs to use.  In
addition, we see the resource keys which have a few differences owing to the
way LSF describes resources using resource sets (rs).  In this step it's not very important
yet as the compilation doesn't need to run in parallel.  Note the depends is empty as
this is the first step that needs to run and has no dependencies.

.. literalinclude:: ../../samples/lulesh/lulesh_sample1_unix_lsf.yaml
   :language: yaml
   :lines: 25-48
   :emphasize-lines: 5-11, 18-24           


The run step gets a little more interesting now that we are mixing serial, mpi parallel, and
openmp parallel modes in a single step.  The biggest difference here is that some of the
resource parameters get used in the step to set the environment variables needed to control
the OpenMP thread counts using the ``$(CPUS_PER_TASK)`` Maestro parameter.

.. literalinclude:: ../../samples/lulesh/lulesh_sample1_unix_lsf.yaml
   :language: yaml
   :lines: 51-77
   :emphasize-lines: 16-18, 21-27

And finally, we have the complete specification here

.. literalinclude:: ../../samples/lulesh/lulesh_sample1_unix_lsf.yaml
   :language: yaml
