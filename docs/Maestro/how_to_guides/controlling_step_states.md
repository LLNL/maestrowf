# Controlling step states
---

Return codes emitted by the bash scripts/commands defininig a step are the primary mechanism for determining the final state of a job.  Controlling/manipulating these return codes can be crucial to ensuring a study can actually execute successfully.  A few special cases where you want to pay attention to this are:

* Running a simulation which is known to crash at some point, but that point is beyond the successful data collection window.  This case would normally end up with a failed state from Maestro's point of view, disabling execution of any subsequent steps.

* Running a long running task that can itself talk to the scheduler and turn on 'gracetime' style restart checkpoints shortly before the scheduled job times out to enable more optimial restart behavior (spend less time recomputing as can happen with pre-scheduled restart checkpoint dumps).  This case would end up with a success state from Maestro's point of view instead of the expected time out, thus leaving the step in an actually unfinished state despite the status saying otherwise.

=== "Override Failed Return Code"

    In this case there's a few simple options shown in the sample specification below
    
    1.  Parse the logs and/or examine the outputs and mark successful if the right data was collected
    
    2.  Run any shell command that itself returns a success code
        
    ``` yaml hl_lines="19-21 23-24"
    study:
    - name: stage
      description: copy in input/processing files to isolate them to this study
      run:
        cmd: |
          cp $(SPECROOT)/$(INPUT_FILE) .
          cp $(SPECROOT)/$(POST_PROC_TOOL) .
          # insert other setup junk..
         
    - name: sim-run
      description: run the simulation
      run:
        cmd: |
            # Get the input file
            cp $(stage.workspace)/$(INPUT_FILE) .
           
            $(LAUNCHER) $(SIM_EXECUTABLE) -in $(INPUT_FILE)
 
            # run subsequent command to give success return code
            #   e.g. parse logs/outputs
            $(POST_PROC_TOOL) --validate-outputs  # (1)
            
            #   or simply run an echo or other simple shell command
            echo "Job finished successfully"  # (2)
 
        restart: |
            # OMIT THE SETUP CODE/COPYING/ETC
            # also change the invocation if needing to pass a specific restart
            # checkpoint (not shown)
            
            $(LAUNCHER) $(SIM_EXECUTABLE) -in $(INPUT_FILE)
 
 
        procs: $(PROCS)
        walltime: "30:00"
        depends: [stage]
    ```
    

=== "Force a Timeout"

    This solution is very similar, with the primary difference being that the extra command run in the step after the long running simulation/calculation is a simple sleep type operation that runs for long enough to ensure the scheduler has to interrupt it and thus signal to Maestro that a timeout occurred.  Here we're using the simple sleep shell command with a fixed time.  You may want to embed more logic here to determine the required sleep time if it's not known in advance.  An additional safeguard is used here: a post processing tool `$(POST_PROC_TOOL)` is run first to check for gracetime dumps, returning standard error codes, with `0` being used here to say 'yes, gracetime found, go to sleep'.  This retcode then used to switch between sleeping and exiting in an error state to avoid unnecessary restarts if the job actually failed.  This is replicated in the restart script as well to ensure multiple attempts work as expected.  
    
    !!! note 
    
        Any errors in the `$(POST_PROC_TOOL)` will also abort the run as the conditional will correctly detect that based on it's non-zero return code.
    
    ``` yaml hl_lines="19-29 38-48"
    study:
    - name: stage
      description: copy in input/processing files to isolate them to this study
      run:
        cmd: |
          cp $(SPECROOT)/$(INPUT_FILE) .
          cp $(SPECROOT)/$(POST_PROC_TOOL) .
          # insert other setup junk..
         
    - name: sim-run
      description: run the simulation
      run:
        cmd: |
            # Get the input file
            cp $(stage.workspace)/$(INPUT_FILE) .
           
            $(LAUNCHER) $(SIM_EXECUTABLE) -in $(INPUT_FILE)
 
            # Run subsequent commands to check for/force timeout
            #   parse logs/outputs to verify a gracetime occurred
            $(POST_PROC_TOOL) --check-gracetime
            
            if [ $? = 0 ] then
              #  sleep for some amount of time that ensures scheduler will interrupt this
              sleep 3600
            else
              #  error found instead of gracetime, mark failed
              exit 1
            fi
 
        restart: |
            # OMIT THE SETUP CODE/COPYING/ETC
            # also change the invocation if needing to pass a specific restart
            # checkpoint (not shown)

            $(LAUNCHER) $(SIM_EXECUTABLE) -in $(INPUT_FILE)

            # Run subsequent commands to check for/force timeout
            #   parse logs/outputs to verify a gracetime occurred
            $(POST_PROC_TOOL) --check-gracetime
            
            if [ $? = 0 ] then
              #  sleep for some amount of time that ensures scheduler will interrupt this
              sleep 3600
            else
              #  error found instead of gracetime, mark failed
              exit 1
            fi
            
        procs: $(PROCS)
        walltime: "30:00"
        depends: [stage]
    ```
