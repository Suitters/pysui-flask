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

"""Pytest transaction testing."""

import json
import base64

from flask.testing import FlaskClient
from pysui_flask.api.xchange.payload import *
from tests.integration.utils import (
    PysuiAccount,
    account_data,
    login_user,
    logoff_user,
    sign_request_for,
    USER_LOGIN_CREDS,
    MSIG_LOGIN_CREDS,
    MSIG1_LOGIN_CREDS,
    MSIG2_LOGIN_CREDS,
)

from pysui import SyncClient, SuiAddress
from pysui.sui.sui_txn import SyncTransaction
import pysui.sui.sui_crypto as crypto


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
    response = sign_request_for(client, sui_client, USER_LOGIN_CREDS)


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

def _msig_data_by_name(name:str, block: list[dict]) -> dict:
    """Find msig account data block by name."""

    for msig in block:
        if msig["multisig_name"] == name:
            return msig
    return None


def _user_data_by_name(name:str, block: list[dict]) -> dict:
    """Find account data block by name."""

    for user in block:
        if user["user_name"] == name:
            return user
    return None

def _mmember_data_by_index(index:int, msig_block: dict,user_block:list[dict]) -> dict:
    """Find account data block by name."""
    member = msig_block["multisig_members"][index]

    for user in user_block:
        if user["account_key"] == member["owner_id"]:
            return user

    return None

def test_pysui_tx_with_msig(client: FlaskClient, sui_client: SyncClient, accounts:dict):
    """Test msig signing."""

    # Get Msig account_key
    msig_block = _msig_data_by_name("Msig01",accounts["multi_signatures"])
    msig_addy = SuiAddress(msig_block["active_address"])

    # Sync user
    _ = login_user(client, USER_LOGIN_CREDS)
    sender_account: PysuiAccount = account_data(client)
    sender_active_addy = SuiAddress(
        sender_account.active_address
    )
    # Create the transaction that puts gas in msig address
    txer = SyncTransaction(sui_client, initial_sender=sender_active_addy)
    scoin = txer.split_coin(coin=txer.gas, amounts=[10000000000])
    txer.transfer_objects(transfers=[scoin], recipient=msig_addy)
    txin = TransactionIn(
        tx_builder=base64.b64encode(
            txer.serialize(include_sender_sponsor=False)
        ).decode()
    )
    # Post the transaction
    response = client.post("/account/pysui_txn", json=txin.to_json())

    # Sign the transfer
    rfilt = SignRequestFilter(pending=True)
    response = client.get(
        "/account/signing_requests",
        json=rfilt.to_json(),
    )
    assert response.status_code == 200
    result = response.json
    assert len(result["result"]["signing_requests"]) == 1
    sign_request = result["result"]["signing_requests"][0]

    kp = sui_client.config.keypair_for_address(sender_active_addy)
    assert sign_request["status"] == 1

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
    _ = logoff_user(client)

    # Get 2 of the sigs
    mmem1_account = _mmember_data_by_index(0,msig_block,accounts["users"])
    mmem2_account = _mmember_data_by_index(1,msig_block,accounts["users"])


    # Create the transaction that puts some msig gas back to orig
    txer = SyncTransaction(sui_client, initial_sender=msig_addy)
    scoin = txer.split_coin(coin=txer.gas, amounts=[5000000000])
    txer.transfer_objects(transfers=[scoin], recipient=sender_active_addy)

    txin = TransactionIn(
        tx_builder=base64.b64encode(
            txer.serialize(include_sender_sponsor=False)
        ).decode(),
        signers=Signers(
            sender=MultiSig(
                msig_account=msig_block["active_address"],
                msig_signers=[
                    mmem1_account["active_address"],
                    mmem2_account["active_address"],
                ],
            )
        ),
    )
    # Post the transaction
    _ = login_user(client, USER_LOGIN_CREDS)
    response = client.post("/account/pysui_txn", json=txin.to_json())
    assert response.status_code == 201
    assert "error" not in response.json
    _ = logoff_user(client)
    response = sign_request_for(client, sui_client, MSIG1_LOGIN_CREDS)
    assert response.status_code == 201
    response = sign_request_for(client, sui_client, MSIG2_LOGIN_CREDS)
    assert response.status_code == 201
    result = response.json
    assert result["result"]["signature_response"] == "signed_and_executed"
    _ = login_user(client, MSIG2_LOGIN_CREDS)
    response = client.get(
        "/account/pysui_get_txn",
        json=json.dumps({}),
    )
    assert response.status_code == 200
    result = response.json
    assert result["result"]["transactions"]
    _ = logoff_user(client)

def test_pysui_tx_sponsor(client: FlaskClient, sui_client: SyncClient, accounts:dict):
    """Test msig signing."""

    # Get Msig account_key
    msig_block = _msig_data_by_name("Msig01",accounts["multi_signatures"])
    msig_addy = SuiAddress(msig_block["active_address"])

    # Get 2 of the sigs
    mmem1_account = _mmember_data_by_index(0,msig_block,accounts["users"])
    mmem2_account = _mmember_data_by_index(1,msig_block,accounts["users"])

    # Sync user
    sender_active_addy = SuiAddress(mmem1_account["active_address"])
    # Create the transaction that puts gas in msig address
    txer = SyncTransaction(sui_client, initial_sender=sender_active_addy)
    scoin = txer.split_coin(coin=txer.gas, amounts=[10000000000])
    txer.transfer_objects(transfers=[scoin], recipient=msig_addy)
    txin = TransactionIn(
        tx_builder=base64.b64encode(
            txer.serialize(include_sender_sponsor=False)
        ).decode(),
        signers=Signers(sender=mmem1_account["active_address"],sponsor=mmem2_account["active_address"])
    )
    # Post the transaction
    _ = login_user(client, MSIG1_LOGIN_CREDS)
    response = client.post("/account/pysui_txn", json=txin.to_json())
    _ = logoff_user(client)
    response = sign_request_for(client, sui_client, MSIG1_LOGIN_CREDS)
    assert response.status_code == 201
    response = sign_request_for(client, sui_client, MSIG2_LOGIN_CREDS)
    assert response.status_code == 201
    result = response.json
    assert result["result"]["signature_response"] == "signed_and_executed"
