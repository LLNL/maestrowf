<!-- NOTE: sort out how to get extra metadata/tags in here for doc generation -->

# MEP 001 - Encore: Study Chaning and Iteration

## Abstract

Optimization/iteration are common workflow patterns, and this Encore feature aims to
partially address that as a next layer on top of Maestro's existing behavior where
the unit of work being chained together is a Maestro study.  The most basic usecase
here is rerunning the the same study process, but passing different parameter values through
it, i.e. refining parameters in a grid search to converge upon some optimum, or to
reduce uncertainty metrics by adding additional samples in the parameter space.  Despite
aiming this at studies calling themselves, this also enables branching workflows, and
studies calling other comletely different ones.  The proposed changes outlined here will
focus primarily on the user facing/specification side of it, with an emphasis on how
to get data from previous studies in the chain, update variables and other env block
tokens, how to control the iterations/chaining, and global parameters.  New, always present
tokens will also be detailed.

<!-- TODO: add notes about how OUTPUT_PATH behaves in this mode -->
## User Interface

### New Tokens

Encore introduces a handful of new tokens with reserved names that are always available:

**Name**                    | **Description** | **Notes** |
:-                          |  :-             | :- |
`$(STUDY_ITER)`             | Current iteration of this study specification | 
`$(ENCORE_ITER)`            | Current iteration of this study + counts of all prev studies in the chain |
`$(ENCORE.parent.workspace)`| Path to parent studies' ``encore`` step workspace | Useful focus point for reaching back into studies to get data not easily passed by other tokens/parameters |
`$(ENCORE_PREV_RESULTS)`    | Path to parent study's ``encore.yaml`` | 
`$(ENCORE_ROOT)`            | Path to root of Encore study workspaces, which contains logs and per iteration study workspaces |

### Encore Step, Encore.yaml

Triggering an 'Encore' involves adding a special step named Encore and at a minimum
an ``encore.yaml`` file written inside it which passes information to Maestro about
whether to run an Encore, stop, and update any scalars/tokens in the subsequent
iteration.

At a minimum, this `encore.yaml` needs to contain one piece of information:
```yaml title="Minimal encore.yaml"
is_done: false
```

Setting this ``is_done`` key to true or false is how you tell Maestro whether your study needs
an 'encore' (another iteration) or not.  If no other information is provided, Maestro assumes
you want to iterate on the current study specification.  However, as study's cannot generate
parameters during execution, you will often want to pass in new values to parameters or update
env block tokens.

### Changing Parameters

Changing parameters can be done via two methods, just like a standard Maestro study.  The two examples
below assume a sample study that has a single parameter 'PARAM1', and we'll generate 4 new values
with both methods.

=== "``global.parameters``"

    In this scenario, the format to update parameters is a mapping of parameters contained in the
	``parameters`` key in the list of child_specs, with a structure identical to what you see in
	the Maestro study specification
	
    ```yaml title="Explicit parameter value specification in encore.yaml"
	is_done: false
	child_specs:
	  - name: $(CURRENT_SPEC)
	    parameters:
		  PARAM1:
		    values: [0, 0.2, 0.7, 0.01]
			labels: PARAM1.%%
	```
	
    !!! note
        Might want some 'helper functions' from maestro to write new ones into ``encore.yaml`` here?
		
=== "``pgen``"

    Invoke pgen, with or without args, using the ``pgen`` and ``pgen_args`` mappings in the list of
	child_specs.
	
	```yaml title="Call pgen with pargs to setup next iterations' parameters"
	is_done: false
	child_specs:
	  - name: $(CURRENT_SPEC)
	    pgen: pgen.py
		pgen_args:
		  - name: num_values
		    value: "4"
		  - name: value_range
		    value: "0,1"
	```
	
	This is equivalent to the cli invocation of a pgen that has pargs named 'num_values' and 'value_range':
	
	```shell
	maestro run encore_study.yaml --pgen pgen.py --parg "num_values:10" --parg "value_range:0,1"
	```
	
  
### Updating existing ``env`` block tokens


<!-- NOTE: is there a good way to enable pre-launch validation of encore.yaml? i.e. not ingesting any unknown tokens, etc -->

