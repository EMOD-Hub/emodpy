# FAQ

Several common questions are answered below. If you are using a disease-specific emodpy package, see the FAQs from that package for additional guidance.

#### Why does emodpy download a new Eradication binary each time I run?

The emodpy package is designed to work much like a web browser: when you go to a website, the browser downloads html, png, and other files. If you visit the page again, it downloads them again so you always have the most current files.

We want emodpy to work in much the same way. When you run simulations, emodpy will download the latest tested binary, schema, and supporting files that from the relevant EMOD ongoing branch.

#### What is the purpose of manifest.py?

The manifest.py file contains *all* of your input and output paths in a single location. It also includes the path where model binaries (and associated schema) are downloaded to and uploaded from. Although you may ignore these files, it can be helpful to reference the schema for parameter information and have access to the binary itself.

#### I want to load a demographics.json file, not create one programmatically.

Okay, but be aware that one of the benefits of emodpy and emod-api is that you get guaranteed consistency between demographics and configuration parameters to meet all interdependencies. However, if you want to use a raw demographics.json that you are very confident in, you can open that in your demographics builder.

#### Why are the example.py scripts read from the bottom?

A Python script's "main" block, which is also the entry point to the run script, appears at the end so that all the functions in the script have been parsed and are available. It is a common convention to structure the call flow bottom-up because of that.

#### My simulation failed on COMPS but I didn't get an error until then

The OS of the requested executable and the OS of the target platform need to match. For example, if your target platform is Calculon, the default, you'll have to use a Linux build. There are no protections at this time (nor planned) to catch such misconfigurations.

#### What if I need a new or different SIF with a different custom environment?

Anyone is free to create SIFs for themselves and use those. COMPS can build SIFs for you provided a definition (.def) file. There are people at IDM who can do it on their desktops. Bear in mind Singularity really only installs on Linux.

#### What does "DTK" stand for?
Disease Transmission Kernel. This was the early internal name of EMOD.

#### What is a "parameter sweep"?

When the docs refer to a "parameter sweep", it usually means an experiment consisting of a multiple simulations where almost all the input values are the same except for a single parameter. The parameter being swept will have different values across a range, possibly the min to the max, but any range of interest to the modeler. Parameter sweeps can be very useful for just learning the sensitivity of a given parameter, or as a form of manual calibration. A "1-D parameter sweep" is where you just sweep over a single parameter. You can also do "2-D parameter sweeps", where you sweep over two parameters at once, and so on. But these of course require more simulations and more detailed visualization.

A special kind of parameter sweep is sweeping over Run_Number which is the random number seed. This kind of sweep gives you a sense of the model to general stochasticity, given your other inputs.

You can sweep over config, demographics, or campaign parameters.

#### Is there any place where I can see which parameters are taken from distributions and what type of distributions are they?

Any parameter that is being set from a distribution will have the distribution type in the name. E.g., Base_Infectivity_Gaussian_Mean tells you that this value is being drawn from a Gaussian distribution. If you don't see any distribution name in the parameter name, it's just fixed at that parameter value.
