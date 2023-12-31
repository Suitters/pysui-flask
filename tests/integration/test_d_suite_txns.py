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
    USER3_LOGIN_CREDS,
    USER5_LOGIN_CREDS,
    USER6_LOGIN_CREDS,
    PysuiAccount,
    account_data,
    check_error_expect,
    login_user,
    logoff_user,
    sign_request_for,
    USER_LOGIN_CREDS,
    MSIG1_LOGIN_CREDS,
    MSIG2_LOGIN_CREDS,
    gas_not_in,
    address_not_active,
)

from pysui import SyncClient, SuiAddress
from pysui.sui.sui_txn import SyncTransaction
from pysui.sui.sui_txn.transaction_builder import PureInput
from pysui.sui.sui_types.scalars import SuiU64
import pysui.sui.sui_crypto as crypto


def test_pysui_tx_inspect(client: FlaskClient, sui_client: SyncClient):
    """Test deserializing and inspecting a SuiTransaction."""
    txer = SyncTransaction(client=sui_client)
    scoin = txer.split_coin(coin=txer.gas, amounts=[1000000000])
    txer.transfer_objects(transfers=[scoin], recipient=sui_client.config.active_address)
    inspect_dict = {
        "tx_base64": base64.b64encode(
            txer.serialize(include_sender_sponsor=False)
        ).decode()
    }
    _ = login_user(client, USER_LOGIN_CREDS)
    response = client.get(
        "/account/transaction/validate", json=json.dumps(inspect_dict)
    )
    assert response.status_code == 200
    assert "error" not in response.json
    result = response.json
    _ = logoff_user(client)


def test_template_owned(client: FlaskClient, sui_client: SyncClient):
    """Test creating a transaction Template."""
    txer = SyncTransaction(client=sui_client)
    scoin = txer.split_coin(coin=txer.gas, amounts=[1000000000])
    txer.transfer_objects(transfers=[scoin], recipient=sui_client.config.active_address)
    template_dict = {
        "template_name": "Template 1",
        "template_visibility": 1,
        "template_version": "0.0.0",
        "template_overrides": [{"input_index": 0, "override_required": True}],  # "all",
        "template_builder": base64.b64encode(
            txer.serialize(include_sender_sponsor=False)
        ).decode(),
    }
    _ = login_user(client, USER5_LOGIN_CREDS)
    response = client.post("/account/template", json=json.dumps(template_dict))
    _ = logoff_user(client)
    assert response.status_code == 201
    assert "error" not in response.json
    result = response.json
    assert "template_created" in result["result"]
    assert result["result"]["template_created"]["id"] == 1
    assert result["result"]["template_created"]["name"] == "Template 1"


def test_template_fetch_owned(client: FlaskClient):
    """Test retrieving a specific template."""
    _ = login_user(client, USER5_LOGIN_CREDS)
    response = client.get("/account/template/1", json=json.dumps({}))
    _ = logoff_user(client)
    assert response.status_code == 200
    assert "error" not in response.json
    result = response.json
    assert "template" in result["result"]
    assert result["result"]["template"]["id"] == 1
    assert result["result"]["template"]["template_name"] == "Template 1"


def test_templates_fetch(client: FlaskClient):
    """Test fetching all templates."""
    _ = login_user(client, USER5_LOGIN_CREDS)
    response = client.get("/account/templates", json=json.dumps({}))
    assert response.status_code == 200
    assert "error" not in response.json
    result = response.json
    _ = logoff_user(client)


def test_template_owned_missing_req(client: FlaskClient):
    """Fail template execution with missing required override."""
    _ = login_user(client, USER5_LOGIN_CREDS)
    response = client.post(
        "/account/template/execute", json=json.dumps({"tx_template_id": 1})
    )
    _ = logoff_user(client)
    check_error_expect(response, -1011)


def test_template_owned_invalid_override(client: FlaskClient):
    """Fail template execution with unknown override."""
    _ = login_user(client, USER5_LOGIN_CREDS)
    response = client.post(
        "/account/template/execute",
        json=json.dumps(
            {
                "tx_template_id": 1,
                "input_overrides": [
                    {"input_index": 0, "input_value": "foo"},
                    {"input_index": 7, "input_value": "bar"},
                ],
            }
        ),
    )
    _ = logoff_user(client)
    check_error_expect(response, -1010)


