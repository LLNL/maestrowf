Getting Started
================

Maestro Docker Container
*********************

In order to set up the Docker container execute the following from the root of the Maestro repository::

    $ docker --build -t maestrowf .

To launch the interactive shell of the Ubuntu image simply run::

    $ docker run -it maestrowf

Once inside the Docker container, the following should bring up help::

    $ maestro -h

Installing MaestroWF
*********************

MaestroWF can be installed via pip outside of Docker with the following::

    $ pip install maestrowf

.. note:: Using a `virtualenv <https://virtualenv.pypa.io/en/stable/>`_ is recommended.

Once installed run::

    $ maestro -h

    usage: maestro [-h] [-l LOGPATH] [-d DEBUG_LVL] [-c] {cancel,run,status} ...

    The Maestro Workflow Conductor for specifiying, launching, and managing general workflows.

    positional arguments:
      {cancel,run,status}
        cancel              Cancel all running jobs.
        run                 Launch a study based on a specification
        status              Check the status of a running study.

    optional arguments:
      -h, --help            show this help message and exit
      -l LOGPATH, --logpath LOGPATH
                            Alternate path to store program logging.
      -d DEBUG_LVL, --debug_lvl DEBUG_LVL
                            Level of logging messages to be output:
                            5 - Critical
                            4 - Error
                            3 - Warning
                            2 - Info (Default)
                            1 - Debug
      -c, --logstdout       Log to stdout in addition to a file. [Default: True]
