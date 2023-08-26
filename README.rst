pysui-flask
===========

pysui-flask exposes pysui SDK via RESTful API

pysui-flask uses `pipenv <https://pypi.org/project/pipenv/>`_ for package dependency management and virutal environments

Setup for use
*************

#. Clone this repo
#. Change into repo folder
#. Activate virtual environment
#. Install packages

.. code-block::

    git clone git@github.com:FrankC01/pysui-flask.git
    cd pysui-flask
    pipenv shell
    pipenv install


Validate
********

.. code-block::

    pytest


Running
*******

.. code-block::

    cd pysui_flask
    flask run
