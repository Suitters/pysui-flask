#    Copyright Frank V. Castellucci
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#        http://www.apache.org/licenses/LICENSE-2.0
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

# -*- coding: utf-8 -*-

"""Pytest account routes."""
import json
import base64
from flask.testing import FlaskClient

from pysui_flask.api.xchange.payload import *
from pysui import SyncClient, SuiConfig
from pysui.sui.sui_txn import SyncTransaction

from tests.integration.utils import check_error_expect, login_user, logoff_user

USER_LOGIN_CREDS: dict = {"username": "FrankC015", "password": "Oxnard Gimble"}
MSIG_LOGIN_CREDS: dict = {"username": "Msig01", "password": "Oxnard Gimble"}
BAD_OPS_USER_LOGIN_CREDS: dict = {
    "username": "FrankC016",
    "password": "Oxnard Gimble",
}


def test_account_pre_login_root(client: FlaskClient):
    """Validate error on non-JSON and empty request."""
    response = client.get("/account/")
    check_error_expect(response, -5)


def test_bad_login_content(client: FlaskClient):
    """Validate error on bad account login credentials."""
    creds = {
        "username": "fastfrank",
        "password": "Slippery Slope",
    }
    response = login_user(client, creds)
    check_error_expect(response, -10)


def test_no_ops(client: FlaskClient):
    """Test account with no public key can't execute those that require."""
    response = login_user(client, BAD_OPS_USER_LOGIN_CREDS)
    assert response.status_code == 200
    response = client.get("/account/gas", json=json.dumps({"all": False}))
    check_error_expect(response, -1001)
    response = logoff_user(client)
    assert response.status_code == 200


def test_set_publickey(client: FlaskClient):
    """Test account with no public key can't execute those that require."""
    response = login_user(client, BAD_OPS_USER_LOGIN_CREDS)
    assert response.status_code == 200
    pubkey_wallet = {
        "public_key": {
            "key_scheme": "ED25519",
            "wallet_key": "qo8AGl3wC0uqhRRAn+L2B+BhGpRMp1UByBi8LtZxG+U=",
        }
    }
    response = client.post(
        "/account/public_key", json=json.dumps(pubkey_wallet)
    )
    assert response.status_code == 200
    result = response.json
    assert result["result"]["user_update"]
    response = client.get("/account/gas", json=json.dumps({"all": False}))
    assert response.status_code == 200
    result = response.json
    assert not result["result"]["data"]
    response = logoff_user(client)


# This session is used through end of module
def test_good_login_content(client: FlaskClient):
    """Validate good account login credentials."""
    response = login_user(client, USER_LOGIN_CREDS)
    assert response.status_code == 200
    result = response.json
    assert "result" in result and "session" in result["result"]
    _ = logoff_user(client)


# 0x94a1d8d13ad80563f307362f730e84691fa1cde7b83932abae0af2620c3e0855
def test_account_post_login_root(client: FlaskClient):
    """Validate error on non-JSON and empty request."""
    _ = login_user(client, USER_LOGIN_CREDS)
    response = client.get("/account/", json=json.dumps({}))
    assert response.status_code == 200
    result = response.json
    assert result["result"]["account"]["user_name"] == "FrankC015"
    assert result["result"]["account"]["user_role"] == 2
    _ = logoff_user(client)


# Sui Calls


def test_get_gas(client: FlaskClient):
    """Should have some gas."""
    _ = login_user(client, USER_LOGIN_CREDS)
    response = client.get("/account/gas", json=json.dumps({"all": False}))
    assert response.status_code == 200
    result = response.json
    assert result["result"]["data"][0]
    _ = logoff_user(client)


def test_get_objects(client: FlaskClient):
    """Should have some objects."""
    _ = login_user(client, USER_LOGIN_CREDS)
    response = client.get("/account/objects", json=json.dumps({"all": False}))
    assert response.status_code == 200
    result = response.json
    assert result["result"]["data"]
    _ = logoff_user(client)


