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

### Spack environment

!!! success "Recommended Option"

This option may be of interest if you are running on a system where Flux is not the native scheduler and/or is not publicly installed.  Check out the [spack tutorials](https://spack-tutorial.readthedocs.io/en/latest/tutorial_environments.html) for building an environment to install Flux and python, and then you can install Maestro into that environment.
    

## Running with Flux
---

As mentioned at the above, the Flux adapter is different from the SLURM and LSF adapters in that it also enables usage as an allocation packing option where you may be running a Flux instance inside of SLURM/LSF.  The adapter in Maestro can use an optional 'uri' to specify a particular Flux instance to schedule to, or in its absence assume it's talking to a system level broker where Maestro submits standalone batch jobs just as with SLURM and LSF.

### Standalone batch jobs

In the absence of either populating the 'flux_uri' key in the batch block or the presence of the `FLUX_URI` environment variable, Maestro assumes you are scheduling to a system level instance, i.e. a machine managed natively by Flux.  This will behave the same as the SLURM and LSF adapters.
    
    
### Allocation packing mode

When the `FLUX_URI` environment variable is set, Maestro will submit jobs to that specific Flux broker, which can either be a nested instance inside a batch job on a Flux managed machine (uri ~ Flux jobid), or a Flux broker that was started by the user inside of a SLURM or LSF allocation.  THere are two ways to get this going
    
#### Launch Maestro inside the batch job/Flux broker
    
When you are inside a Flux batch job, or start a Flux broker inside of a SLURM or LSF allocation, Flux will automatically export the `FLUX_URI`.  In this case you can simply execute `maestro run <specification>` inside of that broker/allocation and it will read that environment variable and submit all jobs to that broker.  The primary concern here will be you may want/need to account for Maestro's conductor process consuming resources on one of the cores, depending on how often conductor sleeps and how resource intensive your processes are.
        
#### Launch Maestro external to the batch job/Flux broker

!!! success "Recommended Option"


On HPC clusters this often means running Maestro on the login node, but can be any machine that has ssh access to node/allocation that the Flux broker is running in.  This option has the benefit that Maestro's conductor process does not consume allocation resources, and also that the allocation terminating early does not interrupt conductor's management of the study and leave it in an error state.  There are multiple recipes for this, which vary in complexity based on machine configuration and flux version.  See the Flux docs for more thorough discussions of this process on the non flux native machines such as [Slurm](https://flux-framework.readthedocs.io/en/latest/quickstart.html#starting-a-flux-instance) and [LSF](https://flux-framework.readthedocs.io/en/latest/tutorials/lab/coral.html).
       
* Current versions of flux (~>0.40)

    This process becomes much easier in the newest Flux versions which have native support for resolving nested uri on both SLURM and LSF; see more discussion in the flux documentation linked earlier
    
    === "LSF"
    
        Resolving the uri can be done without using the helper script `flux_address.sh` shown above
        
        ```console
        $ flux uri --remote lsf:<lsf jobid>
        ssh://<job hostname>/var/tmp/flux-<hash>/local-0
        ```
        
        ```console
        $ export FLUX_URI=`flux uri --remote lsf:<lsf_jobid>`
        
        $ maestro run <study_specification> [run opts]
        ```
        
    === "SLURM"
    
        Similarly for slurm:
        
        ```console
        $ flux uri --remote slurm:<slurm jobid>
        ssh://<job hostname>/var/tmp/flux-<hash>/local-0
        ```
        
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
