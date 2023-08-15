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


def test_admin_pre_login_root(client: FlaskClient):
    """."""
    response = client.get("/")
    assert response.json["error"] == "Admin session not found"


def test_admin_login(client: FlaskClient):
    """."""
    creds = {
        "username": "fastfrank",
        "password": "AmTSExC46K9ZDms8GyQvIHYDb+X19Fpn6OxaRVigPBrz",
    }
    response = client.get("/login", json=json.dumps(creds))
    assert response.status_code == 200
    assert "session" in response.json


def test_admin_post_login_root(client: FlaskClient):
    """."""
    response = client.get("/")
    assert response.status_code == 200
    assert "session" in response.json


def test_admin_create_account(client: FlaskClient):
    """."""


def test_admin_accounts(client: FlaskClient):
    """."""
    response = client.get("/accounts")
    assert response.status_code == 200
    as_json = response.json
    print()
