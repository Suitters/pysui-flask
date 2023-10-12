"""""""""""
pysui-flask
"""""""""""

.. contents:: Overview
    :depth: 3

====================
Introduction
====================

**ALPHA ALPHA ALPHA** - Use tenderly, it's fragile!

While pysui-flask exposes *some* pysui SDK via RESTful API, the main features are MultiSignature management and transaction processing

====================
Key Dependencies
====================

pysui-flask uses `pipenv <https://pypi.org/project/pipenv/>`_ for package dependency management and virutal environments

pysui-flask uses `suibase <https://suibase.io/>`_ for integration testing locally

====================
Setup for use
====================

#. Clone this repo
#. Change into repo folder
#. Activate virtual environment
#. Install packages

.. code-block::

    git clone git@github.com:Suitters/pysui-flask.git
    cd pysui-flask
    pipenv shell
    pipenv install

--------------------------
Validate
--------------------------

.. code-block::

    pytest

--------------------------
Running
--------------------------

.. code-block::

    flask run

====================
Theory of Operations
====================

#. Chain data can be queries by anyone (read operations)
#. Accounts (user accounts or multisigs) particpating in transactions must be provisioned by admin
#. Transactions submitted incllude sender and optionally sponsers
#. Sender and sponsors can be single or multisig
#. Signing requests are queued to indivual accounts
#. Signing may be accepted (response includes signature of transaction bytes) or denied
