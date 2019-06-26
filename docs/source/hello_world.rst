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

Next we will add the `env` section. This section isn't required, but in this case, we want to stash all study workspaces in a common directory. The `env` section can contain a section named `variables`, which can contain a variable named `OUTPUT_PATH`. Maestro recognizes `OUTPUT_PATH` as a keyword and we can use it to have Maestro create new workspaces for this study in a single place. In this case, we want to create the path `./sample_output/hello_world` to collect all "Hello World" studies. To do that, add the `env` section as follows to the specification:

.. code-block:: yaml
    :linenos:

    env:
        variables:
            OUTPUT_PATH: ./sample_output/hello_world

.. note:: The `OUTPUT_PATH` variable is a Maestro recognized keyword that specifies the base path where study output is written.

The final section to add will be the `study` section which will only contain a single step. Below the `description` section in the study file you've created add the following block:

.. code-block:: yaml
    :linenos:

    study:
        - name: hello_world
          description: Say hello to the world!
          run:
              cmd: |
                echo "Hello, World!" > hello_world.txt


.. note:: The `-` denotes a list item in YAML. To add elements, simply add new elements prefixed with a hyphen. For now, we will keep it simple with one step and will cover adding extra steps later in this guide.

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

The completed "Hello World" specification should now look like the following:

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
          description: Say hello to the world!
          run:
              cmd: |
                echo "Hello, World!" > hello_world.txt

Now that the single step "Hello World" study is complete, go ahead and save it to the file `hello_world.yaml`. In order to run the study, simply run the following::

    $ maestro run hello_world.yaml

The command above will produce a timestamped folder that contains the output of the above study. If you'd like to know more about Maestro's command line interface and study output, take a look at our :doc:`Quick Start <./quick_start>` guide. The "hello_world" study above produces a directory that looks similar to the following:

.. code-block:: bash

    drwxr-xr-x  6 frank  staff   192B Jun 18 11:32 hello_world
    -rw-r--r--  1 frank  staff   1.8K Jun 18 11:32 hello_world.pkl
    -rw-r--r--  1 frank  staff     0B Jun 18 11:32 hello_world.txt
    -rw-r--r--  1 frank  staff   306B Jun 18 11:32 hello_world.yaml
    drwxr-xr-x  3 frank  staff    96B Jun 18 11:32 logs
    drwxr-xr-x  5 frank  staff   160B Jun 18 11:32 meta
    -rw-r--r--  1 frank  staff   241B Jun 18 11:32 status.csv

From here, change into the "hello_world" subdirectory. Here you'll see that there are four files: the generated "hello_world.sh" shell script, the resulting output "hello_world.txt", a .out log file, and a .err error log. Your directory should look similar to:

.. code-block:: bash

    -rw-r--r--  1 frank  staff     0B Jun 18 11:32 hello_world.err
    -rw-r--r--  1 frank  staff     0B Jun 18 11:32 hello_world.out
    -rwxr--r--  1 frank  staff    53B Jun 18 11:32 hello_world.sh
    -rw-r--r--  1 frank  staff    14B Jun 18 11:32 hello_world.txt

You'll notice that the study directory only contains "hello_world" and the contents for a single run (which corresponds to the singular step above). Maestro detects that the step is not parameterized and uses the workspace that corresponds with the "hello_world" step. If we execute the command `cat hello_world.txt` we see that the output is exactly as specified in the `cmd` portion of the step::

    $ cat hello_world.txt
    $ Hello, World!

In the next section we cover the basics of how to add a single parameter to the "Hello World" study.

Adding a Single Parameter to "Hello World"
*******************************************

Now that you have a functioning single step study, let's expand "Hello World" to greet multiple people. To add this new functionality, that means you need to add a new section called `global.parameters` to our `hello_world.yaml` study specification.  So, let's say we want to say hello to Pam, Jim, Michael, and Dwight. The `global.paramters` section would look as follows:

.. code-block:: yaml
    :linenos:

    global.parameters:
        NAME:
            values: [Pam, Jim, Michael, Dwight]
            label: NAME.%%

.. note:: `%%` is a special token that defines where the value in the label is placed. In this case the parameter labels will be `NAME.Pam`, `NAME.Jim`, and etc. The label can take a custom text format, so long as the `%%` token is included to be able to substitute the parameter's value in the appropriate place.

In order to use the `NAME` parameter, we simply modify the "hello_world" step as follows:

.. code-block:: yaml
    :linenos:

    study:
        - name: hello_world
          description: Say hello to the world!
          run:
              cmd: |
                echo "Hello, $(NAME)!" > hello_world.txt

.. note:: The `$(NAME)` format is an example of the general format used for variables, parameters, dependency references, and labels. For more examples of referencing values, see the `LULESH study <https://github.com/LLNL/maestrowf/blob/develop/samples/lulesh/lulesh_sample1_unix.yaml>`_ in the samples folder in the Maestro GitHub repository.

The full single parameter version of the study specification that says hello to different people is as follows:

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
          description: Say hello to someone!
          run:
              cmd: |
                echo "Hello, $(NAME)!" > hello_world.txt

    global.parameters:
        NAME:
            values: [Pam, Jim, Michael, Dwight]
            label: NAME.%%

