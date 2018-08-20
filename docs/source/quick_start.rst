Quick Start Guide
==================

If you haven't already done so, see installation instructions in :doc:`Getting Started <./getting_started>`. For this guide, you will need to checkout `Maestro via GitHub <https://github.com/LLNL/maestrowf>`_ in order to use the provided samples.

Running the LULESH Study
*************************

This section will take you through the basics of using Maestro to launch a study locally. If you're looking for a more detailed breakdown of the LULESH study, skip to the :doc:`LULESH Specification Breakdown <./lulesh_breakdown>`.

`LULESH <https://github.com/LLNL/LULESH>`_ (Livermore Unstructured Lagrangian Explicit Shock Hydrodynamics) is a proxy application developed and open sourced by Lawrence Livermore National Laboratory. The application is capable of being compiled for both serial and distributed execution and provides a simple stand-in for an actual simulation code.

The LULESH study comes in two flavors: one for Unix systems and one for MacOSX systems. Both specifications are just about identical save for minor differences in ``sed`` commands. Simply pick the version for your system. In order to execute the LULESH sample study, execute the following command using Maestro from the root of the repository (using the Unix version as an example)::

    $ maestro run ./samples/lulesh/lulesh_sample1_unix.yaml -o ./tests/lulesh

.. note:: The ``-o`` flag is used for specifying a custom output path. Normally, Maestro creates a timestamped folder each time it is executed. The use of the ``-o`` is used here for consistency with provided logging.

Maestro begins by loading the specification and checks out a copy of LULESH from GitHub::

    2018-08-07 00:58:56,887 - maestrowf.maestro:setup_logging:360 - INFO - INFO Logging Level -- Enabled
    2018-08-07 00:58:56,887 - maestrowf.maestro:setup_logging:361 - WARNING - WARNING Logging Level -- Enabled
    2018-08-07 00:58:56,887 - maestrowf.maestro:setup_logging:362 - CRITICAL - CRITICAL Logging Level -- Enabled
    2018-08-07 00:58:56,887 - maestrowf.datastructures.core.study:__init__:195 - INFO - OUTPUT_PATH = /home/travis/build/LLNL/maestrowf/testing/lulesh
    2018-08-07 00:58:56,887 - maestrowf.datastructures.core.study:add_step:298 - INFO - Adding step 'make-lulesh' to study 'lulesh_sample1'...
    2018-08-07 00:58:56,888 - maestrowf.datastructures.core.study:add_step:298 - INFO - Adding step 'run-lulesh' to study 'lulesh_sample1'...
    2018-08-07 00:58:56,888 - maestrowf.datastructures.core.study:add_step:307 - INFO - run-lulesh is dependent on make-lulesh. Creating edge (make-lulesh, run-lulesh)...
    2018-08-07 00:58:56,888 - maestrowf.datastructures.core.study:add_step:298 - INFO - Adding step 'post-process-lulesh' to study 'lulesh_sample1'...
    2018-08-07 00:58:56,888 - maestrowf.datastructures.core.study:add_step:307 - INFO - post-process-lulesh is dependent on run-lulesh_*. Creating edge (run-lulesh_*, post-process-lulesh)...
    2018-08-07 00:58:56,889 - maestrowf.datastructures.core.study:add_step:298 - INFO - Adding step 'post-process-lulesh-trials' to study 'lulesh_sample1'...
    2018-08-07 00:58:56,889 - maestrowf.datastructures.core.study:add_step:307 - INFO - post-process-lulesh-trials is dependent on run-lulesh_*. Creating edge (run-lulesh_*, post-process-lulesh-trials)...
    2018-08-07 00:58:56,889 - maestrowf.datastructures.core.study:add_step:298 - INFO - Adding step 'post-process-lulesh-size' to study 'lulesh_sample1'...
    2018-08-07 00:58:56,889 - maestrowf.datastructures.core.study:add_step:307 - INFO - post-process-lulesh-size is dependent on run-lulesh_*. Creating edge (run-lulesh_*, post-process-lulesh-size)...
    2018-08-07 00:58:56,890 - maestrowf.datastructures.core.study:setup_workspace:337 - INFO - Setting up study workspace in '/home/travis/build/LLNL/maestrowf/testing/lulesh'
    2018-08-07 00:58:56,890 - maestrowf.datastructures.core.study:setup_environment:347 - INFO - Environment is setting up.
    2018-08-07 00:58:56,890 - maestrowf.datastructures.core.studyenvironment:acquire_environment:191 - INFO - Acquiring dependencies
    2018-08-07 00:58:56,890 - maestrowf.datastructures.core.studyenvironment:acquire_environment:193 - INFO - Acquiring -- LULESH
    2018-08-07 00:58:56,890 - maestrowf.datastructures.environment.gitdependency:acquire:150 - INFO - Cloning LULESH from https://github.com/LLNL/LULESH.git...
    Cloning into '/home/travis/build/LLNL/maestrowf/testing/lulesh/LULESH'...
    remote: Counting objects: 64, done.
    remote: Compressing objects: 100% (40/40), done.
    remote: Total 64 (delta 10), reused 43 (delta 6), pack-reused 16
    Unpacking objects: 100% (64/64), done.
    2018-08-07 00:58:57,306 - maestrowf.datastructures.core.study:configure_study:382 - INFO -
    ------------------------------------------
    Output path =               /home/travis/build/LLNL/maestrowf/testing/lulesh
    Submission attempts =       1
    Submission restart limit =  1
    Submission throttle limit = 0
    Use temporary directory =   False
    ------------------------------------------
    2018-08-07 00:58:57,307 - maestrowf.datastructures.core.executiongraph:__init__:337 - INFO -
    ------------------------------------------
    Submission attempts =       1
    Submission throttle limit = 0
    Use temporary directory =   False
    Tmp Dir =
    ------------------------------------------

