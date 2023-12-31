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
from pysui_flask.api.xchange.payload import PwdChange

from tests.integration.utils import (
    check_error_expect,
    login_user,
    logoff_user,
    USER_LOGIN_CREDS,
)


BAD_OPS_USER_LOGIN_CREDS: dict = {
    "username": "FrankC016",
    "password": "Oxnard Gimble",
}

PWD_OPS_USER_LOGIN_CREDS: dict = {
    "username": "FrankC013",
    "password": "Oxnard Gimble",
}

PWD_OPS_USER_NEW_CREDS: dict = {
    "username": "FrankC013",
    "password": "Jinxy Cat",
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
    # response = client.get("/account/gas", json=json.dumps({"all": False}))
    # check_error_expect(response, -1)
    response = logoff_user(client)
    assert response.status_code == 200


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
    _ = logoff_user(client)

def test_change_pwd(client: FlaskClient):
    """Validate good password change."""
    response = login_user(client, PWD_OPS_USER_LOGIN_CREDS)
    assert response.status_code == 200
    result = response.json
    assert "result" in result and "session" in result["result"]
    payload = PwdChange(current_pwd=PWD_OPS_USER_LOGIN_CREDS["password"],new_pwd=PWD_OPS_USER_NEW_CREDS["password"])
    response = client.post("/account/password", json=payload.to_json())
    assert response.status_code == 201
    _ = logoff_user(client)
    response = login_user(client, PWD_OPS_USER_NEW_CREDS)
    assert response.status_code == 200
    _ = logoff_user(client)
    result = response.json
    assert "result" in result and "session" in result["result"]

def test_change_bad_pwd(client: FlaskClient):
    """Validate password change errors and lock."""
    response = login_user(client, PWD_OPS_USER_NEW_CREDS)
    assert response.status_code == 200
    # TODO: Make this iterations over configuration variable
    # Attempt 1
    payload = PwdChange(current_pwd=PWD_OPS_USER_LOGIN_CREDS["password"],new_pwd=PWD_OPS_USER_NEW_CREDS["password"])
    response = client.post("/account/password", json=payload.to_json())
    check_error_expect(response, -11)
    # Attempt 2
    payload = PwdChange(current_pwd=PWD_OPS_USER_LOGIN_CREDS["password"],new_pwd=PWD_OPS_USER_NEW_CREDS["password"])
    response = client.post("/account/password", json=payload.to_json())
    check_error_expect(response, -11)
    # Attempt 3
    payload = PwdChange(current_pwd=PWD_OPS_USER_LOGIN_CREDS["password"],new_pwd=PWD_OPS_USER_NEW_CREDS["password"])
    response = client.post("/account/password", json=payload.to_json())
    check_error_expect(response, -11)
    # Attempt 4
    payload = PwdChange(current_pwd=PWD_OPS_USER_LOGIN_CREDS["password"],new_pwd=PWD_OPS_USER_NEW_CREDS["password"])
    response = client.post("/account/password", json=payload.to_json())
    assert response.status_code == 200
    result = response.json
    assert result["result"]["changed"] == False
    _ = logoff_user(client)
    response = login_user(client, PWD_OPS_USER_NEW_CREDS)
    check_error_expect(response, -13)
