# MEP 003 - Human Readable Hashing: Compact and sortable step name hashing

## Abstract

Step naming and workspace naming behaviors in Maestro is a frequent pain point in many studies.  The default naming convention aimed to provide quick lookup by encoding parameter names and values in the step name and workspace names.  There are multiple issues that can occur with this scheme that are the target of this enhancement proposal:

* Floating point numbers
    * String versions of floats chosen by a human are not always representable exactly once converted into binary, e.g. 0.1, which is an infinitely repeating binary sequence, which converted back to a string with 17 digits of precision is 0.10000000000000001, 18 yields 0.100000000000000006, ...  Default Maestro label construction would thus have varying numbers of digits in the parameter combination's label/id, frequently far more than what appears in the study specification
    * Primarily a readability problem which gets worse with more digits
  
* Many parameters
    * Many parameters lead to ~unreadable step id's/workspace names, whether that's reading from the command line (`ls`) one of the status command's tables, or some other tabular report/document outside of Maestro (documents, dashboards, ...)
    * Using 10's of parameters, especially with floats, can quickly yield final workspace names that blow out system path length limits.  The only current solution is hashing
    * Both a readability problem and cause of crashing workflows; auto-hashing may help here, but that has it's own issues (see next item)
  
* Existing hashing
    * While this solves the path length issues, it also produces a human unfriendly string which is generally not sortable, not amenable to tab completion, and is quite unreadable and difficult to use even to look up parameter names/values out of a table
    * Existing method uses md5, but other hashing options aren't really any more readable/human friendly
    * Trades readability for compactness


This proposal aims to relieve these tensions, maintaining compactness, human readability, and still guaranteeing uniqueness of the hash.  

!!! danger

    This proposal does not really detail a proper 'hash', as individual step's information (step name, parameter names/values, ...) is not
	enough info by itself to determine the resulting 'hash'.  Rather the hash is dependent upon the number of instances of a step, i.e.
	an ordering/enumeration.

## Parameter Combinations

A core identifier of a Maestro step instance is the parameter combination.  We shall refer to a simple study below to illustrate how parameter combinations work and the different kinds that can be attached to a study step instance.

### Demo Study Spec
``` yaml
description:
  name: parameter_combo_demo
  description: |
      Simple study used to demonstrate parameter combinations and a new
	  workspace/step hashing implementation
	  
study:
  - name: donor-sim
    description: Simple step using a subset of parameters
	run:
	  cmd: |
	    echo "Used Parameters: RES: $(RES)"
		
  - name: acceptor-sim
    description: Simple step using all parameters
	run:
	  cmd: |
	    echo "Used Parameters: RES: $(RES), SHIFT_X: $(SHIFT_X)"
		
global.parameters:
  RES:
    values: [1, 1, 2, 2]
	labels: RES.%%
	
  SHIFT_X:
    values: [3, 5, 3, 5]
```

### Demo Study Parameter Combinations
This results in the following set of parameter combinations:

| **Parameter** | **Combo 1** | **Combo 2** | **Combo 3** | **Combo 4** |
| :-----------: | :---------: | :---------: | :---------: | :---------: |
| RES           |           1 |           1 |           2 |           2 |
| SHIFT_X       |           3 |           5 |           3 |           5 |

