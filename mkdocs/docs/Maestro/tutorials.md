# Tutorials
----

This section will build up a complete example demonstrating the core features of Maestro studies and how to run and interact with them.  These examples can be found in the `samples` directory at the root of the git repository in addition to being copyable directly from the docs.

## Hello World
----

We'll start with a simple linear study, aka no parameters.  Create a `YAML` file named `hello_world.yaml` and start with the two keys that are required to make a runnable study specification: `description` and `study`.  Documentation and repeatability are core features of Maestro, and the description is one of the means of enforcing these.  Two keys are required for the `description` block, `name` and `description`, as shown below:

``` yaml
description:
    name: hello_world
    description: A simple 'Hello World' study.
```

Now that we have the documentation and purpose of the study embedded into it it's time to add something for it to actually do.  This is done via the `study` block, which contains a list of study steps.  We'll use the `-` `YAML` syntax here as each step is a multiline dictionary of sub keys.  As with the study level `description`, each step is required to have a `name` and a `description`.  `name` is a unique identifier here and can be used in references as shown in subsequent examples.  Finally there is the `run` block, which contains at a minimum a `cmd` key which contains the actual shell commands to run.  Currently these are bash only.  We use the `|` `YAML` syntax to denote the following will be multiple lines but all are stored in the `cmd` key:

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

### The `run` command

The `run` subcommand is how you tell Maestro to go and execute this study we've defined:

``` console
maestro run study.yaml
```

There are many additional arguments you can pass to each subcommand, but for this study there is one that is particularly relevant: `sleep`.  By default Maestro will sleep for 60 seconds between checks for submitting new jobs and checking on status of existing jobs.  As most of the studies in the tutorial run very quickly we can adjust this down to ~1s to get faster turnaround.

``` console title="maestro run -h" hl_lines="1 4 14 15"
usage: maestro run [-h] [-a ATTEMPTS] [-r RLIMIT] [-t THROTTLE] [-s SLEEPTIME] [--dry] [-p PGEN] [--pargs PARGS] [-o OUT] [-fg] [--hashws] [-n | -y] [--usetmp] specification

positional arguments:
  specification         The path to a Study YAML specification that will be loaded and executed.

options:
  -h, --help            show this help message and exit
  -a ATTEMPTS, --attempts ATTEMPTS
                        Maximum number of submission attempts before a step is marked as failed. [Default: 1]
  -r RLIMIT, --rlimit RLIMIT
                        Maximum number of restarts allowed when steps. specify a restart command (0 denotes no limit). [Default: 1]
  -t THROTTLE, --throttle THROTTLE
                        Maximum number of inflight jobs allowed to execute simultaneously (0 denotes not throttling). [Default: 0]
  -s SLEEPTIME, --sleeptime SLEEPTIME
                        Amount of time (in seconds) for the manager to wait between job status checks. [Default: 60]
  --dry                 Generate the directory structure and scripts for a study but do not launch it. [Default: False]
  -p PGEN, --pgen PGEN  Path to a Python code file containing a function that returns a custom filled ParameterGenerator instance.
  --pargs PARGS         A string that represents a single argument to pass a custom parameter generation function. Reuse '--parg' to pass multiple arguments. [Use with '--pgen']
  -o OUT, --out OUT     Output path to place study in. [NOTE: overrides OUTPUT_PATH in the specified specification]
  -fg                   Runs the backend conductor in the foreground instead of using nohup. [Default: False]
  --hashws              Enable hashing of subdirectories in parameterized studies (NOTE: breaks commands that use parameter labels to search directories). [Default: False]
  -n, --autono          Automatically answer no to input prompts.
  -y, --autoyes         Automatically answer yes to input prompts.
  --usetmp              Make use of a temporary directory for dumping scripts and other Maestro related files.
```

<!-- ADD IN SAMPLE OUTPUT YOU SEE WHEN CALLING MAESTRO RUN -> including the prompt to submit or not -->


