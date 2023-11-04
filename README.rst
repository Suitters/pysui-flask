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
Accounts
--------------------------

Only administrators of the pysui-flask setup can provision new accounts. Once provision can
login or logoff, change passwords, submit transactions and sign or deny signing a transaction.

**Endpoint POST** `/account/login` - With user name and password, establishes session

**Endpoint POST** `/account/logoff` - Ends session

**Endpoint POST** `/account/password` - Changes the account password



--------------------------
Transactions
--------------------------

When a transaction is posted for execution to pysui-flask it does not execute immediatley.
Instead:

#. The accounts for required signatures of the transaction get a queued signing request record.
#. Accounts then fetch pending signature requests.
#. Accounts can then either sign and approve or reject the request.
#. Once all required signatures are returned approved, the transaction submitted to Sui for execution.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Submit Transaction for Execution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Endpoint POST** `/account/transaction/execute`

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

^^^^^^^^^^^^^^^^^^^^^^^^^^
Query Signing Requests
^^^^^^^^^^^^^^^^^^^^^^^^^^

**Endpoint GET** `/account/signing-requests`

When submitted, default signer (submitter) or those indicated in `signers` get a signing request queued to their account.
If there is explicit `signers`, a request is posted to each individual signer. This may include both a `sender` signer and
`sponor` signer. Either of which could be a MultiSignature (see below).

Accounts can query for any outstanding signature requests, return payload is array of 0 or more requests

.. code-block::

    # Unique request identifier
    id: int

    # Sui public key string of account to sign
    signer_public_key: str

    # Are they asked to sign as sender (1) or sponsor (2)
    signing_as: int

    # Base64 transaction bytes to sign
    tx_bytes: str

    # Status of request. May be one of:
    # 1 - pending signature
    # 2 - previously signed
    # 3 - previously denied
    status: int

^^^^^^^^^^^^^^^^^^^^^^^^^^
Sign or Reject
^^^^^^^^^^^^^^^^^^^^^^^^^^

**Endpoint POST** `/account/sign`

Receiver signs the tx_bytes in request and submits back

Signing payload

.. code-block::

    # Unique request identifier
    request_id: int

    # Accepted and signed
    accepted_outcome: {

        # Sui public key string of signer
        public_key: str

        # Sui address
        active_address: str

        # Signed bytes as base64 string

        signature: str
        }

Rejecting payload

.. code-block::

    # Unique request identifier
    request_id: int

    # Accepted and signed
    rejected_outcome: {

        # Small description of why rejected
        cause: str

        }


--------------------------
MultiSignature
--------------------------

--------------------------
Templates
--------------------------