def test_template_owned_execute(client: FlaskClient, sui_client: SyncClient):
    """Pass template execution with valid pure required override."""
    _ = login_user(client, USER5_LOGIN_CREDS)
    response = client.post(
        "/account/template/execute",
        json=json.dumps(
            {
                "tx_template_id": 1,
                "input_overrides": [
                    {
                        "input_index": 0,
                        "input_value": PureInput.pure(SuiU64(2000000000)),
                    },
                ],
            }
        ),
    )
    _ = logoff_user(client)
    assert response.status_code == 201
    assert "error" not in response.json
    result = response.json
    assert len(result["result"]["accounts_posted"]) == 1
    _ = logoff_user(client)
    response = sign_request_for(client, sui_client, USER5_LOGIN_CREDS)


def test_template_shared(client: FlaskClient, sui_client: SyncClient):
    """Test creating a transaction Template."""
    txer = SyncTransaction(client=sui_client)
    primary_coin = gas_not_in(sui_client)
    to_address = sui_client.config.active_address
    scoin = txer.split_coin(coin=primary_coin, amounts=[1000000000])
    txer.transfer_objects(transfers=[scoin], recipient=to_address)
    # TODO: Add error check in backend for duplicate indexes
    template_dict = {
        "template_name": "Template 2",
        "template_visibility": 2,
        "template_version": "0.0.0",
        "template_overrides": [
            {"input_index": 0, "override_required": False},
            {"input_index": 1, "override_required": True},
            {"input_index": 2, "override_required": True},
        ],
        "template_builder": base64.b64encode(
            txer.serialize(include_sender_sponsor=False)
        ).decode(),
    }
    _ = login_user(client, USER5_LOGIN_CREDS)
    response = client.post("/account/template", json=json.dumps(template_dict))
    _ = logoff_user(client)
    assert response.status_code == 201
    assert "error" not in response.json
    result = response.json
    assert "template_created" in result["result"]
    assert result["result"]["template_created"]["id"] == 2
    assert result["result"]["template_created"]["name"] == "Template 2"


def test_template_shared_execute(
    client: FlaskClient, sui_client: SyncClient, accounts: dict
):
    """Pass template execution with valid pure required override."""
    _ = login_user(client, USER6_LOGIN_CREDS)
    # Get account address
    udata = _user_data_by_name("FrankC06", accounts["users"])
    addy6 = SuiAddress(udata["active_address"])
    result = sui_client.get_gas(addy6)
    assert result.is_ok()
    primary_coin = result.result_data.data[0]
    response = client.post(
        "/account/template/execute",
        json=json.dumps(
            {
                "tx_template_id": 2,
                "input_overrides": [
                    {
                        "input_index": 1,
                        "input_value": primary_coin.coin_object_id,
                    },
                    {
                        "input_index": 2,
                        "input_value": PureInput.pure(addy6),
                    },
                ],
            }
        ),
    )
    _ = logoff_user(client)
    assert response.status_code == 201
    assert "error" not in response.json
    result = response.json
    assert len(result["result"]["accounts_posted"]) == 1
    response = sign_request_for(client, sui_client, USER6_LOGIN_CREDS)


def test_pysui_tx_verification(client: FlaskClient, sui_client: SyncClient):
    """Test deserializing and inspecting a SuiTransaction."""
    txer = SyncTransaction(client=sui_client)
    scoin = txer.split_coin(coin=txer.gas, amounts=[1000000000])
    txer.transfer_objects(transfers=[scoin], recipient=sui_client.config.active_address)
    inspect_dict = {
        "tx_base64": base64.b64encode(
            txer.serialize(include_sender_sponsor=False)
        ).decode(),
        "perform": "verification",
    }
    _ = login_user(client, USER_LOGIN_CREDS)
    response = client.get(
        "/account/transaction/validate", json=json.dumps(inspect_dict)
    )
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
        "/account/signing-requests",
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
        "/account/transaction",
        json=json.dumps({}),
    )
    assert response.status_code == 200
    result = response.json
    assert not result["result"]["transactions"]
    _ = logoff_user(client)


