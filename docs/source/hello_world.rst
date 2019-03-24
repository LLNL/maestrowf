Basics of Study Construction
=============================

Now that you're acquainted with Maestro's interface running a pre-made example, we'll walk you through the basics of making a simple "Hello, World" specification of your own. This page will walk you through the following:

- A single step "Hello World" without parameterization.
- An introduction to a single parameter "Hello World" study.
- An introduction to a multi-parameter "Hello World" study.
- Adding a "farewell" step to "Hello World".

Maestro's default study description uses general YAML notation, which stands for "Yet Another Markup Language" and is a standard data serialization language. For more information on the YAML language, head `here <https://yaml.org/spec/1.2/spec.html>`_ to learn more.

Creating a Single Step Study
*****************************

To start, we will walk through constructing a single step "Hello World" study that simply echoes "Hello, World!" to a file. The first step is to name your study -- in this case we'll settle for something simple and just call our study "Hello World". In your editor of choice, begin by adding the following:

.. code-block:: yaml
    :linenos:

    description:
        name: hello_world
        description: A simple 'Hello World' study.


.. note:: The `description` block is a required section in every study and has two required keys: name, and description. You may add other keys to the description section, but Maestro will not check for them.

Next we will add the `env` section. This section isn't required, but in this case, we want to stash all study workspaces in a common directory. The `env` section can contain a section named `variables`, which can contain a variable named `OUTPUT_PATH`. Maestro recognizes `OUTPUT_PATH` as a keyword and we can use it to have Maestro create new workspaces for this study in a single place. In this case, we want to create the path `./sample_output/hello_world` to collect all "hello world" studies. To do that, add the `env` section as follows to the specification:

.. code-block:: yaml
    :linenos:

    env:
        variables:
            OUTPUT_PATH: ./sample_output/hello_world

The final section to add will be the `study` section which will only contain a single step. Below the `description` section in the study file you've created add the following block:

.. code-block:: yaml
    :linenos:

    study:
        - name: hello_world
          description: Build the serial version of LULESH.
          run:
              cmd: |
                echo "Hello, World!" > hello_world.txt


.. note:: The `-` denotes a list item in YAML, which means if you wanted to add more steps you could. For now, though, we will keep it simple with one.

The only required keys for a study step are the name, description, and a run section containing a command (`cmd`). You might notice the similarity in requirement to the study itself of a `name` and `description` entry. This requirement is intentional in order to encourage documentation as you develop a study. The following are descriptions of the required keys:

.. glossary::

    name
     A unique name to identify this step by (tip: make this something relevant).

    description
     A human-readable sentence or paragraph describing what this step is meant to achieve.

    run
     A dictionary containing keys that describe what runs in this step.

    cmd
     A string of commands to be executed by this step.

There are optional keys which we will cover later on -- but for now, these are the minimum set of requirements.

The completed "hello world" specification should now look like the following:

.. code-block:: yaml
    :linenos:

    description:
        name: hello_world
        description: A simple 'Hello World' study.

    env:
        variables:
            OUTPUT_PATH: ./sample_output/hello_world

    study:
        - name: hello_world
          description: Build the serial version of LULESH.
          run:
              cmd: |
                echo "Hello, World!" > hello_world.txt

Now that the single step "Hello World" study is complete, go ahead and save it to the file `hello_world.yaml`. In order to run the study, simply run the following::

    $ maestro run hello_world.yaml

The command above will produce a timestamped folder that contains the output of the above study. If you'd like to know more about Maestro's command line interface and study output, take a look at our :doc:`Quick Start <./quick_start>` guide. The "hello_world" study above produces a directory that looks similar to the following:

.. code-block:: bash

    drwxr-xr-x  4 dinatale3  59021   136B Jan 10 09:41 hello_world
    -rw-r--r--  1 dinatale3  59021   2.3K Jan 10 09:41 hello_world.pkl
    -rw-r--r--  1 dinatale3  59021     0B Jan 10 09:41 hello_world.txt
    -rw-r--r--  1 dinatale3  59021   340B Jan 10 09:40 hello_world.yaml
    drwxr-xr-x  3 dinatale3  59021   102B Jan 10 09:40 logs
    drwxr-xr-x  5 dinatale3  59021   170B Jan 10 09:40 meta
    -rw-r--r--  1 dinatale3  59021   241B Jan 10 09:41 status.csv

From here, change into the "hello_world" subdirectory. Here you'll see that there are two files: the generated "hello_world.sh" shell script and the resulting output "hello_world.txt". The directory looks similar to:

.. code-block:: bash

    -rwxr--r--  1 dinatale3  59021    53B Jan 10 09:41 hello_world.sh
    -rw-r--r--  1 dinatale3  59021    14B Jan 10 09:41 hello_world.txt

You'll notice that the study directory only contains "hello_world" and the contents for a single run (which corresponds to the singular step above). Maestro detects that the step is not parameterized and uses the workspace that corresponds with the "hello_world" step.

In the next section we cover the basics of how to add a single parameter to the "Hello World" study.

Adding a Single Parameter to Hello World
*****************************************

Now that you have a functioning single step study, let's expand "Hello World" to greet multiple people. To add this new functionality, that means you need to add a new section called `global.parameters` to our `hello_world.yaml` study specification.  So, let's say we want to say hello to Pam, Jim, Michael, and Dwight. The `global.paramters` section would look as follows:

.. code-block:: yaml
    :linenos:

    global.parameters:
        NAME:
            values: [Pam, Jim, Michael, Dwight]
            label: NAME.%%

.. note:: `%%` is a special token that defines where the value in the label is placed. In this case the parameter labels will be `NAME.Pam`, `NAME.Jim`, and etc. The label can take a custom text format, so long as the `%%` token is included to be able to substitute the parameter's value in the appropriate place.

In order to use the
