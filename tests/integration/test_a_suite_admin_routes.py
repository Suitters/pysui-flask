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

"""Pytest admin routes."""

import base64
import json

from flask.testing import FlaskClient

from tests.integration.utils import (
    ADMIN_LOGIN_CREDS,
    check_error_expect,
    clean_url_base64,
    login_admin,
    logoff_admin,
)

from pysui import SyncClient
from pysui.abstracts.client_keypair import SignatureScheme
from pysui.sui.sui_crypto import SuiKeyPair, SuiPublicKey


# Negative testing before session


def test_admin_pre_login_root(client: FlaskClient):
    """Validate error on non-JSON and empty request."""
    response = client.get("/admin/")
    check_error_expect(response, -5)


def test_no_login(client: FlaskClient):
    """Validate error on non-JSON and empty request."""
    response = client.post("/admin/user_account")
    check_error_expect(response, -5)


def test_bad_admin_login(client: FlaskClient):
    """Validate error on bad login credentials."""
    creds = {
        "username": "fastfrank",
        "password": "Slippery Slope",
    }
    response = login_admin(client, creds)
    # response = client.get("/admin/login", json=json.dumps(creds))
    check_error_expect(response, -10)


def test_bad_credential_length(client: FlaskClient):
    """Validate error on bad login credentials."""
    creds = {
        "username": "fastfra",
        "password": "Slippery Slope",
    }
    response = login_admin(client, creds)
    # response = client.get("/admin/login", json=json.dumps(creds))
    check_error_expect(response, -10)


# Valid login


def test_admin_login(client: FlaskClient):
    """Validate good login credentials."""
    response = login_admin(client)
    # response = client.get("/admin/login", json=json.dumps(ADMIN_LOGIN_CREDS))
    assert response.status_code == 200
    result = response.json
    assert "result" in result and "session" in result["result"]


def test_admin_post_login_root(client: FlaskClient):
    """Validate logged in already."""
    response = client.get("/admin/", json={})
    assert response.status_code == 200
    result = response.json
    assert "result" in result and "session" in result["result"]


_BAD_CONTENT: list[dict] = [
    {"foo": "bar"},
    {"user": "bar", "foo": "bar"},
    {"config": "bar", "foo": "bar"},
    {"user": {}, "config": {}},
]


def test_admin_create_account_data_errors(client: FlaskClient):
    """Validate various bad user account configurations."""
    # Ensure login
    response = client.get("/admin/login", json=json.dumps(ADMIN_LOGIN_CREDS))
    assert response.status_code == 200
    result = response.json
    assert "result" in result and "session" in result["result"]

    for bad_content in _BAD_CONTENT:
        response = client.post("/admin/account", json=json.dumps(bad_content))
        check_error_expect(response, -20)


def test_admin_account_not_found(client: FlaskClient):
    """Validate no account found."""
    acc_key = clean_url_base64("AKkeo53DD/dra88PdTPhBngdbdTOBHJq8GrnWIfbKsb7")
    response = client.get(f"/admin/account/{acc_key}", json=json.dumps({}))
    check_error_expect(response, -40)


def test_admin_create_accounts(client: FlaskClient, sui_client: SyncClient):
    """Create accounts from Sui localnode addresses."""
    rpc_url = sui_client.config.rpc_url
    ws_url = ""
    addys: dict[str, SuiKeyPair] = sui_client.config.addresses_and_keys
    goodies: list[dict] = []
    account_index = 1
    for kp in addys.values():
        pub_key = kp.public_key
        goodies.append(
            {
                "user": {
                    "username": "FrankC0" + str(account_index),
                    "password": "Oxnard Gimble",
                    "public_key": {
                        "key_scheme": pub_key.scheme.sig_scheme,
                        "wallet_key": pub_key.pub_key,
                    },
                },
            }
        )
        account_index += 1
    response = client.post("/admin/accounts", json=json.dumps(goodies))
    assert response.status_code == 201
    result = response.json
    assert result["result"]["created"]
    assert len(result["result"]["created"]) == len(goodies)
    print(goodies)


def test_admin_all_accounts(client: FlaskClient):
    """Validate getting all accounts."""
    # response = client.get("/user_accounts", json=json.dumps({"limit": 50}))
    # assert response.status_code == 200
    response = client.get("/admin/accounts", json=json.dumps({"count": 2}))
    assert response.status_code == 200
    result = response.json["result"]
    while result["cursor"]["has_remaining_data"]:
        response = client.get(
            "/admin/accounts/" + str(result["cursor"]["next_page"]),
            json=json.dumps({"count": 4}),
        )
        assert response.status_code == 200
        result = response.json["result"]
    print(result)


def test_admin_create_msig(client: FlaskClient, sui_client: SyncClient):
    """Create accounts from Sui localnode addresses."""
    # Get first 3 accounts
    response = client.get("/admin/accounts", json=json.dumps({"count": 3}))
    assert response.status_code == 200
    result = response.json["result"]["accounts"]
    # Build members
    base_weight = 3
    members = []
    for acc in result:
        members.append({"account_key": acc["account_key"], "weight": base_weight})
        base_weight += 3
    threshold = 9

    rpc_url = sui_client.config.rpc_url
    # # Get 3 members
    # msig_members = list(sui_client.config.addresses_and_keys.items())[0:3]

    msig_payload = {
        "members": members,
        "threshold": threshold,
        "name": "Msig01",
        "requires_attestation": False,
    }

    response = client.post("/admin/multi_sig_account", json=json.dumps(msig_payload))
    print(msig_payload)


def test_account_lock_unlock(client: FlaskClient, accounts: dict):
    """."""
    account = clean_url_base64(accounts["users"][5]["account_key"])
    response = client.post(f"/admin/account/{account}/lock", json=json.dumps({}))
    assert response.status_code == 201
    response = client.post(f"/admin/account/{account}/unlock", json=json.dumps({}))
    assert response.status_code == 201
