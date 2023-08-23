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


def test_account_post_login_root(client: FlaskClient):
    """Validate error on non-JSON and empty request."""
    response = client.get("/account/", json=json.dumps({}))
    assert response.status_code == 200
    result = response.json
    assert result["result"]["account"]["user_name"] == "FrankC01"
    assert result["result"]["account"]["user_role"] == 2


def test_account_get_gas(client: FlaskClient):
    """Should be empty."""


def test_account_get_objects(client: FlaskClient):
    """Should be empty."""