Once set up is complete, Maestro will begin expanding the `Study` graph into an ``ExecutionGraph``. The ``ExecutionGraph`` represents the complete execution plan for a study. The snippets below show some of the expected output which will be a mix of single steps and parameterized steps.

Singular steps (such as "make-lulesh") appear in the log as follows::

   2018-08-07 00:58:57,307 - maestrowf.datastructures.core.study:_stage_parameterized:431 - INFO -
    ==================================================
    Processing step 'make-lulesh'
    ==================================================
    2018-08-07 00:58:57,308 - maestrowf.datastructures.core.study:_stage_parameterized:503 - INFO -
    -------------------------------------------------
    Adding step 'make-lulesh' (No parameters used)
    -------------------------------------------------
    2018-08-07 00:58:57,308 - maestrowf.datastructures.core.study:_stage_parameterized:518 - INFO - Searching for workspaces...
    cmd = cd /home/travis/build/LLNL/maestrowf/testing/lulesh/LULESH
    sed -i 's/^CXX = $(MPICXX)/CXX = $(SERCXX)/' ./Makefile
    sed -i 's/^CXXFLAGS = -g -O3 -fopenmp/#CXXFLAGS = -g -O3 -fopenmp/' ./Makefile
    sed -i 's/^#LDFLAGS = -g -O3/LDFLAGS = -g -O3/' ./Makefile
    sed -i 's/^LDFLAGS = -g -O3 -fopenmp/#LDFLAGS = -g -O3 -fopenmp/' ./Makefile
    sed -i 's/^#CXXFLAGS = -g -O3 -I/CXXFLAGS = -g -O3 -I/' ./Makefile
    make clean
    make