def test_get_object(client: FlaskClient):
    """Should not be empty."""
    _ = login_user(client, USER_LOGIN_CREDS)
    response = client.get(
        "/account/object/0x5464b56a2ab51547cd7da5fe0e31278b833bf54d87df2be93c85b738f83cfb05",
        json=json.dumps({}),
    )
    assert response.status_code == 200
    result = response.json
    assert result["result"]["code"] == "notExists"
    _ = logoff_user(client)


def test_pysui_tx_inspect(client: FlaskClient, sui_client: SyncClient):
    """Test deserializing and inspecting a SuiTransaction."""
    txer = SyncTransaction(sui_client)
    scoin = txer.split_coin(coin=txer.gas, amounts=[1000000000])
    txer.transfer_objects(
        transfers=[scoin], recipient=sui_client.config.active_address
    )
    inspect_dict = {
        "tx_base64": base64.b64encode(
            txer.serialize(include_sender_sponsor=False)
        ).decode()
    }
    _ = login_user(client, USER_LOGIN_CREDS)
    response = client.get("/account/pysui_txn", json=json.dumps(inspect_dict))
    assert response.status_code == 200
    assert "error" not in response.json
    result = response.json
    _ = logoff_user(client)


def test_pysui_tx_verification(client: FlaskClient, sui_client: SyncClient):
    """Test deserializing and inspecting a SuiTransaction."""
    txer = SyncTransaction(sui_client)
    scoin = txer.split_coin(coin=txer.gas, amounts=[1000000000])
    txer.transfer_objects(
        transfers=[scoin], recipient=sui_client.config.active_address
    )
    inspect_dict = {
        "tx_base64": base64.b64encode(
            txer.serialize(include_sender_sponsor=False)
        ).decode(),
        "perform": "verification",
    }
    _ = login_user(client, USER_LOGIN_CREDS)
    response = client.get("/account/pysui_txn", json=json.dumps(inspect_dict))
    assert response.status_code == 200
    assert "error" not in response.json
    result = response.json
    assert isinstance(result["result"]["verification"], str)
    assert result["result"]["verification"] == "success"
    _ = logoff_user(client)


def test_no_signing_requests(client: FlaskClient):
    """Should be empty."""
    _ = login_user(client, USER_LOGIN_CREDS)
    response = client.get(
        "/account/signing_requests",
        json=json.dumps({}),
    )
    assert response.status_code == 200
    result = response.json
    assert not result["result"]["signing_requests"]
    _ = logoff_user(client)


def test_no_transactions(client: FlaskClient):
    """Should be empty."""
    _ = login_user(client, USER_LOGIN_CREDS)
    response = client.get(
        "/account/pysui_get_txn",
        json=json.dumps({}),
    )
    assert response.status_code == 200
    result = response.json
    assert not result["result"]["transactions"]
    _ = logoff_user(client)


def test_pysui_tx_execute(client: FlaskClient, sui_client: SyncClient):
    """Test deserializing and submitting a SuiTransaction."""
    txer = SyncTransaction(sui_client)
    scoin = txer.split_coin(coin=txer.gas, amounts=[1000000000])
    txer.transfer_objects(
        transfers=[scoin], recipient=sui_client.config.active_address
    )
    txin = TransactionIn(
        tx_builder=base64.b64encode(
            txer.serialize(include_sender_sponsor=False)
        ).decode()
    )
    _ = login_user(client, USER_LOGIN_CREDS)
    response = client.post("/account/pysui_txn", json=txin.to_json())
    assert response.status_code == 201
    assert "error" not in response.json
    result = response.json
    assert len(result["result"]["accounts_posted"]) == 1
    _ = logoff_user(client)


