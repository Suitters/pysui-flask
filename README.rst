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

Only administrators of the pysui-flask setup can provision new accounts. Once account provisioned, user can
login or logoff, change passwords, submit transactions and sign or deny signing a transaction.

Endpoint: **/account/login** - Post with user name and password payload, establishes session

Endpoint: **/account/logoff** - Post. Ends session.

Endpoint: **/account/password** - Post with new password payload.


--------------------------
Transactions
--------------------------

When a transaction is posted for execution to pysui-flask it does not execute immediatley.
Instead:

#. The accounts for required signatures of the transaction get a queued signing request record.
#. Accounts then fetch pending signature requests.
#. Accounts can then either sign and approve or reject the request.
#. Once all required signatures are returned approved, the transaction is submitted to Sui for execution.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Submit Transaction for Execution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Endpoint: **/account/transaction/execute** - Post serialized base64 SuiTransaction

Transactions can be submitted (requestor) by any Account. The transaction payload fields

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
Signers
^^^^^^^^^^^^^^^^^^^^^^^^^^

At a maximum 2 Signers, in the execution payload (transaction or template), can be specified: Sender and Sponsor.
Either can reference a single user Account or a MultiSig. If not provided, the requestor is considered to be the
transaction `sender`. Signer payload

.. code-block::

    # Can be multi-sig, single active-address or None (default to requestor)
    sender: Optional[Union[MultiSig, str]] = None

    # Can be multi-sig, single active-address or None (default to requestor)
    sponsor: Optional[Union[MultiSig, str]] = None

If either sender or sponsor are strings, it is the Sui address string of the user Account.

A MultiSig signer payload requires the MultiSig provisioned Sui address and the subset of the provisioned
MultiSig members Sui addresses

.. code-block::

    # This is the active-address of the provision MultiSig
    msig_account: str

    # Optionally these are active_addresses for the MultiSig members who are
    # required to sign. If None, all members must sign
    msig_signers: Optional[list[str]] = None


^^^^^^^^^^^^^^^^^^^^^^^^^^
Query Signing Requests
^^^^^^^^^^^^^^^^^^^^^^^^^^

Endpoint: **/account/signing-requests** - Get signing requests for account.

When submitted, default signer (account submitter) or those indicated in `signers` get a signing request queued to their account.
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

    # Base64 serialized SuiTransaction to sign
    tx_bytes: str

    # Status of request. May be one of:
    # 1 - pending signature
    # 2 - previously signed
    # 3 - previously denied
    status: int

^^^^^^^^^^^^^^^^^^^^^^^^^^
Sign or Reject
^^^^^^^^^^^^^^^^^^^^^^^^^^

Endpoint: **/account/sign** - Post a signed transaction or deny the signature.

Receiver signs the SuiTransaction serialized base64 tx_bytes in request and submits back

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
Administration
--------------------------

Administrators provision new Accounts and MultiSigs.

Endpoint: **/admin/login** - Post with admin user name and password payload, establishes session

Endpoint: **/admin/logoff** - Post. Ends session.

The admin uername and password are part of the `pysui-flask` configuration.

^^^^^^^^^^^^^^^^^^^^^^^^^^
Provision user Account
^^^^^^^^^^^^^^^^^^^^^^^^^^

Endpoint: **/admin/account** - Post (provision) a new user Account
Endpoint: **/admin/accounts** - Post (provision) a list of new user Account

User Accounts are required to perform transaction operations and/or participate in signing.

.. code-block::

    # Account user name string
    username: str

    # Account user password string, this is hashed before persisting
    password: str

    # The Accounts Sui public key base64 string or wallet paylod
    public_key: Union[str, dict]

If you are geneating an account from a wallet then the wallet payload (dict)

.. code-block::

    # The Sui key scheme for the public key
    key_scheme: str     # One of ED25519, SECP256K1, SECP256R1

    # The hex string of the public key from wallet.
    wallet_key: str


^^^^^^^^^^^^^^^^^^^^^^^^^^
Provision MultiSig
^^^^^^^^^^^^^^^^^^^^^^^^^^

Endpoint: **/admin/multisig** - Post (provision) a new MultiSig

The members of the MultiSig payload must be existing user Accounts

.. code-block::

    # A list of members of the MultiSig
    members: list[dict]

    # A name to assign the MultiSig
    name: str

    # The signing threshold (sum of weights of members when signing)
    threshold:int

The individual MultiSig members payload

.. code-block::

    # The members Sui address
    account_key:str

    # The weight the signature of this member contributes to the threshold (max val 255)
    weight: int

--------------------------
Templates
--------------------------

User Accuonts and create and execute reusable SuiTransaction called Templates.

A Template is a serialized SuiTransaction that can shared or private and cen control which
inputs may be overridden when executed.

^^^^^^^^^^^^^^^^^^^^^^^^^^
Create Template
^^^^^^^^^^^^^^^^^^^^^^^^^^

Endpoint: **/account/template** - Post (create) a new Template

New Template payload

.. code-block::

    # Name of the template
    template_name: str

    # Version of the template
    template_version: str

    # Base64 serialized SuiTransaction
    template_builder: str

    # Owned "1" or Shared "2"
    template_visibility: str

    # List of overrides or string ("all", "none")
    template_overrides: Union[list[dict], str]

Template override payload

.. code-block::

    # The zero based input index that can be overridden
    input_index: int

    # Flag indicating that input override must (True) be done in order to execute or not (False)
    override_required: bool

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Submit Template for execution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Endpoint: **/account/template/execute** - Post a Template as a Transaction

.. code-block::

    # Unique Template ID
    tx_template_id: int

    # Input overrides. If none given, template is executed as created
    input_overrides: Optional[list[dict]]

    # Same as Submit Transaction for Execution
    verify: Optional[bool] = None

    # Same as Submit Transaction for Execution
    gas_budget: Optional[str] = None

    # Same as Submit Transaction for Execution
    gas_object: Optional[str] = None

    # Same as Submit Transaction for Execution
    signers: Optional[Signers] = None

Template execution overrides. Override values **must be** of type defined in the templates
input value type

.. code-block::

    # The zero based input index that is being overridden
    input_index: int

    # The override value. If string it is assumed to be a 'object' and the value
    # is the Sui Object ID that expands to object reference.
    # Otherwise if list of bytes it is assumed to be a 'pure' value
    input_value: Union[str, list]


--------------------------
Configuration
--------------------------
