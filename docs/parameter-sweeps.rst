====================================
Parameter sweeps and model iteration
====================================

.. contents:: Contents
   :local:

Parameter sweeps for model calibration
======================================

(more info)
For more information on model calibration, see :doc:`calibrate`.


Parameter sweeps and stochasticity
==================================

.. this is the "iteration" bit
.. this should not be EMOD specific

With a stochastic model (such as |EMOD_s|), it is especially important to utilize parameter sweeps,
not only for calibration to data or parameter selection, but to fully explore the stochasticity in
output. Single model runs may appear to provide good fits to data, but variation will arise and
multiple runs are necessary to determine the appropriate range of parameter values necessary to
achieve  desired outcomes. Multiple iterations of a single set of parameter values should be run to
determine trends in simulation output: a single simulation output could provide results that are due
to random chance.



How to do parameter sweeps
==========================