def test_pysui_tx_execute(client: FlaskClient, sui_client: SyncClient):
    """Test deserializing and submitting a SuiTransaction."""
    txer = SyncTransaction(client=sui_client)
    scoin = txer.split_coin(coin=txer.gas, amounts=[1000000000])
    txer.transfer_objects(transfers=[scoin], recipient=sui_client.config.active_address)
    txin = TransactionIn(
        tx_builder=base64.b64encode(
            txer.serialize(include_sender_sponsor=False)
        ).decode()
    )
    _ = login_user(client, USER_LOGIN_CREDS)
    response = client.post("/account/transaction/execute", json=txin.to_json())
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
        "/account/transaction",
        json=json.dumps({}),
    )
    assert response.status_code == 200
    result = response.json
    assert result["result"]["transactions"]
    _ = logoff_user(client)


def test_pysui_tx_execute_deny_sig(client: FlaskClient, sui_client: SyncClient):
    """Test denying a signature request."""
    # Create the transaction
    txer = SyncTransaction(client=sui_client)
    scoin = txer.split_coin(coin=txer.gas, amounts=[1000000000])
    txer.transfer_objects(transfers=[scoin], recipient=sui_client.config.active_address)
    txin = TransactionIn(
        tx_builder=base64.b64encode(
            txer.serialize(include_sender_sponsor=False)
        ).decode()
    )
    # Post the transaction
    _ = login_user(client, USER_LOGIN_CREDS)
    response = client.post("/account/transaction/execute", json=txin.to_json())
    assert response.status_code == 201
    assert "error" not in response.json
    result = response.json
    assert len(result["result"]["accounts_posted"]) == 1
    # Get pending sig
    rfilt = SignRequestFilter(pending=True)
    response = client.get(
        "/account/signing-requests",
        json=rfilt.to_json(),
    )
    assert response.status_code == 200
    result = response.json
    assert len(result["result"]["signing_requests"]) == 1
    # Deny the signature
    sign_request = result["result"]["signing_requests"][0]
    kp = sui_client.config.keypair_for_address(sui_client.config.active_address)
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
        "/account/sign",
        json=payload.to_json(),
    )
    assert response.status_code == 201
    result = response.json
    assert result["result"]["signature_response"] == "denied"
    _ = logoff_user(client)


def _msig_data_by_name(name: str, block: list[dict]) -> dict:
    """Find msig account data block by name."""

    for msig in block:
        if msig["multisig_name"] == name:
            return msig
    return None


def _user_data_by_name(name: str, block: list[dict]) -> dict:
    """Find account data block by name."""

    for user in block:
        if user["user_name"] == name:
            return user
    return None


def _mmember_data_by_index(
    index: int, msig_block: dict, user_block: list[dict]
) -> dict:
    """Find account data block by name."""
    member = msig_block["multisig_members"][index]

    for user in user_block:
        if user["account_key"] == member["owner_id"]:
            return user

    return None


def test_pysui_tx_with_msig(
    client: FlaskClient, sui_client: SyncClient, accounts: dict
):
    """Test msig signing."""

    # Get Msig account_key
    msig_block = _msig_data_by_name("Msig01", accounts["multi_signatures"])
    msig_addy = SuiAddress(msig_block["active_address"])

    # Sync user
    _ = login_user(client, USER_LOGIN_CREDS)
    sender_account: PysuiAccount = account_data(client)
    sender_active_addy = SuiAddress(sender_account.active_address)
    # Create the transaction that puts gas in msig address
    txer = SyncTransaction(client=sui_client, initial_sender=sender_active_addy)
    scoin = txer.split_coin(coin=txer.gas, amounts=[10000000000])
    txer.transfer_objects(transfers=[scoin], recipient=msig_addy)
    txin = TransactionIn(
        tx_builder=base64.b64encode(
            txer.serialize(include_sender_sponsor=False)
        ).decode()
    )
    # Post the transaction
    response = client.post("/account/transaction/execute", json=txin.to_json())

    # Sign the transfer
    rfilt = SignRequestFilter(pending=True)
    response = client.get(
        "/account/signing-requests",
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
        "/account/sign",
        json=payload.to_json(),
    )
    assert response.status_code == 201
    result = response.json
    _ = logoff_user(client)

    # Get 2 of the sigs
    mmem1_account = _mmember_data_by_index(0, msig_block, accounts["users"])
    mmem2_account = _mmember_data_by_index(1, msig_block, accounts["users"])

    # Create the transaction that puts some msig gas back to orig
    txer = SyncTransaction(client=sui_client, initial_sender=msig_addy)
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
    response = client.post("/account/transaction/execute", json=txin.to_json())
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
        "/account/transaction",
        json=json.dumps({}),
    )
    assert response.status_code == 200
    result = response.json
    assert result["result"]["transactions"]
    _ = logoff_user(client)


