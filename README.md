# Maestro Workflow Conductor (MaestroWF)
[![PyPI](https://img.shields.io/pypi/v/maestrowf.svg)](https://pypi.python.org/pypi?name=maestrowf&version=1.0.0&:action=display)
[![Issues](https://img.shields.io/github/issues/LLNL/maestrowf.svg)](https://github.com/LLNL/maestrowf/issues)
[![Forks](https://img.shields.io/github/forks/LLNL/maestrowf.svg)](https://github.com/LLNL/maestrowf/network)
[![Stars](https://img.shields.io/github/stars/LLNL/maestrowf.svg)](https://github.com/LLNL/maestrowf/stargazers)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://raw.githubusercontent.com/LLNL/maestrowf/master/LICENSE)

## Introduction

Maestro Workflow Conductor is a Python tool and library for specifying and automating multi-step computational workflows both locally and on supercomputers. Maestro parses a human-readable YAML specification that is self-documenting and portable from one user and environment to another.

On the backend, Maestro implements a set of standard interfaces and data structures for handling "study" construction. These objects offer you the ability to use Maestro as a library, and construct your own workflows that suit your own custom needs. We also offer other structures that make portable execution on various schedulers much easier than porting scripts by hand.

### Core Concepts

There are many definitions of workflow, so we try to keep it simple and define the term as follows:
```
A set of high level tasks to be executed in some order, with or without dependencies on each other.
```

We have designed Maestro around the core concept of what we call a "study". A study is defined as a set of steps that are executed (a workflow) over a set of parameters. A study in Maestro's context is analogous to an actual tangible scientific experiment, which has a set of clearly defined and repeatable steps which are repeated over multiple specimen.

Maestro's core tenets are defined as follows:

##### Repeatability
A study should be easily repeatable. Like any well-planned and implemented science experiment, the steps themselves should be executed the exact same way each time a study is run over each set of parameters or over different runs of the study itself.

##### Consistent
Studies should be consistently documented and able to be run in a consistent fashion. The removal of variation in the process means less mistakes when executing studies, ease of picking up studies created by others, and uniformity in defining new studies.

##### Self-documenting
Documentation is important in computational studies as much as it is in physical science. The YAML specification defined by Maestro provides a few required key encouraging human-readable documentation. Even further, the specification itself is a documentation of a complete workflow.

----------------

## Getting Started

To get started, we recommend using virtual environments. If you do not have the
Python virtual environment package and wrapper installed follow this [guide](http://python-guide-pt-br.readthedocs.io/en/latest/dev/virtualenvs/).

### Environment Setup
If you do not have or use virtualenvwrapper:

    $ python -m virtualenv venv
    $ source venv/bin/activate
Otherwise:

    $ mkvirtualenv venv


Once set up, test the environment. The paths should point to a virtual environment folder.

    $ which python
    $ which pip

### Installation

For general installation, you can install MaestroWF using the following:

    $ pip install maestrowf

If you plan to develop on MaestroWF, install the repository directly using:

    $ pip install -r requirements.txt
    $ pip install -e .

----------------

### Quickstart Example

MaestroWF comes packed with a basic example using LULESH, a proxy application provided by LLNL. You can find the Quick Start guide [here](https://maestrowf.readthedocs.io/en/latest/quick_start.html#).

----------------

## Contributors
Many thanks go to MaestroWF's [contributors](https://github.com/LLNL/maestrowf/graphs/contributors).

If you have any questions or to submit feature requests please [open a ticket](https://github.com/llnl/maestrowf/issues).

----------------

## Release
MaestroWF is released under an MIT license.  For more details see the
NOTICE and LICENSE files.

``LLNL-CODE-734340``
