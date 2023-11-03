"""""""""""
pysui-flask
"""""""""""

.. contents:: Overview
    :depth: 3

====================
Introduction
====================

**ALPHA ALPHA ALPHA** - Use tenderly, it's fragile!

While pysui-flask exposes *some* pysui SDK via RESTful API, the main features are
MultiSignature management, transaction and signing processing, and transaction Templates.

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

#. No private keys are required
#. Chain data can be queried by anyone (read operations)
#. Accounts can participate in transactions
#. Accounts must be provisioned into pysui-flask by admin
#. Accounts log in to create/submit transactions
#. MultiSignature configurations must be provisioned into pysui-flask by admin
#. Transactions submitted include sender and, optionally, sponser
#. Sender and sponsor may be single or multisig
#. Signing requests are queued to indivual accounts
#. Signing may be accepted (response includes signature of transaction bytes) or denied
#. When all signatures satisfied, submits transaction for execution
#. Define Templates which can be reused with zero or more optional input overrides
#. Templates can define overrides of input arguments, can also indicate an override is required
#. Templates visibility can be 'owned' or 'shared'
#. Template execution substitutes overridden inputs and 'submits' as a transaction


--------------------------
Transactions
--------------------------

""""""""""""""""""""""""""
Submitting Transactions
""""""""""""""""""""""""""

**Endpoint** `/account//pysui_txn`

Transactions can be submitted by any Account. The transaction payload fields

.. code-block::

    # Serialized pysui SuiTransaction base64 string
    tx_builder: str

    # Flag to verify transaction against Sui ProtocolConfig constraints
    verify: Optional[bool] = None

    # Explicit gas budget option
    gas_budget: Optional[str] = None

    # Explicit gas object option (gas comes from sponsor if indicated)
    gas_object: Optional[str] = None

    # Accounts to notify for signing, defaults to account submitting transaction
    signers: Optional[Signers] = None

When submitted, default signer (submitter) or those indicated in `signers` get a signing request queued to their account.
Accounts can query for any outstanding signature requests



--------------------------
MultiSignature
--------------------------

--------------------------
Templates
--------------------------