It is also possible to update the configuration set in the [Environment Block (``env``)](../specification#Environment Tokens) via the encore.yaml, on a per child study specification basis.

```yaml title="Parent study specification env block"
env:
  variables:
    TOKEN1: 1.0
	
  dependencies:
    paths:
	  - name: INPUT_DATA_FILE
	    path: initial_input_data.csv
```

You can reference these tokens in the encore.yaml and change the values:

```yaml title="Updating env tokens for the next iteration"
is_done: false
child_specs:
 - name: $(CURRENT_STUDY_SPECIFICATION)
   env:
     variables:
	   TOKEN1: 2.0
	 dependencies:
	   paths:
	     - name: INPUT_DATA_FILE
		   path: iteration_2_input_data.csv
```

!!! note
    Should we require users to write the `$(ENCORE.parent.workspace)` token in the `path` or just
	inline that in the generated study spec for that next iteration automatically?
	
We can enable error checking/error messaging by comparing these tokens with what's in the child_study,
making it easy to catch typos that result in new unused tokens.

### Dispatching multiple new studies

This results file can also be used to launch multiple new studies at once, which is most useful
in the case that the child study specifications aren't the same as the current one, i.e. where you
are changing more than just the parameter values.  This use case is where the list structure
of the ``child_specs`` item becomes important

=== "Dispatch two children with no parameters"

    In this scenario, the format to update parameters is a mapping of parameters contained in the
	``parameters`` key in the list of child_specs, with a structure identical to what you see in
	the Maestro study specification
	
    ```yaml title="Multiple child studies with no value/config inputs"
	is_done: false
	child_specs:
	  - name: child_study_A.yaml

      - name: child_study_B.yaml
	```
	
    !!! note
        Find a better use case to document this and help sort out passing data between these when
		it's not just parameters (i.e. workspace paths, consolidated data files, ...)
		
=== "Pass data to child specs"

    Placeholder for example to pass some sort of data to each child
	
	!!! note
	    What about dependencies here?  -> three children, with one dependent upon the other two for
		a case with multiple parents?

### Communicating/documenting the process

A core philosophy of Maestro is enabling reproducible science, and that means clearly documenting
the process.  To that end, a major question mark on this feature is what/if any indicators might
be useful in the spec to show that particular tokens are intended for use in the encore feature?
Seralization/creation of the ``encore.yaml`` file is likely to often be done in friendlier languages
than bash, such as python, which obscures the details of it from view in the study specification.
Thus, how are future users to know which/if any ``env`` block tokens are updated in each iteration?

As a motivating example, consider a simple Newton style optimizer which requires previous iteration
data to compute the new search direction and step size.  We will solve a simple system to illustrate
this: find the minimum value of a quadratic function

$$
y = ax^2 + bx + c
$$

A newton step (dx) for this would be

$$
\begin{gather*}
y_i &=& a x_i^2 + b x_i + c \\
dx &=& -\frac{2.0*a x_i + b}{2.0*c} \\
x_{i+1} &=& x_i + dx \\
y_{i+1} &=& a x_{i+1}^2 + b x_{i+1} + c \\
\end{gather*}
$$

For this to work we need an initial guess $x_i$, and we need to update that every iteration.  So
on iteration two, the $x_{i+1}$ computed in iteration 1 would need to be passed in to provide the
$x_i$.  Thus might have something like this in the ``env`` block of the spec to kick things off

```yaml title="Newton example's env block"
env:
  variables:
    X_INIT: 1.0
```

and then the following in the ``encore.yaml`` to update the token's value for the next iteration

```yaml title="Newton example's encore.yaml"
is_done: false
child_specs:
 - name: $(CURRENT_SPEC)
   env:
     variables:
	   X_INIT: <x_{i+1} computed in current iteration>
```

With only the information visible in the initial specification, there's no real indication that
``X_INIT`` is a token that will be updated every iteration: that info remains buried in the
supporting python script used to write out the ``encore.yaml`` with the new value from the current
iterations computed $x_{i+1}$.  Is there something we can/should tag/mark some tokens as 
overridable/updateable?

=== "Tag it with 'reserved' encore attributes"

    ```yaml
	env:
	  variables:
	    X_INIT:
		  encore_variable: True
		  value: 1.0
	```

=== "Generic interactive cli override tags"

    ```yaml
	env:
	  variables:
	    X_INIT:
		  value: 1.0
		  prompt: "Enter a starting point for the newton solver: single floating point number"
	```
	
	Here, ``prompt`` would be a way to both mark this as an overridable parameter, communicate that
	to future users, as well as provide a means of asking for values to be input when you call
	`maestro run ..` with some text to help guide the input.  Such a feature could also mark it
	for use by encore if a convention is adopted that only overridable tokens can be passed via
	``encore.yaml``.  The fact that encore may be modifying this is potentialy less immediately 
	clear when viewing a spec however.


### Optional Capabilities

Enabling multiple study dispatch upon the second iteration does open up a potentialy interesting
possibility: enabling study dependencies as each Maestro study does with steps.  I.e. in the below
example we can launch independent iterations of study1 and study2, and then execute study3 upon
completion of both of those

```yaml title="encore.yaml"
is_done: false
child_specs:
 - name: study2.yaml
   pgen: chained_pgen.py
 - name: study1.yaml
   pgen: chained_pgen.py
   pgen_args:
     - name: num_values
	   value: "10"
     - name: value_range
	   value: "0, 1"
 - name: study3.yaml
   depends: [study2, study3]
   ...
```

An open question remains: is this use case really needed/useful, or just adding extra complexity?
