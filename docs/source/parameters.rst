Parameters
==========

Parameter Generator (pgen)
**************************

Maestro's Parameter Generator (pgen) supports setting up more flexible and complex parameter generation.  Maestro's pgen is a user supplied python file that contains the parameter generation logic, overriding the global.parameters block in the yaml specification file.  To run a Maestro study using a parameter generator just pass in the pgen file to Maestro on the command line when launching the study:

.. code-block:: bash

   $ maestro run study.yaml --pgen pgen.py

The minimum requirements for making a valid pgen file is to make a function called ``get_custom_generator`` which returns a Maestro :py:class:`~maestrowf.datastructures.core.ParameterGenerator` object as demonstrated in the simple example below:

.. code-block:: python
   :linenos:

   from maestrowf.datastructures.core import ParameterGenerator
 
   def get_custom_generator(env, **kwargs):
       p_gen = ParameterGenerator()
       params = {
           "COUNT": {
               "values": [i for i in range(1, 10)],
               "label": "COUNT.%%"
           },
       }
    
       for key, value in params.items():
           p_gen.add_parameter(key, value["values"], value["label"])
    
       return p_gen


The object simply builds the same nested key:value pairs seen in the global.parameters block available in the yaml specification.

For this simple example above, this may not offer compelling advantages over writing out the flattened list in the yaml specification directly.  This programmatic approach becomes preferable when expanding studies to use hundreds of parameters and parameter values or requiring non-trivial parameter value distributions.  The following examples will demonstrate these scenarios using both standard python library tools and additional 3rd party packages from the larger python ecosystem.

EXAMPLES:
  Simple for loops and Itertools for pure python work (side by side with lulesh example)
  products, permutations and combinations
  pargs for dynamic generators

  section on 3rd party tools: note on virtualenvironments to make it work
  numpy/scipy for chebyshev distribution: use extra function in the pgen file
  find another sampling algorithm: latin hypercube, or something else from scikit-learn? what about stats models?

What about adding reference of env block in pgen? (not modifying, just referencing)


First, lets use the excellent built in package itertools to generate the parameters in the lulesh example specification:

.. code-block:: python
   :name: itertools_pgen.py
   :caption: itertools.pgen.py
   :linenos:

   from maestrowf.datastructures.core import ParameterGenerator
   import itertools as iter
   
   def get_custom_generator(env, **kwargs):
       p_gen = ParameterGenerator()

       sizes = (10, 20, 30)
       iterations = (10, 20, 30)

       size_values = []
       iteration_values = []
       trial_values = []
       
       for trial, param_combo in enumerate(iter.product(sizes, iterations)):
           size_values.append(param_combo[0])
           iteration_values.append(param_combo[1])
           trial_values.append(trial)
       
       params = {
           "TRIAL": {
               "values": trial_values,
               "label": "TRIAL.%%"
           },       
           "SIZE": {
               "values": size_values,
               "label": "SIZE.%%"
           },
           "ITER": {
               "values": iteration_values,
               "label": "ITER.%%"
           },           
       }

       for key, value in params.items():
           p_gen.add_parameter(key, value["values"], value["label"])
    
       return p_gen      

This results in the following set of parameters, matching the lulesh sample workflow:

.. table:: Sample parameters from itertools_pgen.py

   =========== ==== ==== ==== ==== ==== ==== ==== ==== ====
    Parameter   Values
   ----------- --------------------------------------------
    TRIAL        0    1    2    3    4    5    6    7    8
   ----------- ---- ---- ---- ---- ---- ---- ---- ---- ----
    SIZE        10   10   10   20   20   20   30   30   30
   ----------- ---- ---- ---- ---- ---- ---- ---- ---- ----
    ITER        10   20   30   10   20   30   10   20   30
   =========== ==== ==== ==== ==== ==== ==== ==== ==== ====
 
