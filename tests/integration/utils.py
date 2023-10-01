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

import base64
import json
from dataclasses import dataclass
from typing import Any, Optional
from dataclasses_json import dataclass_json
from flask.testing import FlaskClient
from pysui import SyncClient, SuiAddress

from pysui_flask.api.xchange.payload import (
    SignRequestFilter,
    SigningApproved,
    SigningResponse,
)

ADMIN_LOGIN_CREDS: dict = {
    "username": "fastfrank",
    "password": "Oxnard Gimble",
}

USER_LOGIN_CREDS: dict = {"username": "FrankC015", "password": "Oxnard Gimble"}
MSIG_LOGIN_CREDS: dict = {"username": "Msig01", "password": "Oxnard Gimble"}

MSIG1_LOGIN_CREDS: dict = {"username": "FrankC01", "password": "Oxnard Gimble"}
MSIG2_LOGIN_CREDS: dict = {"username": "FrankC02", "password": "Oxnard Gimble"}


@dataclass_json
@dataclass
class PysuiAccount:
    """Account."""

    user_name: str
    account_key: str
    creation_date: str
    public_key: str
    active_address: str


def check_error_expect(response, ecode):
    """Assert on error results."""
    assert response.status_code == 200
    assert "error" in response.json
    assert response.json["error_code"] == ecode


def login_admin(
    client: FlaskClient, credentials: Optional[dict] = ADMIN_LOGIN_CREDS
) -> Any:
    """Login admin."""
    return client.get("/admin/login", json=json.dumps(credentials))


def logoff_admin(client: FlaskClient) -> Any:
    """Login any user."""
    return client.get("/admin/logoff", json=json.dumps({}))


def login_user(client: FlaskClient, credentials: dict) -> Any:
    """Login any user."""
    return client.get("/account/login", json=json.dumps(credentials))


def account_data(client: FlaskClient) -> PysuiAccount:
    """Get the account basics."""
    response = client.get("/account/", json=json.dumps({}))
    assert response.status_code == 200
    result = response.json
    return PysuiAccount.from_dict(result["result"]["account"])


def logoff_user(client: FlaskClient) -> Any:
    """Login any user."""
    return client.get("/account/logoff", json=json.dumps({}))


def sign_request_for(
    client: FlaskClient, sui_client: SyncClient, credentials: dict
) -> Any:
    """Encapsulate signing for transaction.

    :param client: Flask test client
    :type client: FlaskClient
    :param sui_client: pysui synchronous client
    :type sui_client: SyncClient
    :param credentials: sign on credentials
    :type credentials: dict
    :return: Flask response
    :rtype: _type_
    """
    _ = login_user(client, credentials)
    acc_data: PysuiAccount = account_data(client)
    rfilt = SignRequestFilter(pending=True)
    response = client.get(
        "/account/signing_requests",
        json=rfilt.to_json(),
    )
    assert response.status_code == 200
    result = response.json
    assert len(result["result"]["signing_requests"]) == 1
    sign_request = result["result"]["signing_requests"][0]
    kp = sui_client.config.keypair_for_address(
        SuiAddress(acc_data.active_address)
    )
    assert sign_request["status"] == 1
    assert (
        sign_request["signer_public_key"]
        == base64.b64encode(kp.public_key.scheme_and_key()).decode()
    )

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
    _ = logoff_user(client)
    return response
