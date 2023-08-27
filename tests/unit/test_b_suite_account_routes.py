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

from pysui import SyncClient, SuiConfig
from pysui.sui.sui_txn import SyncTransaction

from tests.unit.utils import check_error_expect

USER_LOGIN_CREDS: dict = {"username": "FrankC01", "password": "Oxnard Gimble"}


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
    response = client.get("/account/login", json=json.dumps(creds))
    check_error_expect(response, -10)


def test_good_login_content(client: FlaskClient):
    """Validate good account login credentials."""
    response = client.get("/account/login", json=json.dumps(USER_LOGIN_CREDS))
    assert response.status_code == 200
    result = response.json
    assert "result" in result and "session" in result["result"]


# 0x94a1d8d13ad80563f307362f730e84691fa1cde7b83932abae0af2620c3e0855
def test_account_post_login_root(client: FlaskClient):
    """Validate error on non-JSON and empty request."""
    response = client.get("/account/", json=json.dumps({}))
    assert response.status_code == 200
    result = response.json
    assert result["result"]["account"]["user_name"] == "FrankC01"
    assert result["result"]["account"]["user_role"] == 2


# Sui Calls


def test_get_gas(client: FlaskClient):
    """Should have some gas."""
    response = client.get("/account/gas", json=json.dumps({"all": False}))
    assert response.status_code == 200
    result = response.json
    assert result["result"]["data"][0]


def test_get_objects(client: FlaskClient):
    """Should have some objects."""
    response = client.get("/account/objects", json=json.dumps({"all": False}))
    assert response.status_code == 200
    result = response.json
    assert result["result"]["data"]


def test_get_object(client: FlaskClient):
    """Should not be empty."""
    response = client.get(
        "/account/object/0x5464b56a2ab51547cd7da5fe0e31278b833bf54d87df2be93c85b738f83cfb05",
        json=json.dumps({}),
    )
    assert response.status_code == 200
    result = response.json


def test_pysui_tx_inspect(client: FlaskClient):
    """Test deserializing and inspecting a SuiTransaction."""
    sclient = SyncClient(
        SuiConfig.user_config(
            rpc_url="https://fullnode.devnet.sui.io:443",
            prv_keys=["AIUPxQveY18QxhDDdTO0D0OD6PNV+et50068d1g/rIyl"],
        )
    )
    txer = SyncTransaction(sclient)
    scoin = txer.split_coin(coin=txer.gas, amounts=[1000000000])
    txer.transfer_objects(
        transfers=[scoin], recipient=sclient.config.active_address
    )
    inspect_dict = {"tx_base64": base64.b64encode(txer.serialize()).decode()}
    response = client.get("/account/pysui_txn", json=json.dumps(inspect_dict))
    assert response.status_code == 200
    assert "error" not in response.json
    result = response.json


def test_pysui_tx_verification(client: FlaskClient):
    """Test deserializing and inspecting a SuiTransaction."""
    sclient = SyncClient(
        SuiConfig.user_config(
            rpc_url="https://fullnode.devnet.sui.io:443",
            prv_keys=["AIUPxQveY18QxhDDdTO0D0OD6PNV+et50068d1g/rIyl"],
        )
    )
    txer = SyncTransaction(sclient)
    scoin = txer.split_coin(coin=txer.gas, amounts=[1000000000])
    txer.transfer_objects(
        transfers=[scoin], recipient=sclient.config.active_address
    )
    inspect_dict = {
        "tx_base64": base64.b64encode(txer.serialize()).decode(),
        "perform": "verification",
    }
    response = client.get("/account/pysui_txn", json=json.dumps(inspect_dict))
    assert response.status_code == 200
    assert "error" not in response.json
    result = response.json
    assert isinstance(result["result"]["verification"], str)
    assert result["result"]["verification"] == "success"


# def test_pysui_tx_execute(client: FlaskClient):
#     """Test deserializing and inspecting a SuiTransaction."""
#     sclient = SyncClient(
#         SuiConfig.user_config(
#             rpc_url="https://fullnode.devnet.sui.io:443",
#             prv_keys=["AIUPxQveY18QxhDDdTO0D0OD6PNV+et50068d1g/rIyl"],
#         )
#     )
#     txer = SyncTransaction(sclient)
#     scoin = txer.split_coin(coin=txer.gas, amounts=[1000000000])
#     txer.transfer_objects(
#         transfers=[scoin], recipient=sclient.config.active_address
#     )
#     inspect_dict = {"tx_base64": base64.b64encode(txer.serialize()).decode()}
#     response = client.post("/account/pysui_txn", json=json.dumps(inspect_dict))
#     assert response.status_code == 200
#     assert "error" not in response.json
#     result = response.json


def test_add_multisig(client: FlaskClient):
    """Should be empty."""
