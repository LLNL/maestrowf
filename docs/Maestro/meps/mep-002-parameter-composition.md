<!-- NOTE: sort out how to get extra metadata/tags in here for doc generation -->

# MEP 002 - Parameter Composition: Add common operators to study specification an pgen

## Abstract

The default parameter value construction in Maestro is limited to explicit value lists in the study specification. While pgen <!-- INSERT LINK --> facilitates arbitrary construction via python, there are a variety of common operations that are used in composing parameters that could benefit from an api to reduce user boilerplate code.  This proposal outlines a set of basic operations to enable support for along with a UI for working with them directly in the yaml formatted study specification and a corresponding set of functionality available in pgen.  Maestro aims to be minimal on dependencies and not pin all users to particular solutions where possible.  This proposal takes care to maintain that.  The goal is for the core features and operations to depend only upon standard library utilities, with the excellent itertools library facilitating much of this.  There are still many operations that cannot be supported this way, such as the expansive space around statistical methods for generating values, e.g. latin hypercube, random number generation, etc.  For such capabilities a plugin interface will be detailed to enable seamless addition of workflow specific operations that don't require all Maestro users to use the same sampling libraries.

## Common Operations

Here we detail a base set of operators to provide out of the box for building and composing parameter combinations.

`List`

:   Explicit list of values (currently the only method available in `global.parameters` block in the study specification)

`Range`

:   Create value lists using start, stop, and increment (see `range` python function)

`Linspace`

:   Linear sampling between start, stop points, creating `N` intervals

`Random`

:   TODO: fill out the many ways to build random numbers using the standard lib (distributions, seeds, float vs int vs strings (i.e. sample from a list of values))...

`Zip`

:   Compositional operator, as with pythons' zip function, used to create lists of tuples built from other lists

`Batched`

:   Build lists of tuples from a single list,  (see itertools' batched)

`Repeat`

:   Replicate a constant value: i.e. wrap a single value parameter before handing off to zip to combine it with another explicit list. (NOTE: should this just take the 'N' argument instead of requiring going through zip?)

`Reverse`

:   Transformational operator, reversing an existing list of values before combining with other parameters

`Slice`

:   Slice and dice and existing list of values to subset and exsiting list of values

`Sort`

:   Rearrange an existing list of values on some criteria

`Randomize`

:   Randomize the order of an existing list of values

`Uniquify` <!-- Set? -->

:   Reduce a list of values to the set of unique values in it

`Cycle`

:   Enable indexing beyond the end of a list of values; e.g. wrap a parameter in cycle before combining it with another longer list of values in the zip operator

`Product`

:   Take a cross product of two or more parameters (should we have inner and outer products?)

`Permute`

:   Generate permutations from a list of values, or between values of multiple lists


## Study Specification Interface

A new block is proposed for the spec to avoid adding Maestro version specific behavior changes to the `global.parameters` block, leaving that as the default interface for explicit lists of parameters/parameter values.  An intial name for this block of `parameters.compose` will be used in the examples below.  THere are two important differences between this block and `global.parameters`:

1.  Intermediate, anonymous/temporary parameters are supported.  This facilitates parameter construction using multiple chained operations without either making those chained operations overly complex or requiring that these intermediates show up in the final parameter combinations.

2.  A reserved key for assigning a specific named chain of operations to be used as the set of parameter combinations in this study.  This facilitates having multiple operations defined and being able to subselect them by changing/overriding one value instead of swapping out the entire block.
   
    !!! warning
	
	    This block structure/key may change to be more like separate blocks, chosing one of those by name modulo feedback on the interfaces.  Could be helpful to use separate blocks for more clear organization of parameters, but may still want to share between blocks to reduce duplication.
		
		
### Examples

#### `global.parameters` behavior in composition block

This simple case shows how to replicate the behavior of the existing `global.parameters` block via composition operations using two slightly different options, both resulting in the same set of parameter combinations

=== "Direct Operator"

    ``` yaml
      INITIAL_VELOCITY:
        values: [0.1, 0.2, 0.3]
    	labels: "INIT_VEL.%%"
    	
      STOP_TIME:
        values: [4.0, 2.0, 1.0]
    	labels: "ST.%%"
    	
      PARAMETER.COMBINATIONS:        # (1)
        operator: zip
		inputs: [INITIAL_VELOCITY, STOP_TIME]
    ```
    
    1. Here we identify what composition defines the parameter combinations for this study
	
=== "Intermediate Composition"

    ``` yaml
      INITIAL_VELOCITY:
        values: [0.1, 0.2, 0.3]
    	labels: "INIT_VEL.%%"
    	
      STOP_TIME:
        values: [4.0, 2.0, 1.0]
    	labels: "ST.%%"
      
	  PARAMETERS:  # (1)
	    operator: zip
		inputs: [INITIAL_VELOCITY, STOP_TIME]
		
      PARAMETER.COMBINATIONS:        # (2)
        composition_id: RES_STUDY
    ```

    1. An intermediate combination
    2. Here we identify what composition defines the parameter combinations for this study


The resulting set of parameter combinations:

| **Parameter** | **Combo 1** | **Combo 2** | **Combo 3** |
| :-----------: | :---------: | :---------: | :---------: |
| INITIAL_VELOCITY | 0.1 | 0.2 | 0.3 |
| STOP_TIME        | 4.0 | 2.0 | 1.0 |

#### Tuples and cross products

Consider the case of having an existing set of configurations and you want to perturb each one the same way, such as a resolution study

``` yaml
parameters.compose:

  INITIAL_VELOCITY:
    values: [0.1, 0.2, 0.3]  # NOTE: should we replace values with list here?  force operators in this block all the time?
	labels: "INIT_VEL.%%"    # Use familiar Maestro syntax for generating human readable string representation of values
	
  STOP_TIME:
    values: [4.0, 2.0, 1.0]
	labels: "ST.%%"
	
  RESOLUTION:
    values: [1, 2]
	labels: "RES.%%"
	
  GROUP1:                     # (1)
    operator: zip
	inputs: [INITIAL_VELOCITY, STOP_TIME]  # (2)
	
  RES_STUDY:
    operator: product
	inputs: [GROUP1, RESOLUTION]
	
  PARAMETER.COMBINATIONS:        # (3)
    composition_id: RES_STUDY
```

1. An intermediate combination
2. Apply zip to the list of named parameters or compositions
3. Here we identify what composition defines the parameter combinations for this study

The resulting set of parameter combinations:

| **Parameter** | **Combo 1** | **Combo 2** | **Combo 3** | **Combo 4** | **Combo 5** | **Combo 6** |
| :-----------: | :---------: | :---------: | :---------: | :---------: | :---------: | :---------: |
| INITIAL_VELOCITY | 0.1 | 0.1 | 0.2 | 0.2 | 0.3 | 0.3 |
| STOP_TIME        | 4.0 | 4.0 | 2.0 | 2.0 | 1.0 | 1.0 |
| RESOLUTION       | 1   | 2   | 1   | 2   | 1   | 2   |