def test_pysui_tx_sponsor(client: FlaskClient, sui_client: SyncClient, accounts: dict):
    """Test msig signing."""

    # Get Msig account_key
    msig_block = _msig_data_by_name("Msig01", accounts["multi_signatures"])
    msig_addy = SuiAddress(msig_block["active_address"])

    # Get 2 of the sigs
    mmem1_account = _mmember_data_by_index(0, msig_block, accounts["users"])
    mmem2_account = _mmember_data_by_index(1, msig_block, accounts["users"])

    # Sync user
    sender_active_addy = SuiAddress(mmem1_account["active_address"])
    # Create the transaction that puts gas in msig address
    txer = SyncTransaction(client=sui_client, initial_sender=sender_active_addy)
    scoin = txer.split_coin(coin=txer.gas, amounts=[10000000000])
    txer.transfer_objects(transfers=[scoin], recipient=msig_addy)
    txin = TransactionIn(
        tx_builder=base64.b64encode(
            txer.serialize(include_sender_sponsor=False)
        ).decode(),
        signers=Signers(
            sender=mmem1_account["active_address"],
            sponsor=mmem2_account["active_address"],
        ),
    )
    # Post the transaction
    _ = login_user(client, MSIG1_LOGIN_CREDS)
    response = client.post("/account/transaction/execute", json=txin.to_json())
    _ = logoff_user(client)
    response = sign_request_for(client, sui_client, MSIG1_LOGIN_CREDS)
    assert response.status_code == 201
    response = sign_request_for(client, sui_client, MSIG2_LOGIN_CREDS)
    assert response.status_code == 201
    result = response.json
    assert result["result"]["signature_response"] == "signed_and_executed"


def test_pysui_tx_msig_sponsor(
    client: FlaskClient, sui_client: SyncClient, accounts: dict
):
    """Test msig sponsoring."""

    # Get Msig account_key
    msig_block = _msig_data_by_name("Msig01", accounts["multi_signatures"])

    # Get 2 of the sigs
    mmem1_account = _mmember_data_by_index(0, msig_block, accounts["users"])
    mmem2_account = _mmember_data_by_index(1, msig_block, accounts["users"])

    # Get 2 other users
    mmem3_account = _user_data_by_name("FrankC03", accounts["users"])
    mmem4_account = _user_data_by_name("FrankC04", accounts["users"])

    # Sync user
    sender_active_addy = SuiAddress(mmem3_account["active_address"])
    recipient_active_addy = SuiAddress(mmem4_account["active_address"])
    # Create the transaction that puts gas in msig address
    txer = SyncTransaction(client=sui_client, initial_sender=sender_active_addy)
    scoin = txer.split_coin(coin=txer.gas, amounts=[10000000000])
    txer.transfer_objects(transfers=[scoin], recipient=recipient_active_addy)
    txin = TransactionIn(
        tx_builder=base64.b64encode(
            txer.serialize(include_sender_sponsor=False)
        ).decode(),
        signers=Signers(
            sender=mmem3_account["active_address"],
            sponsor=MultiSig(
                msig_account=msig_block["active_address"],
                msig_signers=[
                    mmem1_account["active_address"],
                    mmem2_account["active_address"],
                ],
            ),
        ),
    )
    # Post the transaction
    _ = login_user(client, USER3_LOGIN_CREDS)
    response = client.post("/account/transaction/execute", json=txin.to_json())
    _ = logoff_user(client)
    response = sign_request_for(client, sui_client, USER3_LOGIN_CREDS)
    assert response.status_code == 201
    response = sign_request_for(client, sui_client, MSIG1_LOGIN_CREDS)
    assert response.status_code == 201
    response = sign_request_for(client, sui_client, MSIG2_LOGIN_CREDS)
    assert response.status_code == 201
    result = response.json
    assert result["result"]["signature_response"] == "signed_and_executed"
