## What is Maestro?

Maestro is an open-source HPC software tool that defines a YAML-based study specification for defining multistep workflows and automates execution of software flows on HPC resources. The core design tenants of Maestro focus on encouraging clear workflow communication and documentation, while making consistent execution easier to allow users to focus on science. Maestro's study specification helps users think about complex workflows in a step-wise, intent-oriented, manner that encourages modularity and tool reuse. These principles are becoming increasingly important as computational science is continuously more present in scientific fields and has started to require a similar rigor to physical experiment. Maestro is currently in use for multiple projects at Lawrence Livermore National Laboratory and has been used to run existing codes including MFEM, and other simulation codes. It has also been used in other areas including in the training of machine-learned models and more.

----------------

## An Example Study using LULESH

Maestro comes packed with a basic example using [LULESH](https://github.com/LLNL/LULESH), a proxy application provided by LLNL. You can find the example [here](https://maestrowf.readthedocs.io/en/latest/quick_start.html#).


## Contributors

Many thanks go to MaestroWF's [contributors](https://github.com/LLNL/maestrowf/graphs/contributors).

If you have any questions or to submit feature requests please [open a ticket](https://github.com/llnl/maestrowf/issues).

----------------

## Release
MaestroWF is released under an MIT license.  For more details see the
NOTICE and LICENSE files.

``LLNL-CODE-734340``