def test_sender_is_requestor_execute(
    client: FlaskClient, sui_client: SyncClient
):
    """Test execution after signing."""
    rfilt = SignRequestFilter(pending=True)
    _ = login_user(client, USER_LOGIN_CREDS)
    response = client.get(
        "/account/signing_requests",
        json=rfilt.to_json(),
    )
    assert response.status_code == 200
    result = response.json
    assert len(result["result"]["signing_requests"]) == 1
    sign_request = result["result"]["signing_requests"][0]
    kp = sui_client.config.keypair_for_address(
        sui_client.config.active_address
    )
    assert sign_request["status"] == 1
    assert (
        sign_request["signer_public_key"]
        == base64.b64encode(kp.public_key.scheme_and_key()).decode()
    )

    payload = SigningResponse(
        request_id=sign_request["id"],
        accepted_outcome=SigningApproved(
            public_key=sign_request["signer_public_key"],
            active_address=sui_client.config.active_address.address,
            signature=kp.new_sign_secure(sign_request.pop("tx_bytes")).value,
        ),
    )
    response = client.post(
        "/account/signing_request",
        json=payload.to_json(),
    )
    assert response.status_code == 201
    result = response.json
    response = client.get(
        "/account/signing_requests",
        json=rfilt.to_json(),
    )
    assert response.status_code == 200
    result = response.json
    assert not result["result"]["signing_requests"]
    _ = logoff_user(client)


def test_transactions(client: FlaskClient):
    """Test transaction was executed."""
    _ = login_user(client, USER_LOGIN_CREDS)
    response = client.get(
        "/account/pysui_get_txn",
        json=json.dumps({}),
    )
    assert response.status_code == 200
    result = response.json
    assert result["result"]["transactions"]
    _ = logoff_user(client)


def test_pysui_tx_execute_deny_sig(
    client: FlaskClient, sui_client: SyncClient
):
    """Test denying a signature request."""
    # Create the transaction
    txer = SyncTransaction(sui_client)
    scoin = txer.split_coin(coin=txer.gas, amounts=[1000000000])
    txer.transfer_objects(
        transfers=[scoin], recipient=sui_client.config.active_address
    )
    txin = TransactionIn(
        tx_builder=base64.b64encode(
            txer.serialize(include_sender_sponsor=False)
        ).decode()
    )
    # Post the transaction
    _ = login_user(client, USER_LOGIN_CREDS)
    response = client.post("/account/pysui_txn", json=txin.to_json())
    assert response.status_code == 201
    assert "error" not in response.json
    result = response.json
    assert len(result["result"]["accounts_posted"]) == 1
    # Get pending sig
    rfilt = SignRequestFilter(pending=True)
    response = client.get(
        "/account/signing_requests",
        json=rfilt.to_json(),
    )
    assert response.status_code == 200
    result = response.json
    assert len(result["result"]["signing_requests"]) == 1
    # Deny the signature
    sign_request = result["result"]["signing_requests"][0]
    kp = sui_client.config.keypair_for_address(
        sui_client.config.active_address
    )
    assert sign_request["status"] == 1
    assert (
        sign_request["signer_public_key"]
        == base64.b64encode(kp.public_key.scheme_and_key()).decode()
    )

    payload = SigningResponse(
        request_id=sign_request["id"],
        rejected_outcome=SigningRejected(
            cause="Don't want to",
        ),
    )
    response = client.post(
        "/account/signing_request",
        json=payload.to_json(),
    )
    assert response.status_code == 201
    result = response.json
    assert result["result"]["signature_response"] == "denied"
    _ = logoff_user(client)


def test_msig_login(client: FlaskClient):
    """Test logging in with the multisig account."""
    # Login with multisig
    response = login_user(client, MSIG_LOGIN_CREDS)
    assert response.status_code == 200
    result = response.json
    assert "session" in result["result"]
    # Get gas, should be empty
    response = client.get("/account/gas", json=json.dumps({"all": False}))
    assert response.status_code == 200
    result = response.json
    assert len(result["result"]["data"]) == 0
    _ = logoff_user(client)
