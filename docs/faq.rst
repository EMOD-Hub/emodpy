==========================
Frequently asked questions
==========================

As you get started with |EMODPY_s|, you may have questions. The most common
questions are answered below. If you are using a disease-specific |EMODPY_s|
package, see the FAQs from that package for additional guidance. For
questions related to functionality in related packages, see the following
documentation:

* :doc:`emod-generic:faq` for |EMOD_s|
* :doc:`idmtools:faq` for |IT_s|
* :doc:`emod_api:faq` for |emod_api|

.. contents:: Contents
   :local:

Why does |EMODPY_s| download a new Eradication binary each time I run?
======================================================================

|EMODPY_s| is designed to work much like a web browser: when you go to a
website, the browser downloads html, png, and other files. If you visit the
page again, it downloads them again so you always have the most current files.
We want |EMODPY_s| to work in much the same way. When you run simulations,
|EMODPY_s| will download the latest tested binary, schema, and supporting
files that from the relevant |EMOD_s| ongoing branch.

However, if you need the stability of working from an older version, you can
pass a Bamboo build number to :py:func:`emodpy.bamboo.get_model_files` to
download that build instead. If you want to manually add a binary and and
corresponding schema in the downloads directory to use, comment out the call
to :py:func:`emodpy.bamboo.get_model_files` and nothing new will be
downloaded.		

What is the purpose of manifest.py?
===================================

The manifest.py file contains *all* of your input and output paths in a
single location. It also includes the path where model binaries
(and associated schema) are downloaded to and uploaded from. Although
you may ignore these files, it can be helpful to reference the schema
for parameter information and have access to the binary itself.

I want to load a demographics.json file, not create one programmatically.
=========================================================================

Okay, but be aware that one of the benefits of |EMODPY_s| and |emod_api| is
that you get guaranteed consistency between demographics and configuration
parameters to meet all interdependencies. However, if you want to use a raw
demographics.json that you are very confident in, you can open that in your
demographics builder. For example::

    def build_demog():
        import emod_api.demographics.Demographics as Demographics
        demog = Demographics.from_file( "demographics.json" )
            return demog

What happens if I don't connect to the VPN?
===========================================

You must be connected to the |IDM_s| VPN to access Bamboo and download the
Eradication binaries (including plug-ins and schema). As an alternative, comment
out the call to :py:func:`emodpy.bamboo.get_model_files` in the code
and run the following (where "emod-disease" can be "emodpy-hiv", "emodpy-malaria",
or "emod-measles"::

    pip install emod-disease --upgrade
    python -m emod-disease.bootstrap

The model files will be in a subdirectory called "stash."

Why are the example.py scripts read from the bottom?
====================================================

A Python script's "main" block, which is also the entry point to the run
script, appears at the end so that all the functions in the script have been
parsed and are available. It is a common convention to structure the call
flow bottom-up because of that.

My simulation failed on |COMPS_s| but I didn't get an error until then
======================================================================

The OS of the requested Bamboo build plan and the OS of the target platform
need to match. For example, if your target platform is Calculon, the default,
you'll have to request a Linux build from Bamboo. There are no protections at
this time (nor planned) to catch such misconfigurations.