Parameterized steps (such as "run-lulesh") appear by printing out their expansion such as in the snippet below. Each combination is printed as it is expanded, for each combination in the ``global.parameters`` section of the study based on the parameters the given step uses::

    2018-08-07 00:58:57,308 - maestrowf.datastructures.core.study:_stage_parameterized:431 - INFO -
    ==================================================
    Processing step 'run-lulesh'
    ==================================================
    2018-08-07 00:58:57,308 - maestrowf.datastructures.core.study:_stage_parameterized:571 - INFO -
    ==================================================
    Expanding step 'run-lulesh'
    ==================================================
    -------- Used Parameters --------
    set(['SIZE', 'ITERATIONS'])
    ---------------------------------
    2018-08-07 00:58:57,308 - maestrowf.datastructures.core.study:_stage_parameterized:578 - INFO -
    **********************************
    Combo [SIZE.10.TRIAL.1.ITER.10]
    **********************************
    2018-08-07 00:58:57,309 - maestrowf.datastructures.core.study:_stage_parameterized:599 - INFO - Searching for workspaces...
    cmd = /home/travis/build/LLNL/maestrowf/testing/lulesh/LULESH/lulesh2.0 -s 10 -i 10 -p > SIZE.10.ITER.10.log
    2018-08-07 00:58:57,309 - maestrowf.datastructures.core.study:_stage_parameterized:630 - INFO - New cmd = /home/travis/build/LLNL/maestrowf/testing/lulesh/LULESH/lulesh2.0 -s 10 -i 10 -p > SIZE.10.ITER.10.log
    2018-08-07 00:58:57,309 - maestrowf.datastructures.core.study:_stage_parameterized:640 - INFO - Processing regular dependencies.
    2018-08-07 00:58:57,309 - maestrowf.datastructures.core.study:_stage_parameterized:648 - INFO - Adding edge (make-lulesh, run-lulesh_ITER.10.SIZE.10)...
    2018-08-07 00:58:57,309 - maestrowf.datastructures.core.study:_stage_parameterized:578 - INFO -
    **********************************
    Combo [SIZE.10.TRIAL.2.ITER.20]
    **********************************
    2018-08-07 00:58:57,309 - maestrowf.datastructures.core.study:_stage_parameterized:599 - INFO - Searching for workspaces...
    cmd = /home/travis/build/LLNL/maestrowf/testing/lulesh/LULESH/lulesh2.0 -s 10 -i 20 -p > SIZE.10.ITER.20.log
    2018-08-07 00:58:57,309 - maestrowf.datastructures.core.study:_stage_parameterized:630 - INFO - New cmd = /home/travis/build/LLNL/maestrowf/testing/lulesh/LULESH/lulesh2.0 -s 10 -i 20 -p > SIZE.10.ITER.20.log
    2018-08-07 00:58:57,309 - maestrowf.datastructures.core.study:_stage_parameterized:640 - INFO - Processing regular dependencies.
    2018-08-07 00:58:57,310 - maestrowf.datastructures.core.study:_stage_parameterized:648 - INFO - Adding edge (make-lulesh, run-lulesh_ITER.20.SIZE.10)...

Once expansion is complete, Maestro will prompt you to confirm if you'd like to launch the study. Simply confirm with a `y` and hit enter.::

    $ Would you like to launch the study? [yn] y

Maestro will launch a conductor in the background using ``nohup`` in order to monitor the executing study.


Monitoring a Running Study
***************************

Once the conductor is spun up, you will be returned to the command line prompt. There should now be a ``.tests/lulesh`` directory within the root of the repository. This directory represents the executing study's workspace, or where Maestro will place this study's data, logs, and state. For a more in-depth description of the contents of a workspace see the documentation about :doc:`Study Workspaces <./maestro_core>`.

In order to check the status of a running study, use the ``maestro status`` subcommand. The only required parameter to the status command is the path to the running study's workspace. In this case, to find the status of the running study (from the root of the repository) is::

    $ maestro status ./tests/lulesh

