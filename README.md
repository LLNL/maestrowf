# Maestro Workflow Conductor (MaestroWF)
[![PyPI](https://img.shields.io/pypi/v/maestrowf.svg)](https://pypi.python.org/pypi?name=maestrowf&version=1.0.0&:action=display)
[![Issues](https://img.shields.io/github/issues/LLNL/maestrowf.svg)](https://github.com/LLNL/maestrowf/issues)
[![Forks](https://img.shields.io/github/forks/LLNL/maestrowf.svg)](https://github.com/LLNL/maestrowf/network)
[![Stars](https://img.shields.io/github/stars/LLNL/maestrowf.svg)](https://github.com/LLNL/maestrowf/stargazers)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://raw.githubusercontent.com/LLNL/maestrowf/master/LICENSE)

A Python package that implements the workflow and run specification. The
package provides users with a generalized way to define a workflow, configure
parameters sweeps, and manage dependencies.

MaestroWF is designed with the following core principles in mind:

##### Reproducibility
All simulation studies should be easily reproducible with just a single (or
small set of) file(s). Person A should be able to hand off to Person B without
 large amounts of effort.

##### Repeatability
All simulation studies should be easily repeatable. That is to say, it is not
enough to reproduce old studies -- executing the same exact flow on new studies
is just as important and should be easy to achieve in a simple manner.

##### Self-Documentation

It is not enough that a workflow runs. Getting to results is just as important
 as how you get there. Even more important, documentation of how to execute
studies and what a workflow is doing at each step.

##### Consistency

Standard documentation and management of studies allows for an ecosystem to
 be built around a common infrastructure. This concept allows for new tools and
 services to be provided (in most cases) in a manner transparent to the end
 user. Even more so, consistency allows different users to communicate about
 a workflow using the same language and core concepts.

##### Dependency Management

 An expandable framework for pulling dependencies from a wide array of different
 sources. So long as a programming interface can be defined for acquiring a
 dependency it can be added and managed in a study.

----------------

## External Information and Documentation

We are actively collecting and documenting requirements and user stories. If
you'd like to contribute information about your own use cases and workflow
process, please see the links below. Generally, we separate requirements into
two categories: study and workflow definition, and simulation management.

External Location for requirements pending.**

##### Study and Workflow Definition

Anything related to describing the definition of the methodology and process.
These requirements currently directly refer to the YAML study specification,
which is a general way to describe workflow processes, their computing
environment, and the steps in the methodology for producing results.

##### Simulation Management

Functional requirements about what management capabilities the tool must be
able to perform. Capabilities such as automatic job tracking, job restarts, and
other functionality that a user would expect a backend system to handle without
user intervention.

----------------

## MaestroWF Core concepts

The foundations of the MaestroWF package are built on classes designed to
represent a few high level concepts which aim to have extremely clear APIs:
* A ```StudyEnvironment``` class that contains all data representing variables,
sourcing scripts, and dependencies that the Study requires to run.
* A ```ParameterGenerator``` class that contains all parameters, which
yields ```Combination``` objects that represent a valid combination of parameters
to be used in a single instance of a Study.
* A ```Study``` class (derived from a ```DAG```) which represents the high level
parameterized workflow and constructs the full study from parameters and
environment objects that it stores.

### Environment

The environment of a Study is represented by two classes: the ```StudyEnvionment```
and ```ParameterGenerator``` classes.

#### StudyEnvironment
The ```StudyEnvironment``` class stores all of the fundamental items a user
expects in the environment when executing a particular study. These items include:
* Variables
* Scripts
* Dependencies

Each of items stored within the ```StudyEnvironment``` is derived from the
appropriate abstract class with the appropriate interface. Each abstract type
requires a derived class know how to apply itself to the item being passed to it;
and if it must acquire some external item must provide the appropriate method to
do so. This design aims to make it so that a study is much easier to repeat (and
with metadata easy to reproduce).

#### ParameterGenerator
The goal of the ```ParameterGenerator``` class is to provide one centralized location
 for managing and storing parameters. The implementation of the ParameterGenerator,
 currently, is very basic. It takes lists of parameters and uses those to construct
 combinations. Essentially, if you were to view this as an Excel table, you would
 have a row for each valid combination you wanted to study.

The other goal is to make it so that by having the ParameterGenerator manage
parameters, functionality can be added without affecting how the end user interacts
with this class. The ParameterGenerator has an Iterator built in and will generate
each combination one by one. The end user should NEVER SEE AN INVALID COMBINATION.
Because this class generates the combinations as specified by the parameters added
(eventually with types or enforced inheritance), it opens up being able to quietly
change how this class generates its combinations. The iterable interface that the
end user sees will remain constant, allowing the internal workings of
the ```ParameterGenerator``` to remain abstracted.

### Study

The ```Study``` class is part of the meat and potatoes of this whole package. A
Study object is where the intersection of the major moving parts are
collected. These moving parts include:
- ParameterGenerator for getting combinations of user parameters
- StudyEnvironment for managing and applying the environment to studies
- Study flow, which is a DAG of the abstract workflow

The class is responsible for a number of the major key steps in study setup
as well. Those responsibilities include (but are not limited to):
- Setting up the workspace where a simulation campaign will be run.
- Applying the StudyEnvionment to the abstract flow DAG:
    - Creating the global workspace for a study.
    - Setting up the parameterized workspaces for each combination.
    - Acquiring dependencies as specified in the StudyEnvironment.
- Intelligently constructing the expanded ExecutionDAG to be able to:
    - Recognize when a step executes in a parameterized workspace
    - Recognize when a step executes in the global workspace
- Expanding the abstract flow to the full set of specified parameters.


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

If you plan to develop on MaestroWF, install the repository directly using:

    $ pip install -r requirements.txt
    $ pip install -e .

----------------

## Quickstart Example

MaestroWF comes packed with a basic example using LULESH, a proxy application provided
by LLNL. Information and source code for LULESH can be found [here](https://codesign.llnl.gov/lulesh.php).

The example performs the following workflow locally:
- Download LULESH from the webpage linked above and decompress it.
- Substitute all necessary variables with their serial compilers and make LULESH.
- Execute a small parameter sweep of varying size and iterations (a simple sensitivity study)

In order to execute the sample study simply execute from the root directory of the repository:

    $ maestro ./samples/lulesh/lulesh_sample1.yaml

When prompted, reply in the affirmative:

    $ Would you like to launch the study?[yn] y

Currently, there is no way to monitor the status of a running study. However, you can monitor the output path which is placed in the ```sample_output/lulesh/``` directory.

NOTE: This example can only be executed on Unix systems currently because it makes use of ```sed``` and ```curl```. 

----------------

## Contributors
Many thanks go to MaestroWF's [contributors](https://github.com/LLNL/maestrowf/graphs/contributors).

If you have any questions, please [open a ticket](https://github.com/llnl/maestrowf/issues).

----------------

## Release
MaestroWF is released under an MIT license.  For more details see the
NOTICE and LICENSE files.

``LLNL-CODE-734340``
