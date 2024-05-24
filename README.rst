Herringlib
==========

Since Herring was just retired, it is apropos that Herringlib also be retired.
------------------------------------------------------------------------------


This is a set of development tasks for use with the Herring make utility (a python rake).

Installation
------------

Clone to either ~/.herring/herringlib or path_to_python_project/herringlib

Recommended to install unionfs-fuse then clone this herringlib to ~/.herring/herringlib and create
path_to_python_project/herringlib where you can put project specific tasks.

Usage
-----

Here a typical project creation example::

    cd path_to_python_project
    touch herringfile
    herring project::init \
    --name PROJECT_NAME \
    --package PACKAGE_NAME \
    --author "Your Name" \
    --author_email YOUR@REAL.EMAIL \
    --description "A short description of project"

where::

    PROJECT_NAME should not have any spaces
    PACKAGE_NAME is usually the lowercase of PROJECT_NAME where hyphens have been converted to underscores

Now edit herringfile, setup.py, and docs/conf.py

Next create your projects virtualenv with::

    herring project::mkvenvs

Now you are ready to go to town.  Here's the normal build cycle::

    herring version::bump
    git add ...
    git commit -m 'blah, blah'
    herring test
    herring build
    herring deploy
    herring doc
    herring doc::publish

Rinse and repeat.

