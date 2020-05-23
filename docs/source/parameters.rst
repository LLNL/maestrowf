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
  find another sampling algorithm: latin hypercube, or something else from scikit-learn? what about stats models?

What about adding reference of env block in pgen? (not modifying, just referencing)


First, lets use the excellent built-in package itertools to progammatically generate the parameters in the lulesh example specification:

.. code-block:: python
   :name: itertools_pgen.py
   :caption: itertools_pgen.py
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

Pgen Arguments
**************

There is an additional pgen feature that can be used to make them more dynamic.  The above example generates a fixed set of parameters, requiring editing the itertools_pgen.py file to change that.  Maestro supports passing arguments to these generator functions on the command line:


.. code-block:: bash

   $ maestro run study.yaml --pgen itertools_pgen_pargs.py --parg "SIZE_MIN:10" --parg "SIZE_STEP:10" --parg "NUM_SIZES:4"

Each argument is a string in key:val form, which can be accessed in the generator function as shown below:

.. code-block:: python
   :name: itertools_pgen_pargs.py
   :caption: itertools_pgen_pargs.py
   :linenos:

   from maestrowf.datastructures.core import ParameterGenerator
   import itertools as iter
   
   def get_custom_generator(env, **kwargs):
       p_gen = ParameterGenerator()

       # Unpack any pargs passed in
       size_min = int(kwargs.get('SIZE_MIN', '10'))
       size_step = int(kwargs.get('SIZE_STEP', '10'))
       num_sizes = int(kwargs.get('NUM_SIZES', '3'))
       
       sizes = range(size_min, size_min+num_sizes*size_step, size_step)
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

Passing the pargs 'SIZE_MIN:10', 'SIZE_STEP:10', and 'NUM_SIZES:4' then yields the expanded parameter set:

.. table:: Sample parameters from itertools_pgen_pargs.py

   =========== ==== ==== ==== ==== ==== ==== ==== ==== ==== ==== ==== ====
    Parameter   Values
   ----------- -----------------------------------------------------------
    TRIAL        0    1    2    3    4    5    6    7    8    9   10   11
   ----------- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ----
    SIZE        10   10   10   20   20   20   30   30   30   40   40   40
   ----------- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ----
    ITER        10   20   30   10   20   30   10   20   30   10   20   30
   =========== ==== ==== ==== ==== ==== ==== ==== ==== ==== ==== ==== ====

The next few examples demonstrate using 3rd party librarys and breaking out the actual parameter generation algorithm into separate helper functions that the ``get_custom_generator`` function uses to get some more complicated distributions.  The first is a simple parameter distribution for single variables that's encounterd in polynomial interpolation and designed to suppress the Runge and Gibbs phenomena: chebyshev points.

.. code-block:: python
   :name: np_cheb_pgen_pargs.py
   :caption: np_cheb_pgen_pargs.py
   :linenos:
   
   from maestrowf.datastructures.core import ParameterGenerator
   import numpy as np

   def chebyshev_dist(var_range, num_pts):
       r = 0.5*(var_range[1] - var_range[0])

       angles = np.linspace(np.pi, 0.0, num_pts)
       xpts = r*np.cos(angles) + r
       ypts = r*np.sin(angles)
   
       return xpts
   
   def get_custom_generator(env, **kwargs):
       p_gen = ParameterGenerator()

       # Unpack any pargs passed in
       x_min = int(kwargs.get('X_MIN', '0'))
       x_max = int(kwargs.get('X_MAX', '1'))
       num_pts = int(kwargs.get('NUM_PTS', '10'))
       
       x_pts = chebyshev_dist([x_min, x_max], num_pts)

       params = {
           "X": {
               "values": list(x_pts),
               "label": "X.%%"
           },       
       }

       for key, value in params.items():
           p_gen.add_parameter(key, value["values"], value["label"])
    
       return p_gen

       
Running this parameter generator with the following pargs
 
.. code-block:: bash

   $ maestro run study.yaml --pgen np_cheb_pgen.py --parg "X_MIN:0" --parg "X_MAX:3" --parg "NUM_PTS:11"

results in the 1D distribution of points for the ``X`` parameter shown by the orange circles:

.. image:: pgen_images/cheb_map.png
