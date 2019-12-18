![](/assets/logo.png?raw=true "Orchestrate your workflows with ease!")

# Maestro Workflow Conductor ([maestrowf](https://pypi.org/project/maestrowf/))

[![Build Status](https://travis-ci.org/LLNL/maestrowf.svg?branch=develop)](https://travis-ci.org/LLNL/maestrowf)
[![PyPI](https://img.shields.io/pypi/v/maestrowf.svg)](https://pypi.python.org/pypi?name=maestrowf&version=1.0.0&:action=display)
![Spack](https://img.shields.io/spack/v/py-maestrowf)
[![Issues](https://img.shields.io/github/issues/LLNL/maestrowf.svg)](https://github.com/LLNL/maestrowf/issues)
[![Forks](https://img.shields.io/github/forks/LLNL/maestrowf.svg)](https://github.com/LLNL/maestrowf/network)
[![Stars](https://img.shields.io/github/stars/LLNL/maestrowf.svg)](https://github.com/LLNL/maestrowf/stargazers)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://raw.githubusercontent.com/LLNL/maestrowf/master/LICENSE)

[![Downloads](https://pepy.tech/badge/maestrowf)](https://pepy.tech/project/maestrowf)
[![Downloads](https://pepy.tech/badge/maestrowf/month)](https://pepy.tech/project/maestrowf/month)
[![Downloads](https://pepy.tech/badge/maestrowf/week)](https://pepy.tech/project/maestrowf/week)

Maestro can be installed via [pip](https://pip.pypa.io/):

    pip install maestrowf

## Getting Started is Quick and Easy

Create a `YAML` file named `study.yaml` and paste the following content into the file:

``` yaml
description:
    name: hello_world
    description: A simple 'Hello World' study.

study:
    - name: hello_world
      description: Say hello to the world!
      run:
          cmd: |
            echo "Hello, World!" > hello_world.txt
```

> *PHILOSOPHY*: Maestro believes in the principle of a clearly defined process, specified as a list of tasks, that are self-documenting and clear in their intent.

Running the `hello_world` study is as simple as...

    maestro run study.yaml

## Creating a Parameter Study is just as Easy

With the addition of the `global.parameters` block, and a few simple tweaks to your `study` block, the complete specification should look like this:

``` yaml
description:
    name: hello_planet
    description: A simple study to say hello to planets (and Pluto)

study:
    - name: hello_planet
      description: Say hello to a planet!
      run:
          cmd: |
            echo "Hello, $(PLANET)!" > hello_$(PLANET).txt

global.parameters:
    PLANET:
        values: [Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Pluto]
        label: PLANET.%%
```

> *PHILOSOPHY*: Maestro believes that a workflow should be easily parameterized with minimal modifications to the core process.

Maestro will automatically expand each parameter into its own isolated workspace, generate a script for each parameter, and automatically monitor execution of each task.

And, running the study is still as simple as:

``` bash
    maestro run study.yaml
```

## Scheduling Made Simple

But wait there's more! If you want to schedule a study, it's just as simple. With some minor modifications, you are able to run on an [HPC](https://en.wikipedia.org/wiki/Supercomputer) system.

``` yaml
description:
    name: hello_planet
    description: A simple study to say hello to planets (and Pluto)

batch:
    type:  slurm
    queue: pbatch
    host:  quartz
    bank:  science

study:
    - name: hello_planet
      description: Say hello to a planet!
      run:
          cmd: |
            echo "Hello, $(PLANET)!" > hello_$(PLANET).txt
          nodes: 1
          procs: 1
          walltime: "00:02:00"

global.parameters:
    PLANET:
        values: [Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Pluto]
        label: PLANET.%%
```

> **NOTE**: This specification is configured to run on LLNL's quartz cluster. Under the `batch` header, you will need to make the necessary changes to schedule onto other HPC resources.
>
> *PHILOSOPHY*: Maestro believes that how a workflow is defined should be decoupled from how it's run. We achieve this capability by providing a seamless interface to multiple schedulers that allows Maestro to readily port workflows to multiple platforms.

For other samples, see the [samples](/samples) subfolder. To continue with our Hello World example, see the [Basics of Study Construction](https://maestrowf.readthedocs.io/en/latest/hello_world.html) in our [documentation](https://maestrowf.readthedocs.io/en/latest/index.html).

## An Example Study using LULESH

Maestro comes packed with a basic example using [LULESH](https://github.com/LLNL/LULESH), a proxy application provided by LLNL. You can find the example [here](https://maestrowf.readthedocs.io/en/latest/quick_start.html#).

## What is Maestro?

Maestro Workflow Conductor is a Python tool and library for specifying and automating multi-step computational workflows both locally and on supercomputers. Maestro parses a human-readable YAML specification that is self-documenting and portable from one user and environment to another.

On the backend, Maestro implements a set of standard interfaces and data structures for handling "study" construction. These objects offer you the ability to use Maestro as a library, and construct your own workflows that suit your own custom needs. We also offer other structures that make portable execution on various schedulers much easier than porting scripts by hand.

### Maestro's Foundation and Core Concepts

There are many definitions of workflow, so we try to keep it simple and define the term as follows:

``` text
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

## Setting up your Python Environment

To get started, we recommend using virtual environments. If you do not have the
Python `virtualenv` package installed, take a look at their official [documentation](http://python-guide-pt-br.readthedocs.io/en/latest/dev/virtualenvs/) to get started.

To create a new virtual environment:

    python -m virtualenv maestro_venv
    source maestro_venv/bin/activate

### Getting Started for Contributors

If you plan to develop on Maestro, install the repository directly using:

    pip install -r requirements.txt
    pip install -e .

Once set up, test the environment. The paths should point to a virtual environment folder.

    which python
    which pip

## Contributors

Many thanks go to MaestroWF's [contributors](https://github.com/LLNL/maestrowf/graphs/contributors).

If you have any questions or to submit feature requests please [open a ticket](https://github.com/llnl/maestrowf/issues).

----------------

## Release
MaestroWF is released under an MIT license.  For more details see the
NOTICE and LICENSE files.

``LLNL-CODE-734340``