If we execute the study and print the contents of the study's workspace, we'll see that the contents are the same as described above. Just as before, if we change into the `hello_world` directory we'll see that the format of the directory has changed. There will now be a set of four directories, one for each parameter value, each containing the `hello_world.txt` output.

.. code-block:: bash

    drwxr-xr-x 6 root root 4096 Mar 25 01:30 ./
    drwxr-xr-x 5 root root 4096 Mar 25 01:30 ../
    drwxr-xr-x 2 root root 4096 Mar 25 01:30 NAME.Dwight/
    drwxr-xr-x 2 root root 4096 Mar 25 01:30 NAME.Jim/
    drwxr-xr-x 2 root root 4096 Mar 25 01:30 NAME.Michael/
    drwxr-xr-x 2 root root 4096 Mar 25 01:30 NAME.Pam/

However, if we `cat` each of the outputs from each directory, we'll see that the value for `$(NAME)` has been substituted::

    $ cat */hello_world.txt
    $ Hello, Dwight!
    $ Hello, Jim!
    $ Hello, Michael!
    $ Hello, Pam!


Expanding "Hello World" to Multiple Steps
******************************************

Now that we've got our specification set up to say hello to multiple people, let's take a step back and look at our base "Hello World" specification and add "bye_world" as specified below:

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
          description: Say hello to the world!
          run:
              cmd: |
                echo "Hello, World!" > hello_world.txt

        - name: bye_world
          description: Say bye to someone!
          run:
              cmd: |
                echo "Bye, World!" > bye_world.txt
              depends: [hello_world]


After adding this step to your specification, go ahead and run it using `maestro run` as before. Now, if you look at the generated study directory, we see that the study generates an extra directory for the "bye_world" step.

.. code-block:: bash

    drwxr-xr-x  6 frank  staff   192B Jun 25 20:54 bye_world
    -rw-r--r--  1 frank  staff   2.3K Jun 25 20:54 hello_bye.pkl
    -rw-r--r--  1 frank  staff     0B Jun 25 20:53 hello_bye.txt
    -rw-r--r--  1 frank  staff   551B Jun 25 20:53 hello_bye_world.yaml
    drwxr-xr-x  6 frank  staff   192B Jun 25 20:53 hello_world
    drwxr-xr-x  3 frank  staff    96B Jun 25 20:54 logs
    drwxr-xr-x  5 frank  staff   160B Jun 25 20:53 meta
    -rw-r--r--  1 frank  staff   383B Jun 25 20:54 status.csv

If you change into this directory, you'll see that a similar set of files to the previous "hello_world" step have been created. You'll see that executing `cat bye_world.txt` prints out "Bye, World!". Now, to take this a step further -- what if we wanted to say bye to each particular person in our parameterized "hello world" example?

Now, if we start with our parameterized hello world specification, we add the "bye_world" step and make it dependent on the "hello_world" step. You should also update the description and study name to something meaningful for the new study.

.. code-block:: YAML
    description:
        name: hello_bye_parameterized
        description: A study that says hello and bye to multiple people.

    env:
        variables:
            OUTPUT_PATH: ./sample_output/hello_world

    study:
        - name: hello_world
          description: Say hello to someone!
          run:
              cmd: |
                echo "$(GREETING), $(NAME)!" > hello_world.txt

        - name: bye_world
          description: Say bye to someone!
          run:
              cmd: |
                echo "Bye, World!" > bye_world.txt
              depends: [hello_world]

    global.parameters:
        NAME:
            values: [Pam, Jim, Michael, Dwight]
            label: NAME.%%
        GREETING:
            values: [Hello, Ciao, Hey, Hi]
            label: GREETING.%%

The study workspace looks the same as the "hello_bye_world" study specified above at the top level;  however, like the multi-parameterized "hello_world" study you'll see that each step's workspaces have parameterized folders. The "hello_world" step has the same workspace set up as the previous parameterized study as expected.

.. code-block:: bash
    drwxr-xr-x  6 frank  staff   192B Jun 25 22:33 GREETING.Ciao.NAME.Jim
    drwxr-xr-x  6 frank  staff   192B Jun 25 22:33 GREETING.Hello.NAME.Pam
    drwxr-xr-x  6 frank  staff   192B Jun 25 22:33 GREETING.Hey.NAME.Michael
    drwxr-xr-x  6 frank  staff   192B Jun 25 22:33 GREETING.Hi.NAME.Dwight

If you look into the "bye_world" workspace, you'll also notice it has the same exact set of folders as "hello_world". While this set up might seem weird at first, it is a feature of how Maestro expands the study using parameters. In a later section, we'll describe how Maestro expands the study in a predictable manner -- but for now, it is enough to know that the "bye_world" step was expanded in a 1:1 fashion because the step is dependent on "hello_world" and the parameters it used. Maestro, in this case, can not make any assumptions and simply expands the "bye_world" one to one with each parameterized "hello_world".

.. note:: You can view the sample specifications constructed here in their entirety in Maestro's GitHub repository `here <https://github.com/LLNL/maestrowf/tree/develop/samples/hello_world>`_.
