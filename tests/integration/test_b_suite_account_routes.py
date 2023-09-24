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

from flask.testing import FlaskClient

from tests.integration.utils import (
    check_error_expect,
    login_user,
    logoff_user,
    USER_LOGIN_CREDS,
    MSIG_LOGIN_CREDS,
)


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
