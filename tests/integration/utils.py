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

"""Pytest common utilities."""
import json
from flask.testing import FlaskClient


def check_error_expect(response, ecode):
    """Assert on error results."""
    assert response.status_code == 200
    assert "error" in response.json
    assert response.json["error_code"] == ecode


def login_user(client: FlaskClient, credentials: dict):
    """Login any user."""
    return client.get("/account/login", json=json.dumps(credentials))


def logoff_user(client: FlaskClient):
    """Login any user."""
    return client.get("/account/logoff", json=json.dumps({}))