The resulting output will look something like below::

    Step Name                           Workspace            State        Run Time        Elapsed Time    Start Time                  Submit Time                 End Time                      Number Restarts
    ----------------------------------  -------------------  -----------  --------------  --------------  --------------------------  --------------------------  --------------------------  -----------------
    run-lulesh_ITER.20.SIZE.20          ITER.20.SIZE.20      FINISHED     0:00:00.226297  0:00:00.226320  2018-08-07 12:54:23.233567  2018-08-07 12:54:23.233544  2018-08-07 12:54:23.459864                  0
    post-process-lulesh                 post-process-lulesh  INITIALIZED  --:--:--        --:--:--        --                          --                          --                                          0
    post-process-lulesh-trials_TRIAL.9  TRIAL.9              INITIALIZED  --:--:--        --:--:--        --                          --                          --                                          0
    post-process-lulesh-trials_TRIAL.8  TRIAL.8              INITIALIZED  --:--:--        --:--:--        --                          --                          --                                          0
    post-process-lulesh-size_SIZE.10    SIZE.10              INITIALIZED  --:--:--        --:--:--        --                          --                          --                                          0
    post-process-lulesh-trials_TRIAL.1  TRIAL.1              INITIALIZED  --:--:--        --:--:--        --                          --                          --                                          0
    post-process-lulesh-trials_TRIAL.3  TRIAL.3              INITIALIZED  --:--:--        --:--:--        --                          --                          --                                          0
    post-process-lulesh-trials_TRIAL.2  TRIAL.2              INITIALIZED  --:--:--        --:--:--        --                          --                          --                                          0
    post-process-lulesh-trials_TRIAL.5  TRIAL.5              INITIALIZED  --:--:--        --:--:--        --                          --                          --                                          0
    post-process-lulesh-trials_TRIAL.4  TRIAL.4              INITIALIZED  --:--:--        --:--:--        --                          --                          --                                          0
    post-process-lulesh-trials_TRIAL.7  TRIAL.7              INITIALIZED  --:--:--        --:--:--        --                          --                          --                                          0
    post-process-lulesh-trials_TRIAL.6  TRIAL.6              INITIALIZED  --:--:--        --:--:--        --                          --                          --                                          0
    run-lulesh_ITER.30.SIZE.20          ITER.30.SIZE.20      FINISHED     0:00:00.543726  0:00:00.543743  2018-08-07 12:54:23.469009  2018-08-07 12:54:23.468992  2018-08-07 12:54:24.012735                  0
    run-lulesh_ITER.10.SIZE.20          ITER.10.SIZE.20      FINISHED     0:00:00.148773  0:00:00.148794  2018-08-07 12:54:23.068119  2018-08-07 12:54:23.068098  2018-08-07 12:54:23.216892                  0
    post-process-lulesh-size_SIZE.30    SIZE.30              INITIALIZED  --:--:--        --:--:--        --                          --                          --                                          0
    run-lulesh_ITER.20.SIZE.30          ITER.20.SIZE.30      FINISHED     0:00:01.066736  0:00:01.066757  2018-08-07 12:54:24.892856  2018-08-07 12:54:24.892835  2018-08-07 12:54:25.959592                  0
    run-lulesh_ITER.30.SIZE.10          ITER.30.SIZE.10      FINISHED     0:00:00.054475  0:00:00.054488  2018-08-07 12:54:23.005877  2018-08-07 12:54:23.005864  2018-08-07 12:54:23.060352                  0
    make-lulesh                         make-lulesh          FINISHED     0:00:05.416096  0:00:05.416109  2018-08-07 12:53:17.395362  2018-08-07 12:53:17.395349  2018-08-07 12:53:22.811458                  0
    run-lulesh_ITER.10.SIZE.10          ITER.10.SIZE.10      FINISHED     0:00:00.043584  0:00:00.043610  2018-08-07 12:54:22.905328  2018-08-07 12:54:22.905302  2018-08-07 12:54:22.948912                  0
    run-lulesh_ITER.20.SIZE.10          ITER.20.SIZE.10      FINISHED     0:00:00.035449  0:00:00.035463  2018-08-07 12:54:22.958755  2018-08-07 12:54:22.958741  2018-08-07 12:54:22.994204                  0
    run-lulesh_ITER.10.SIZE.30          ITER.10.SIZE.30      FINISHED     0:00:00.812721  0:00:00.812764  2018-08-07 12:54:24.069466  2018-08-07 12:54:24.069423  2018-08-07 12:54:24.882187                  0
    post-process-lulesh-size_SIZE.20    SIZE.20              INITIALIZED  --:--:--        --:--:--        --                          --                          --                                          0
    run-lulesh_ITER.30.SIZE.30          ITER.30.SIZE.30      FINISHED     0:00:01.376227  0:00:01.376240  2018-08-07 12:54:25.968730  2018-08-07 12:54:25.968717  2018-08-07 12:54:27.344957                  0


The general statuses that are usually encountered are:

    - ``INITIALIZED``: A step that has been generated and is awaiting execution.
    - ``RUNNING``: A step that is currently in progress.
    - ``FINISHED``: A step that has completed successfully.
    - ``FAILED``: A step that during execution encountered a non-zero error code.

Cancelling a Running Study
***************************

Similar to checking the status of a running study, cancelling a study uses the ``maestro cancel`` subcommand with the only required parameter being the path to the study workspace. In the case of the LULESH study, cancel the study using the following command from the root of the repository::

    $ maestro cancel ./tests/lulesh

.. note:: Cancelling a study is not instantaneous. The background conductor is a daemon which spins up periodically, so cancellation occurs the next time the conductor returns from sleeping and sees that a cancel has been triggered.