Now we take into account the concept of 'used parameters', which is what Maestro uses under the covers to build the graph of instantiated steps.  Each column in this table represents one parameter combination, for a toatal of four.  As there are four unique values of these tuples, any step using both parameters (the steps' used parameters) will have four instances.  We see `acceptor-sim` uses both, so we have four instances of this step in the study. However, `donor-sim` only uses one of the parameters, `RES`, and we can see there are only 2 unique values, leading to only two instances of `donor-sim`, as shown in the topology below:

### Demo Study Topology
``` mermaid
flowchart TD;
    A(study-root) --> donor_sim_1;
	subgraph donor_sim_1 [donor-sim]
	  subgraph S1COMBO1 [Donor-Sim Used Combo 1]
	    B(RES = 1);
      end
	end
	A --> donor_sim_2;
	subgraph donor_sim_2 [donor-sim]
	  subgraph S1COMBO2 [Donor-Sim Used Combo 2]
	    C(RES = 2);
      end
	end
	donor_sim_1 --> step_2_1;
	subgraph step_2_1 [acceptor-sim]
	  subgraph S2COMBO1 [Acceptor-Sim Used Combo 1]
	    D(RES = 1\nSHIFT_X = 3);
      end
	end
	donor_sim_1 --> step_2_2;
	subgraph step_2_2 [acceptor-sim]
	  subgraph S2COMBO2 [Acceptor-Sim Used Combo 2]
	    E(RES = 1\nSHIFT_X = 5);
      end
	end	
	donor_sim_2 --> step_2_3;
	subgraph step_2_3 [acceptor-sim]
	  subgraph S2COMBO3 [Acceptor-Sim Used Combo 3]
	    F(RES = 2\nSHIFT_X = 3);
      end
	end
	donor_sim_2 --> step_2_4;
	subgraph step_2_4 [acceptor-sim]
	  subgraph S2COMBO4 [Acceptor-Sim Used Combo 4]
	    G(RES = 2\nSHIFT_X = 5);
      end
	end
```

### Demo Step Names

#### Default Naming ~v1.1

Default names for steps, and workspaces, uses the parameter labels as of v1.1.11, current release as of this draft.  These labels are meant to be more human friendly formats of parameter name.values that identify a specific parameter value.  Step/workspace naming uses the used parameter combinations' labels, as shown below:

| **Used Combo \#**   | **Step Name/Workspace Name** |
| :-----------:       | :---------:                  |
| donor-sim used combo 1 | donor-sim_RES.1             |
| donor-sim used combo 2 | donor-sim_RES.2             |
| acceptor-sim used combo 1 | acceptor-sim_RES.1.SHIFT_X.3   |
| acceptor-sim used combo 2 | acceptor-sim_RES.1.SHIFT_X.5   |
| acceptor-sim used combo 3 | acceptor-sim_RES.2.SHIFT_X.3   |
| acceptor-sim used combo 4 | acceptor-sim_RES.2.SHIFT_X.5   |

## Proposed New Hashing Scheme

A simple, readable hashing scheme is evident in the examples above: `<step-name>_<used_combination_ID>`, where `used_combination_ID` is the step specific used combination numbers, since each step can have it's own set of combinations, and varying numbers of combinations per step.  This per-step nature leads to the base step name being retained as a prefix to ensure it's clear that `used_combination_1` in `donor-sim`'s workspaces is not the same as that within `acceptor-sim`'s workspaces.

### Demo Hashing/Workspaces

| **Used Combo \#**   | **Sorted Parameter Values** | **Hashed step id/workspace** |
| :-----------:       | :---------:                 | :---------:                  |
| donor-sim used combo 1 | RES: 1                  | donor-sim_used_combination_1    |
| donor-sim used combo 2 | RES: 2                  | donor-sim_used_combination_2    |
| acceptor-sim used combo 1 | RES: 1, SHIFT_X: 3      | acceptor-sim_used_combination_1    |
| acceptor-sim used combo 2 | RES: 1, SHIFT_X: 5      | acceptor-sim_used_combination_2    |
| acceptor-sim used combo 3 | RES: 2, SHIFT_X: 3      | acceptor-sim_used_combination_3    |
| acceptor-sim used combo 4 | RES: 2, SHIFT_X: 5      | acceptor-sim_used_combination_4    |

### Hash construction/parameter ordering

Owing to the use of set intersections for determining id's and connectivity, much order information is lost once graph expasion is done.  To keep things simple and ~intuitive, all the used combinations will use sorting basd on parameter names, and then values, with used_combination number counting up from one from that sorted list.  This is reflected in the prior workspace/combo table <!-- INSERT LINK -->

### Study Metadata

There will be some corresponding tweaks to the parameters.yaml metadata to expose the step specific used parameter combinations in addition to the full set of parameter combinations.  This is to facilitate quick lookups of parameter values, e.g. bash or zsh shell functions to quickly get this information via yq <!-- link! -->, pipe it into fzf and then onto cd/pushd for study workspace navigation where you can select step workspaces based on human readable parameter name: value tables, or other quick lookups.  This expands upon the current parameters.yaml which only contained the full parameter combinations, requiring sometimes expensive operations to find the one corresponding to a current step that only uses a subset of parameters.

!!! question

    Add snippets of parameters.yaml, both old and new, and also demo gif of yq + fzf dir navigation workflow?

## Additional Considerations

### Adding parameter combinations to existing study

Consider a hypothetical feature to enable running new parameter combinations through an existing completed study.  The additional step instances such a process creates makes a bit of a mess of the naming convention given there are no guarantees on the ordering of the values in such new combinations being > what's already there. So what solutions could there be for this:

- Don't allow adding new parameter combinations to existing study workspace (current behavior)
- Dynamic renaming: this would be very disruptive and make a mess of any metadata slurped up into anything else as both that and the workspace paths would be changed
- Ignore the tuple style ordering on the names and values after the initial batch: i.e. compute that up front with local ordering per batch of parameters, but join them based on insert order.
    - Not very intuitive for users given lack of indicator when that order assumption changes if we don't also perturb the name of the combination
- Add a new suffix/prefix to the new steps to indicate the break in ordering.  There are a few options:
    - **group**: Pretty self explanatory marker for a new batch of parameter combinations
    - **batch**: Same as above
    - **movement**: More music themed name for the different groups/sets
    - **set**: Still ~self explanatory, but also overloaded with the music theme.  Bonus for being more compact than movement
    - Others, that start deviating: **chorus** (repeating sections of music), **verse** (..), **wave**, ...
  
  
Here's what a few of the options might look like, either omitting or includign the suffix on even the initial batch if such a feature is enabled, or making it implicit (first batch, i.e. no suffix on the first group, only adding it if a second batch of parameter combinations is run thorugh the study):

<!-- NOTE: aliasing/filtering step names falls into this same troublesome bucket where new parameters may violate any uniqueness constraints -->

### Multi-machine workflows

Given multi-machine workflows are on the roadmap, there's yet another wrench to throw into the works: what to do with the resource sets, i.e. procs, nodes, ... These are frequently templated with parameters just like the body of the steps.  However, what does this specific set of parameters, or even a condensed 'resource_set_id' grouping of them mean in this context?  Simply removing them from this naming, i.e. filtering them from the combination id/sorting order, is not an option as that may interfere with resolution and scaling studies where they may be the source of uniqueness relative to other combinations in the set.  Further complicating this is that they may not be single valued per step instance in a given study when extrapolated to the multi-machine context.  Currently available hardware spans a range of resource sets that may fit a given step's requirements, limiting our selves to exclusive usage for now as on a node-scheduled HPC cluster:


| **Resource Set ID** | **Tasks** | **Cores per node** | **Nodes** | **GPUS** |
| :-----------------: | :-------: | :----------------: | :-------: | :------: |
| rs_cpu_1            | 144       | 36                 | 4         | 0        |
| rs_cpu_2            | 112       | 56                 | 2         | 0        |
| rs_cpu_3            | 112       | 112                | 1         | 0        |
| rs_cpu_4            | 192       | 96                 | 2         | 0        |
| rs_cpu_5            | 128       | 128                | 1         | 0        |
| rs_gpu_1            | 4         | 112                | 1         | 4        |
| rs_gpu_2            | 4         |  96                | 1         | 4        |