``` console title='Running the Hello World study'
$ maestro run hello_world.yaml -s 1
[2022-08-27 23:42:48: INFO] INFO Logging Level -- Enabled
[2022-08-27 23:42:48: WARNING] WARNING Logging Level -- Enabled
[2022-08-27 23:42:48: CRITICAL] CRITICAL Logging Level -- Enabled
[2022-08-27 23:42:48: INFO] Loading specification -- path = hello_world.yaml
[2022-08-27 23:42:48: INFO] Directory does not exist. Creating directories to /path/to/maestro/outputs/hello_world/hello_world_20220827-234248/logs
[2022-08-27 23:42:48: INFO] Adding step 'hello_world' to study 'hello_world'...
[2022-08-27 23:42:48: INFO]
------------------------------------------
Submission attempts =       1
Submission restart limit =  1
Submission throttle limit = 0
Use temporary directory =   False
Hash workspaces =           False
Dry run enabled =           False
Output path =               /path/to/maestro/outputs/hello_world/hello_world_20220827-234248
------------------------------------------
Would you like to launch the study? [yn] y
Study launched successfully.
```

Maestro will prompt you to actually launch the study before submitting, letting you confirm some of the settings first.  These options will be covered later in these tutorials and the how-to sections <!-- NOTE: LINK TO HOW-TO-GUIDES -->.

### Checking the status

After invoking `maestro run hello_world.yaml -s 1` you won't see any output directly.  Looking back at the specification that was written, the "Hello World!" output we are looking for is actually written to a file `hello_world.txt`.  Do an `ls` on your current workspace and you will see Maestro created some new folders when it executed the study.  In this case it will simply be the name of the study, from the `description` block, with a date-timestamp appended to it using an `_`.  To see if anything actually ran, maestro provides a `status` sub command, which takes that `study_name_date-timestamp` directory as the only required argument.  Note that the status output automatically wraps text in columns so that the table fits within the current width of your terminal, which you can see happening in the sample output below.  There are some additional layout options you can explore via `maestro status -h` such as `narrow` which can help with this if you have trouble making your terminal wide enough.  The output also adapts to your terminal's color theme, and thus the sample below may look different for you.

``` console
maestro status /path/to/study/output/hello_world_20220712-230235
```

![Hellow World Status](../assets/images/examples/hello_world/hello_world_status.svg)

### Outputs

Now let's take a look at what actually got written to that date-timestamped output directory we found.  You will see something similar to the snapshot below:

![Hello World Workspace](../assets/images/examples/hello_world/hello_world_workspace.svg)

