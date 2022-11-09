![](https://github.com/LLNL/maestrowf/raw/develop/assets/logo.png?raw=true "Orchestrate your workflows with ease!")

# Maestro Workflow Conductor ([maestrowf](https://pypi.org/project/maestrowf/))

[![Build Status](https://travis-ci.org/LLNL/maestrowf.svg?branch=develop)](https://travis-ci.org/LLNL/maestrowf)
[![PyPI](https://img.shields.io/pypi/v/maestrowf.svg)](https://pypi.python.org/pypi?name=maestrowf&version=1.0.0&:action=display)
![Spack](https://img.shields.io/spack/v/py-maestrowf)
[![Issues](https://img.shields.io/github/issues/LLNL/maestrowf.svg)](https://github.com/LLNL/maestrowf/issues)
[![Forks](https://img.shields.io/github/forks/LLNL/maestrowf.svg)](https://github.com/LLNL/maestrowf/network)
[![Stars](https://img.shields.io/github/stars/LLNL/maestrowf.svg)](https://github.com/LLNL/maestrowf/stargazers)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://raw.githubusercontent.com/LLNL/maestrowf/master/LICENSE)

[![Downloads](https://static.pepy.tech/personalized-badge/maestrowf?period=total&units=international_system&left_color=grey&right_color=blue&left_text=Downloads)](https://pepy.tech/project/maestrowf)
[![Downloads](https://static.pepy.tech/personalized-badge/maestrowf?period=month&units=international_system&left_color=grey&right_color=blue&left_text=Downloads/Month)](https://pepy.tech/project/maestrowf)

Maestro can be installed via [pip](https://pip.pypa.io/):

    pip install maestrowf

## Documentation

* [Maestro Documentation](https://maestrowf.readthedocs.io) - Official Maestro documentation.
* [Maestro Sheetmusic](https://github.com/LLNL/maestro_sheetmusic) - A collection of sample and user contributed Maestro study examples.
* [Maestro Samples](/samples) - Maestro sample studies.

## Getting Started is Quick and Easy

Create a `YAML` file named `study.yaml` and paste the following content into the file:

``` yaml
description:
    name: hello_world
    description: A simple 'Hello World' study.

study:
    - name: say-hello
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
    - name: say-hello
      description: Say hello to a planet!
      run:
          cmd: |
            echo "Hello, $(PLANET)!" > hello_$(PLANET).txt

global.parameters:
    PLANET:
        values: [Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto]
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
    - name: say-hello
      description: Say hello to a planet!
      run:
          cmd: |
            echo "Hello, $(PLANET)!" > hello_$(PLANET).txt
          nodes: 1
          procs: 1
          walltime: "00:02:00"

global.parameters:
    PLANET:
        values: [Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto]
        label: PLANET.%%
```

> **NOTE**: This specification is configured to run on LLNL's quartz cluster. Under the `batch` header, you will need to make the necessary changes to schedule onto other HPC resources.
>
> *PHILOSOPHY*: Maestro believes that how a workflow is defined should be decoupled from how it's run. We achieve this capability by providing a seamless interface to multiple schedulers that allows Maestro to readily port workflows to multiple platforms.

For other samples, see the [samples](/samples) subfolder. To continue with our Hello World example, see the [Basics of Study Construction](https://maestrowf.readthedocs.io/en/latest/hello_world.html) in our [documentation](https://maestrowf.readthedocs.io/en/latest/index.html).
