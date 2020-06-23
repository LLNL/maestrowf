.. SimMananger documentation master file, created by
   sphinx-quickstart on Fri Jan 13 12:44:04 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Maestro Workflow Conductor Documentation
===================================================

Maestro is an open-source HPC software tool that defines a YAML-based study
specification for defining multi-step workflows and automates execution of
software flows on HPC resources. The core design tenants of Maestro focus on
encouraging clear workflow communication and documentation, while making
consistent execution easier to allow users to focus on science.

Maestro's study specification helps users think about complex workflows in a
step-wise, intent-oriented, manner that encourages modularity and tool reuse.
Maestro’s development centers around a user-centric design approach and makes
use of software design practices such as abstract interfacing and utilizing
design patterns, forming the foundation of a vision for enabling a layered
architecture to workflow tool design.

These principles are becoming increasingly important as computational science
is continuously more present in scientific fields and users continue to perform
increasingly complex workflow processes across platforms.

Getting Started is Quick and Easy
==================================

Create a ``YAML`` file named ``study.yaml`` and paste the following content
into the file:

.. code:: yaml

    description:
        name: hello_world
        description: A simple 'Hello World' study.

    study:
        - name: say-hello
          description: Say hello to the world!
          run:
              cmd: |
                echo "Hello, World!" > hello_world.txt

.. note::

    `PHILOSOPHY`: Maestro believes in the principle of a clearly defined process,
    specified as a list of tasks, that are self-documenting and clear in their
    intent.

Running the ``hello_world`` study is as simple as:

.. code:: bash

    maestro run study.yaml

Creating a Parameter Study is just as Easy
===========================================

With the addition of the ``global.parameters`` block, and a few simple tweaks
to your study block, the complete specification should look like this:

.. code:: bash

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

.. note::

    `PHILOSOPHY`: Maestro believes that a workflow should be easily parameterized
    with minimal modifications to the core process.

Maestro will automatically expand each parameter into its own isolated
workspace, generate a script for each parameter, and automatically monitor
execution of each task.

And, running the study is still as simple as:

.. code:: bash

    maestro run study.yaml

.. toctree::
   :maxdepth: 4
   :caption: Contents:

   getting_started
   quick_start
   hello_world
   lulesh_breakdown
   parameters
   maestro_core

   modules

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