!!! note

    The output above was generated with the help of the excellent [Rich Library](https://github.com/Textualize/rich), which is also used for rendering the study status.  See the INSERT LINK script if you wish to reproduce the view for your own study workspaces
    
Inside that date-timestamped workspace that contains this instance of the executed study is more than you might expect to get generated for a study who's only output is the "hello_world.txt" that is generated in the actual study step.  Most of this is metadata Maestro needs for generating and running the study (`meta` folder), log files which you can use to debug your studies (see `maestro -h` for debug/log options), the pickle file Maestro creates for managing study data while running, and then finally the workspaces for each of the steps in the study.  In this case we have a single directory with `name` from the specification, combined with error and standard outputs from the executed shell script, the generated output file `hello_world.txt` and the shell script itself `hello_world.sh`.  This last file is one of the more important pieces as it is the shell script as Maestro ran it.  This enables both debugging and verifying pre run (using `--dry` argument to the `run` command), as well as rerunning.  This shell script is runnable as is without Maestro, enabling more rapid debugging and testing of it.  

### Environment (`env`) block

If you keep launching new instances of this study you will quickly have a whole bunch of `hello_world_date-timestamp` directories cluttering up the local workspace along side where your `hello_world.yaml` study specification is.  Maestro provides a facility to help with this in the optional `env`, or environment block.  In this block, under the `variables` sub-block you can specify an optional `OUTPUT_PATH` variable, which is a special token maestro looks for to generate a parent directory to write all those timestamped study instances to and keep them more organized.  Adding that to our specification, all timestamped directories will now be written into a `samples` directory that is located at the same level as our `hello_world.yaml` study specification.  Note that relative pathing works and is relative to the study specification, but absolute paths can also be used.

``` yaml
description:
    name: hello_world
    description: A simple 'Hello World' study.
   
env:
    variables:
      OUTPUT_PATH: ./samples
      
study:
    - name: say-hello
      description: Say hello to the world!
      run:
          cmd: |
            echo "Hello, World!" > hello_world.txt
```

### Workflow topology

One final detail to note here is the topology of the workflow we have built.  Studies are organized using directed acyclic graphs, or DAG's, and Maestro's input features enable building DAG's with several topologies which we will highlight as we go.  This example uses the simplest, which is a single step, unparameterized (or linear) graph as shown below

``` mermaid
graph TD;
    A(study root)-->B(say-hello);
```

Here `study root` has special meaning, and is always the root of the DAG's that define a study despite not being an actual step in your workflow.

## Hello, Bye World
----

Now that we've got a taste for what a Maestro specification looks like, how to run it, and what it generates, it's time to look into more interesting workflow topologies.  That was a lot of work for echoing "Hello World", but we now have a framework to build on and do a whole lot more with minimal extra work.  A common next step in defining studies and workflows is to add dependent or child steps using the optional `depends` key in study steps' `run` block.  Let's add a second step that says 'good-bye', but we also don't want this to run until after we say 'hello'.  The `depends` key simply takes a list of other step names, which tells Maestro to not run this step until those dependencies have successfully completed.

``` yaml
description:
    name: hello_bye_world
    description: A simple 'Hello World' study.
   
env:
    variables:
      OUTPUT_PATH: ./samples/hello_bye_world
      
study:
    - name: say-hello
      description: Say hello to the world!
      run:
          cmd: |
            echo "Hello, World!" > hello_world.txt
            
    - name: say-bye
      description: Say good bye to the world!
      run:
          cmd: |
            echo "Good-bye, World!" > good_bye_world.txt
          depends: [say-hello]
```

### Workflow Topology

Now our topology is slightly more interesting:

``` mermaid
graph TD;
    A(study root)-->B(say-hello);
    B(say-hello)-->C(say-bye);
```

### Outputs

The outputs for this new study now have an extra step, as well as some more isolation via the `OUTPUT_PATH` set to contain all of this study's outputs in it's own sub-directory `hello_bye_world`.

![Hello Bye World Workspace](../assets/images/examples/hello_bye_world/hello_bye_world_workspace.svg)

!!! note

    The step listing in the workspace will reflect file system ordering, not the order defined in the workflow/study specification.

## Parameterized Hello World

This example introduces a new block: `global.parameters`.  With this we can further change the workflow topology by layering on parameters to the `Hello Bye World` example which Maestro will expand into multiple chains of 'Hello' -> 'Bye' steps.  Two parameters are added, each with multiple values: `NAME` and `GREETING`.  These are added in a dictionary style with keys being the parameter names and their values being dictionaries themselves with a `values` key that is a list of values to map the study steps/graph onto, and a label which is a `<string>.%%` format, where the `.%%` is replaced with parameter values.  These labels are used for constructing unique step names and workspaces as will be shown below.

``` yaml
global.parameters:
    NAME:
        values: [Pam, Jim, Michael, Dwight]
        label: NAME.%%
    GREETING:
        values: [Hello, Ciao, Hey, Hi]
        label: GREETING.%%
```

These parameter values are 1-1 pairings that define the set of parameter combinations, not cross products.  The above parameter set builds 4 parameter combos:

|            | Combo #1 | Combo #2 | Combo #3 | Combo #4 |
| :-         | :-:      | :-:      | :-:      | :-:      |
| `NAME`     | Pam      | Jim      | Michael  | Dwight   |
| `GREETING` | Hello    | Ciao     | Hey      | Hi       |

Maestro automatically scans steps and their keys for tokens matching these `global.parameters` entries using a special syntax with the token name wrapped in `$()` constructs.  Below is the hello bye world specification with these two parameters added into the say-hello step:

``` yaml
description:
    name: hello_bye_parameterized
    description: A study that says hello and bye to multiple people.

env:
    variables:
        OUTPUT_PATH: ./samples/hello_bye_parameterized

study:
    - name: say-hello
      description: Say hello to someone!
      run:
          cmd: |
            echo "$(GREETING), $(NAME)!" > hello.txt

    - name: say-bye
      description: Say bye to someone!
      run:
          cmd: |
            echo "Good-bye, World!" > good_bye_world.txt
          depends: [say-hello]

global.parameters:
    NAME:
        values: [Pam, Jim, Michael, Dwight]
        label: NAME.%%
    GREETING:
        values: [Hello, Ciao, Hey, Hi]
        label: GREETING.%%
```

### Workflow Topology

``` mermaid
flowchart TD;
    A(study root) --> COMBO1;
    subgraph COMBO1 [Combo #1]
      subgraph say_hello1 [say-hello]
        B(Hello, Pam) ;
      end
      say_hello1 --> C(say-bye);
    end
    A --> COMBO2
    subgraph COMBO2 [Combo #2]
      direction TB
      subgraph say_hello2 [say-hello]
        D(Ciao, Jim)
      end
      
      say_hello2 --> E(say-bye);
    end
    A --> COMBO3
    subgraph COMBO3 [Combo #3]
      subgraph say_hello3 [say-hello]
        F(Hey, Michael)
      end
      say_hello3 --> G(say-bye);
    end
    A --> COMBO4
    subgraph COMBO4 [Combo #4]
      subgraph say_hello4 [say-hello]
        H(Hi, Dwight)
      end
      say_hello4 --> I(say-bye);
    end
```

### Outputs

The outputs for parameterized studies look a little different.  In each parameterized step there is an additional hierarchy in the directory structure.  Each step still has it's own directory, but inside of those there is now one directory for each parameterized instance of the step.  You'll note the `label` values shown in the `YAML` specification for each parameter are used to construct unique paths to identify each parameter combination.

![Hello Bye Parameterized Workspace](../assets/images/examples/hello_bye_parameterized/hello_bye_parameterized_workspace.svg)

A few details stick out here.  You may notice that the `say-bye` step appears to be parameterized even though we did not put any `$(NAME), $(GREETING)` tokens in that step in the study specification.  When Maestro encounters a step that depends upon a parameterized step it will automatically propagate those parameters down, creating parameterized instances of any child steps.  The exception is the [depends on all](#parameterized-hello-bye-study-with-funnel-dependency) type of dependency, which will be discussed in the next example extension.

### Labels

One more detail that is potentially confusing when working with these outputs is that they all have the same name `'hello.txt'` even though each one contains a different string.  We can use another feature of the Environment (`env`) block to parameterize that as well.  Labels are intepreted as strings, and are processed before expansion of the `global.parameters`, enabling their use for dynamic formatting/naming of things in steps in a reusable way.  The study specification with these few additions is below:

``` yaml hl_lines="8 9 16"
description:
    name: hello_bye_parameterized
    description: A study that says hello and bye to multiple people.

env:
    variables:
        OUTPUT_PATH: ./samples/hello_bye_parameterized
    labels:
        OUT_FORMAT: $(GREETING)_$(NAME).txt

study:
    - name: say-hello
      description: Say hello to someone!
      run:
          cmd: |
            echo "$(GREETING), $(NAME)!" > $(OUT_FORMAT)

    - name: say-bye
      description: Say bye to someone!
      run:
          cmd: |
            echo "Good-bye, World!" > good_bye_world.txt
          depends: [say-hello]

global.parameters:
    NAME:
        values: [Pam, Jim, Michael, Dwight]
        label: NAME.%%
    GREETING:
        values: [Hello, Ciao, Hey, Hi]
        label: GREETING.%%
```

And with that slight change we have output files that don't require any file system context to identify.

![Labeled Hello Bye Parameterized Workspace](../assets/images/examples/hello_bye_parameterized/hello_bye_parameterized_labeled_workspace.svg)

## Parameterized Hello, Bye Study with Funnel Dependency

There is one more type of dependency that can be used to create a new topology in your workflow/study graphs.  Steps can be made dependent on the successful completion of all parameterized versions of the named parent step using the syntax `[<step-name>_*]`, with the `_*`.  The new study will add both an extra step and an extra parameter.  A new step will say bye to someone, each with a different greeting, before a final good bye step directed at everyone after the individual goodbyes are said.  Note the highlighted changes in this new study

``` yaml hl_lines="9 10 17 23 26-31 40-42"
description:
    name: hello_bye_parameterized_funnel
    description: A study that says hello and bye to multiple people, and a final good bye to all.

env:
    variables:
        OUTPUT_PATH: ./samples/hello_bye_parameterized_funnel
    labels:
        HELLO_FORMAT: $(GREETING)_$(NAME).txt
        BYE_FORMAT: $(FAREWELL)_$(NAME).txt

study:
    - name: say-hello
      description: Say hello to someone!
      run:
          cmd: |
            echo "$(GREETING), $(NAME)!" > $(HELLO_FORMAT)

    - name: say-bye
      description: Say bye to someone!
      run:
          cmd: |
            echo "$(FAREWELL), $(NAME)!" > $(BYE_FORMAT)
          depends: [say-hello]

    - name: bye-all
      description: Say bye to everyone!
      run:
          cmd: |
            echo "Good-bye, World!" > good_bye_all.txt
          depends: [say-bye_*]

global.parameters:
    NAME:
        values: [Pam, Jim, Michael, Dwight]
        label: NAME.%%
    GREETING:
        values: [Hello, Ciao, Hey, Hi]
        label: GREETING.%%
    FAREWELL:
        values: [Goodbye, Farewell, So long, See you later]
        label: FAREWELL.%%
```

!!! note

    An important effect of this dependency type is that any step with it requires all parent steps to complete successfully.  If you need the funnel/depends-all step to run no matter what you need to account for a successful return type in the parameterized steps.  See HOW_TO_GUIDES and OTHER_SECTIONS <!-- HOW_TO_GUIDE --> for more discussion of this behavior and how to deal with it.

### Workflow Topology

The new parameter expands the parameter combinations in the workflow:

|            | Combo #1 | Combo #2 | Combo #3 | Combo #4      |
| :-         | :-:      | :-:      | :-:      | :-:           |
| `NAME`     | Pam      | Jim      | Michael  | Dwight        |
| `GREETING` | Hello    | Ciao     | Hey      | Hi            |
| `FAREWELL` | Goodbye  | Farewell | So long  | See you later |

``` mermaid
flowchart TD;
    A(study root) --> COMBO1;
    subgraph COMBO1 [Combo #1]
      subgraph say_hello1 [say-hello]
        B(Hello, Pam)
      end
      subgraph say_bye1 [say-bye]
        C(Goodbye, Pam)
      end
      say_hello1 --> say_bye1
    end
    A --> COMBO2
    subgraph COMBO2 [Combo #2]
      direction TB
      subgraph say_hello2 [say-hello]
        D(Ciao, Jim)
      end
      subgraph say_bye2 [say-bye]
        E(Farewell, Jim)
      end
      say_hello2 --> say_bye2
    end
    A --> COMBO3
    subgraph COMBO3 [Combo #3]
      subgraph say_hello3 [say-hello]
        F(Hey, Michael)
      end
      subgraph say_bye3 [say-bye]
        G(So long, Michael)
      end
      say_hello3 --> say_bye3
    end
    A --> COMBO4
    subgraph COMBO4 [Combo #4]
      subgraph say_hello4 [say-hello]
        H(Hi, Dwight)
      end
      subgraph say_bye4 [say-bye]
        I(See you later, Dwight)
      end
      say_hello4 --> say_bye4;
    end
    
    COMBO1 --> J{{bye-all}}
    COMBO2 --> J{{bye-all}}
    COMBO3 --> J{{bye-all}}
    COMBO4 --> J{{bye-all}}
```

### Outputs

Note the extra parameter also shows up in the `'say-hello'` step despite not being explicitly used.  Maestro currently propagates parameter combinations, not just used parameters.

![Labeled Hello Bye Parameterized Workspace with Funnel](../assets/images/examples/hello_bye_parameterized/hello_bye_parameterized_labeled_funnel_workspace.svg)

!!! warning

    This unique labeling of directories cannot be extended indefinitely.  Operating systems do have fixed path lengths that must be respected.  To accomodate this, Maestro offers a hashing option at run-time to enable arbitrarily large numbers of parameters in each combination: `maestro run study.yaml --hashws ...`
