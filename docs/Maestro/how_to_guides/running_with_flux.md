# Using Maestro with Flux
---
Flux is unique amongst the scheduler adapters as it can be used in standalong batch job mode just like Slurm and LSF as well as in node/allocation packing mode.  The allocation packing mode can be used regardless of the scheduler that is used to launch Flux:

* Schedule to Flux batch jobs, which have nested brokers
* Startup Flux brokers/instances inside of LSF and Slurm allocations and submit to those

A little setup is needed before testing out these different modes.

## Installation

Running with Flux requires a few additional installation steps as Maestro is using the python interface.

### Pip installation of bindings (for Flux > 0.45.0)

!!! success "Recommended Option"
    
    Using this pip binding install process with the newest versions of Flux is a preferred option

Assuming Flux is installed on your system and you have a virtualenv active to install into:
  
```console
$ flux -V
commands:    		0.50.0
libflux-core:		0.50.0
libflux-security:	0.9.0
build-options:		+ascii-only+systemd+hwloc==2.8.0+zmq==4.3.4

$ pip install "flux-python==0.50.0"
```
  
The full list of available versions can be found on [pypi](https://pypi.org/project/flux-python/#history), one per Flux version.  Note that for some versions you may need to use one of the release candidates (rc<num>).

### Spack environment

!!! success "Recommended Option"

This option may be of interest if you are running on a system where Flux is not the native scheduler and/or is not publicly installed.  Check out the [spack tutorials](https://spack-tutorial.readthedocs.io/en/latest/tutorial_environments.html) for building an environment to install Flux and python, and then you can install Maestro into that environment.
    
### Manual linking to existing/system Flux install

!!! danger "Not Recommended"

    This option should be a last resort if the other two options don't work

This option requires a few more steps. First, get the python path from Flux and append it to yours (after activating your virtualenv)
    
```console
$ flux env
export FLUX_PMI_LIBRARY_PATH="/usr/lib64/flux/libpmi.so"
export LUA_PATH="/usr/share/lua/5.3/?.lua;;;"
export FLUX_EXEC_PATH="/usr/libexec/flux/cmd"
export PYTHONPATH="/usr/lib64/flux/python3.6"
export LUA_CPATH="/usr/lib64/lua/5.3/?.so;;;"
export FLUX_CONNECTOR_PATH="/usr/lib64/flux/connectors"
export MANPATH="<some giant list of paths..>"
export FLUX_MODULE_PATH="/usr/lib64/flux/modules"

$ export PYTHONPATH=$PYTHONPATH:/usr/lib64/flux/python3.6
```
    
Alternatively, use awk to update `$PYTHONPATH` automatically (or make a bash/zsh/etc func that can update/remove it later)
    
```bash
export PYTHONPATH=$PYTHONPATH:`flux env | awk -F "[= ]" '{if ($2 == "PYTHONPATH") {env=$3; split(env, p, "\""); print p[2]}}'`
```
    
Then install the two required python packages into your environment
    
```console
$ pip install cffi pyyaml
```
    
Then you can install Maestro and start scheduling jobs to a Flux instance 


## Running with Flux
---

As mentioned at the above, the Flux adapter is different from the SLURM and LSF adapters in that it also enables usage as an allocation packing option where you may be running a Flux instance inside of SLURM/LSF.  The adapter in Maestro can use an optional 'uri' to specify a particular Flux instance to schedule to, or in its absence assume it's talking to a system level broker where Maestro submits standalone batch jobs just as with SLURM and LSF.

### Adapter version

The Flux adapter has an optional version switching mechanism to accomodate the variety of installs and more rapid behavior changes for this pre 1.0 scheduler.  The default behavior is to try using the latest adapter version.  This can be overridden using the [`version`](../specification.md#batch-batch) key in the batch block, choosing from one of the available options using the selection mechanism added in Maestro v1.1.9dev1:

| Adapter Version | Flux Version |
| :-              | :-           |
| 0.17.0          | >= 0.17.0    |
| 0.18.0          | >= 0.18.0    |
| 0.26.0          | >= 0.26.0    |
| 0.49.0          | >= 0.49.0    |

!!! note

    Maestro's adapter versions are not pinned to exact Flux versions.  The adapter version lags behind the Flux core version until breaking changes are introduced by Flux core.

### Standalone batch jobs

In the absence of either populating the 'flux_uri' key in the batch block or the presence of the `FLUX_URI` environment variable, Maestro assumes you are scheduling to a system level instance, i.e. a machine managed natively by Flux.  This will behave the same as the SLURM and LSF adapters.
    
    
### Allocation packing mode

When the `FLUX_URI` environment variable is set, Maestro will submit jobs to that specific Flux broker, which can either be a nested instance inside a batch job on a Flux managed machine (uri ~ Flux jobid), or a Flux broker that was started by the user inside of a SLURM or LSF allocation.  There are two ways to get this going
    
#### Launch Maestro inside the batch job/Flux broker
    
When you are inside a Flux batch job, or start a Flux broker inside of a SLURM or LSF allocation, Flux will automatically export the `FLUX_URI`.  In this case you can simply execute `maestro run <specification>` inside of that broker/allocation and it will read that environment variable and submit all jobs to that broker.  The primary concern here will be you may want/need to account for Maestro's conductor process consuming resources on one of the cores, depending on how often conductor sleeps and how resource intensive your processes are.
        
#### Launch Maestro external to the batch job/Flux broker

!!! success "Recommended Option"


On HPC clusters this often means running Maestro on the login node, but can be any machine that has ssh access to node/allocation that the Flux broker is running in.  This option has the benefit that Maestro's conductor process does not consume allocation resources, and also that the allocation terminating early does not interrupt conductor's management of the study and leave it in an error state.  There are multiple recipes for this, which vary in complexity based on machine configuration and flux version.  See the Flux docs for more thorough discussions of this process on the non flux native machines such as [Slurm](https://flux-framework.readthedocs.io/en/latest/quickstart.html#starting-a-flux-instance) and [LSF](https://flux-framework.readthedocs.io/en/latest/tutorials/lab/coral.html).
       
* Current versions of flux (~>0.40)

    This process becomes much easier in the newest Flux versions which have native support for resolving nested uri on both SLURM and LSF; see more discussion in the flux documentation linked earlier
    
    === "LSF"
    
        Resolving the uri can be done using the system native job id of the batch jobs where the flux broker was launched
        
        ```console
        $ flux uri --remote lsf:<lsf jobid>
        ssh://<job hostname>/var/tmp/flux-<hash>/local-0
        ```
        
        The full recipe of updating the `FLUX_URI` environment variable and running a study in that broker:

        ```console
        $ export FLUX_URI=`flux uri --remote lsf:<lsf_jobid>`
        
        $ maestro run <study_specification> [run opts]
        ```
        
    === "SLURM"
    
        Resolving the uri can be done using the system native job id of the batch jobs where the flux broker was launched
        
        ```console
        $ flux uri --remote slurm:<slurm jobid>
        ssh://<job hostname>/var/tmp/flux-<hash>/local-0
        ```
        
        The full recipe of updating the `FLUX_URI` environment variable and running a study in that broker:
        
        ```console
        $ export FLUX_URI=`flux uri --remote slurm:<slurm_jobid>`
        
        $ maestro run <study_specification> [run opts]
        ```

* Older versions of Flux (~<0.40)

    First, for older versions of Flux which do not have the lsf/slurm jobid proxy helpers, there is a recipe you can bake into your batch job that's launching Flux to expose the uri of the Flux broker to processes outside of that allocation using ssh.

    The address of the broker can be constructed and dropped in a file via the following recipe using Flux's [`getattr`](https://flux-framework.readthedocs.io/projects/flux-core/en/latest/man7/flux-broker-attributes.html) command to query the broker/instance once it's started
    
    ```shell title="flux_address.sh"
    #!/bin/sh
    echo "ssh://$(hostname)$(flux getattr rundir)/local-0" | tee flux_address.txt
    sleep inf
    ```

    To drop this file, submit a batch job or get an interactive allocation that starts up the Flux broker and runs the above script:
    
    First, spin up a Flux instance
    
    === "LSF"
    
        Either using `bsub` or interactively via `lalloc` as shown here
        
        ```console
        $ lalloc 1 -W 60 -q pdebug -G guests
        
        $ jsrun -a 1 -c 40 -g 0 -n 1 --bind=none flux start ./flux_address.sh
        ```
    === "SLURM"
    
        Either use `sbatch` or interactively via `salloc` as shown below
        
        ```console
        $ salloc -N 1 -p pdebug -A guests
        
        $ srun -n1 -c112 flux start ./flux_address.sh
        ```
    
    Then from the login node you can launch a Maestro study that schedules to this nested Flux instance
    
    ```console
    $ export FLUX_URI=`cat flux_address.txt`
    
    $ maestro run <study_specification> [run opts]
    ```

* Extras

    You can still use other Flux commands from the login nodes to the brokers living inside allocations using the same uri resolution methods such as the `flux top` command for monitoring your study's Flux jobs in real time:
    
    ```console
    $ flux proxy `flux uri --remote slurm:<slurm_jobid>` flux top
    ```
    

## Example Specs
---

Check out a few example specifications to get started running with flux ranging from simple flux managed serial commands to mpi enabled applications.

=== "Hello, Bye World"
    
    Simple serial applications managed by flux to run parameter combinations in parallel

    ``` yaml title="hello_bye_parameterized_flux.yaml"
    --8<-- "samples/hello_world/hello_bye_parameterized_flux.yaml"
    ```

    Workflow topology:

    ``` mermaid
    flowchart TD;
        A(study root) --> COMBO1;
        subgraph COMBO1 [Combo #1]
          subgraph say_hello1 [say-hello]
            B(Hello, Pam)
          end
          subgraph say_bye1 [say-bye]
            C(Bye, World!)
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
            E(Bye, World!)
          end
          say_hello2 --> say_bye2
        end
        A --> COMBO3
        subgraph COMBO3 [Combo #3]
          subgraph say_hello3 [say-hello]
            F(Hey, Michael)
          end
          subgraph say_bye3 [say-bye]
            G(Bye, World!)
          end
          say_hello3 --> say_bye3
        end
        A --> COMBO4
        subgraph COMBO4 [Combo #4]
          subgraph say_hello4 [say-hello]
            H(Hi, Dwight)
          end
          subgraph say_bye4 [say-bye]
            I(Bye, World!)
          end
          say_hello4 --> say_bye4;
        end
    ```
    
=== "Lulesh"

    Compilation and running of mpi parallel application, which also runs the parameter combinations in parallel
    
    ``` yaml title="lulesh_sample1_unix_flux.yaml"
    --8<-- "samples/lulesh/lulesh_sample1_unix_flux.yaml"
    ```

    Workflow topology:
    
    ``` mermaid
    flowchart TD;
        A(study root) --> B(make-lulesh);
        B-->COMBO1;
        subgraph COMBO1 [Combo #1]
          subgraph run_lulesh1 [run-lulesh]
            C(SIZE=100\nITERATIONS=10)
          end
        end
        B --> COMBO2
        subgraph COMBO2 [Combo #2]
          subgraph run_lulesh2 [run-lulesh]
            D(SIZE=100\nITERATIONS=20)
          end
        end
        B --> COMBO3
        subgraph COMBO3 [Combo #3]
          subgraph run_lulesh3 [run-lulesh]
            E(SIZE=100\nITERATIONS=30)
          end
        end
        B --> COMBO4
        subgraph COMBO4 [Combo #4]
          subgraph run_lulesh4 [run-lulesh]
            F(SIZE=200\nITERATIONS=10)
          end
        end
        B --> COMBO5
        subgraph COMBO5 [Combo #5]
          subgraph run_lulesh5 [run-lulesh]
            G(SIZE=200\nITERATIONS=20)
          end
        end
        B --> COMBO6
        subgraph COMBO6 [Combo #6]
          subgraph run_lulesh6 [run-lulesh]
            H(SIZE=200\nITERATIONS=30)
          end
        end
        B --> COMBO7
        subgraph COMBO7 [Combo #7]
          subgraph run_lulesh7 [run-lulesh]
            I(SIZE=300\nITERATIONS=10)
          end
        end
        B --> COMBO8
        subgraph COMBO8 [Combo #8]
          subgraph run_lulesh8 [run-lulesh]
            J(SIZE=300\nITERATIONS=20)
          end
        end
        B --> COMBO9
        subgraph COMBO9 [Combo #9]
          subgraph run_lulesh9 [run-lulesh]
            K(SIZE=300\nITERATIONS=30)
          end
        end
    ```