When a study is cancelled, the cancellation is reflected in the status when calling the ``maestro status`` command::

    Step Name                           Workspace            State      Run Time        Elapsed Time    Start Time                  Submit Time                 End Time                      Number Restarts
    ----------------------------------  -------------------  ---------  --------------  --------------  --------------------------  --------------------------  --------------------------  -----------------
    run-lulesh_ITER.20.SIZE.20          ITER.20.SIZE.20      FINISHED   0:00:00.238367  0:00:00.238549  2018-08-07 17:24:04.178433  2018-08-07 17:24:04.178251  2018-08-07 17:24:04.416800                  0
    post-process-lulesh                 post-process-lulesh  CANCELLED  --:--:--        --:--:--        --                          --                          2018-08-07 17:25:06.813454                  0
    post-process-lulesh-trials_TRIAL.9  TRIAL.9              CANCELLED  --:--:--        --:--:--        --                          --                          2018-08-07 17:25:06.813207                  0
    post-process-lulesh-trials_TRIAL.8  TRIAL.8              CANCELLED  --:--:--        --:--:--        --                          --                          2018-08-07 17:25:06.812957                  0
    post-process-lulesh-size_SIZE.10    SIZE.10              CANCELLED  --:--:--        --:--:--        --                          --                          2018-08-07 17:25:06.809833                  0
    post-process-lulesh-trials_TRIAL.1  TRIAL.1              CANCELLED  --:--:--        --:--:--        --                          --                          2018-08-07 17:25:06.810962                  0
    post-process-lulesh-trials_TRIAL.3  TRIAL.3              CANCELLED  --:--:--        --:--:--        --                          --                          2018-08-07 17:25:06.811659                  0
    post-process-lulesh-trials_TRIAL.2  TRIAL.2              CANCELLED  --:--:--        --:--:--        --                          --                          2018-08-07 17:25:06.811368                  0
    post-process-lulesh-trials_TRIAL.5  TRIAL.5              CANCELLED  --:--:--        --:--:--        --                          --                          2018-08-07 17:25:06.812205                  0
    post-process-lulesh-trials_TRIAL.4  TRIAL.4              CANCELLED  --:--:--        --:--:--        --                          --                          2018-08-07 17:25:06.811927                  0
    post-process-lulesh-trials_TRIAL.7  TRIAL.7              CANCELLED  --:--:--        --:--:--        --                          --                          2018-08-07 17:25:06.812708                  0
    post-process-lulesh-trials_TRIAL.6  TRIAL.6              CANCELLED  --:--:--        --:--:--        --                          --                          2018-08-07 17:25:06.812458                  0
    run-lulesh_ITER.30.SIZE.20          ITER.30.SIZE.20      FINISHED   0:00:00.324670  0:00:00.324849  2018-08-07 17:24:04.425894  2018-08-07 17:24:04.425715  2018-08-07 17:24:04.750564                  0
    run-lulesh_ITER.10.SIZE.20          ITER.10.SIZE.20      FINISHED   0:00:00.134795  0:00:00.135016  2018-08-07 17:24:04.032750  2018-08-07 17:24:04.032529  2018-08-07 17:24:04.167545                  0
    post-process-lulesh-size_SIZE.30    SIZE.30              CANCELLED  --:--:--        --:--:--        --                          --                          2018-08-07 17:25:06.810583                  0
    run-lulesh_ITER.20.SIZE.30          ITER.20.SIZE.30      FINISHED   0:00:00.678922  0:00:00.679114  2018-08-07 17:24:05.129377  2018-08-07 17:24:05.129185  2018-08-07 17:24:05.808299                  0
    run-lulesh_ITER.30.SIZE.10          ITER.30.SIZE.10      FINISHED   0:00:00.048609  0:00:00.048803  2018-08-07 17:24:03.974073  2018-08-07 17:24:03.973879  2018-08-07 17:24:04.022682                  0
    make-lulesh                         make-lulesh          FINISHED   0:00:04.979883  0:00:04.980055  2018-08-07 17:22:58.735953  2018-08-07 17:22:58.735781  2018-08-07 17:23:03.715836                  0
    run-lulesh_ITER.10.SIZE.10          ITER.10.SIZE.10      FINISHED   0:00:00.045598  0:00:00.045783  2018-08-07 17:24:03.853461  2018-08-07 17:24:03.853276  2018-08-07 17:24:03.899059                  0
    run-lulesh_ITER.20.SIZE.10          ITER.20.SIZE.10      FINISHED   0:00:00.044422  0:00:00.044655  2018-08-07 17:24:03.912904  2018-08-07 17:24:03.912671  2018-08-07 17:24:03.957326                  0
    run-lulesh_ITER.10.SIZE.30          ITER.10.SIZE.30      FINISHED   0:00:00.359750  0:00:00.359921  2018-08-07 17:24:04.760954  2018-08-07 17:24:04.760783  2018-08-07 17:24:05.120704                  0
    post-process-lulesh-size_SIZE.20    SIZE.20              CANCELLED  --:--:--        --:--:--        --                          --                          2018-08-07 17:25:06.810216                  0
    run-lulesh_ITER.30.SIZE.30          ITER.30.SIZE.30      FINISHED   0:00:00.915474  0:00:00.915682  2018-08-07 17:24:05.818191  2018-08-07 17:24:05.817983  2018-08-07 17:24:06.733665                  0
