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
import json

from flask.testing import FlaskClient

from tests.unit.utils import check_error_expect

ADMIN_LOGIN_CREDS: dict = {
    "username": "fastfrank",
    "password": "Oxnard Gimble",
}

# Negative testing before session


def test_admin_pre_login_root(client: FlaskClient):
    """Validate error on non-JSON and empty request."""
    response = client.get("/admin/")
    check_error_expect(response, -5)


def test_no_login(client: FlaskClient):
    """Validate error on non-JSON and empty request."""
    response = client.post("/admin/user_account")
    check_error_expect(response, -5)


def test_bad_content(client: FlaskClient):
    """Validate error on bad login credentials."""
    creds = {
        "username": "fastfrank",
        "password": "Slippery Slope",
    }
    response = client.get("/admin/login", data=json.dumps(creds))
    check_error_expect(response, -5)


def test_bad_admin_login(client: FlaskClient):
    """Validate error on bad login credentials."""
    creds = {
        "username": "fastfrank",
        "password": "Slippery Slope",
    }
    response = client.get("/admin/login", json=json.dumps(creds))
    check_error_expect(response, -10)


def test_bad_credential_length(client: FlaskClient):
    """Validate error on bad login credentials."""
    creds = {
        "username": "fastfra",
        "password": "Slippery Slope",
    }
    response = client.get("/admin/login", json=json.dumps(creds))
    check_error_expect(response, -10)


# Valid login
def test_admin_login(client: FlaskClient):
    """Validate good login credentials."""
    response = client.get("/admin/login", json=json.dumps(ADMIN_LOGIN_CREDS))
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
        response = client.post(
            "/admin/user_account", json=json.dumps(bad_content)
        )
        check_error_expect(response, -20)


def test_admin_account_not_found(client: FlaskClient):
    """Validate no account found."""
    response = client.get(
        "/admin/user_account/key",
        json=json.dumps(
            {"account_key": "AKkeo/3DD7dra88PdTPhBngdbdTOBHJq8GrnWIfbKsb7"}
        ),
    )
    check_error_expect(response, -40)


def _do_good(name_tag: int) -> dict:
    """Utility to generate a valid user confighuration."""
    good_content = {
        "user": {"username": "FrankC0", "password": "Oxnard Gimble"},
        "config": {
            # "private_key": "AIUPxQveY18QxhDDdTO0D0OD6PNV+et50068d1g/rIyl",
            "public_key": {
                "key_scheme": "ED25519",
                "wallet_key": "qo8AGl3wC0uqhRRAn+L2B+BhGpRMp1UByBi8LtZxG+U=",
            },
            # "environment": "devnet",
            "urls": {
                "rpc_url": "https://fullnode.devnet.sui.io:443",
                "ws_url": "https://fullnode.devnet.sui.io:443",
            },
        },
    }
    if name_tag:
        good_content["user"]["username"] = good_content["user"][
            "username"
        ] + str(name_tag)
    return good_content


def test_admin_create_account_no_errors(client: FlaskClient):
    """Validate single and bulk user account creations."""
    # Good data
    good_content = _do_good(1)

    response = client.post(
        "/admin/user_account", json=json.dumps(good_content)
    )
    assert response.status_code == 201
    result = response.json
    assert "result" in result and "created" in result["result"]
    account_key = result["result"]["created"]["account_key"]
    response = client.get(
        "/admin/user_account/key",
        json=json.dumps({"account_key": account_key}),
    )
    assert response.status_code == 200
    result = response.json
    assert result["result"]["account"]["user_name"] == "FrankC01"
    assert result["result"]["account"]["user_role"] == 2

    # This creates users 2 - 9 (seven more)
    bulk: list[dict] = [_do_good(x) for x in range(2, 10)]
    # Make the last one no public key
    bulk[7]["config"]["public_key"] = None

    response = client.post("/admin/user_accounts", json=json.dumps(bulk))
    assert response.status_code == 201
    result = response.json
    assert result["result"]["created"]
    assert len(result["result"]["created"]) == len(bulk)


def test_admin_all_accounts(client: FlaskClient):
    """Validate getting all accounts."""
    # response = client.get("/user_accounts", json=json.dumps({"limit": 50}))
    # assert response.status_code == 200
    response = client.get(
        "/admin/user_accounts", json=json.dumps({"count": 2})
    )
    assert response.status_code == 200
    result = response.json["result"]
    while result["cursor"]["has_remaining_data"]:
        response = client.get(
            "/admin/user_accounts/" + str(result["cursor"]["next_page"]),
            json=json.dumps({"count": 4}),
        )
        assert response.status_code == 200
        result = response.json["result"]
    print(result)