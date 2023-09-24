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


"""Base Exception."""

from enum import IntEnum
from typing import Optional


# Error codes
class ErrorCodes(IntEnum):
    """Api Error Codes."""

    UNKNOWN_ERROR: int = 0
    LOGIN_REQUIRED: int = -1
    CONTENT_TYPE_ERROR: int = -5
    CREDENTIAL_ERROR: int = -10
    REQUEST_CONTENT_ERROR: int = -20
    USER_ALREADY_EXISTS: int = -30
    ACCOUNT_NOT_FOUND: int = -40
    INVALID_ACCOUNT_ROLE: int = -50
    PAYLOAD_ERROR: int = -60
    # pysui base error from which all pysui exceptions derive
    PYSUI_ERROR_BASE: int = -1000
    # Occurs when sender sponsor does not have public key
    PYSUI_MISSING_PUBLIC_KEY: int = -1001
    PYSUI_INVALID_MS_MEMBER_KEY: int = -1002
    PYSUI_MS_MEMBER_WEIGHT_BELOW_THRESHOLD: int = -1003
    PYSUI_MS_MEMBER_NO_ACCOUNT: int = -1004
    PUBLICKEY_MULTISIG_MEMBER: int = -1005
    PUBLICKEY_SIGNATURES_EXIST: int = -1006
    # Occurs when object in transaction does belong to sender or sponsor
    PYSUI_INVALID_OBJECT_OWNERSHIP: int = -1020
    # sui errors
    SUI_ERROR_BASE: int = -2000


class APIError(Exception):
    """Base API Error."""

    _status_code = 200

    def __init__(
        self,
        message: str,
        error_code: Optional[ErrorCodes] = None,
        payload: Optional[dict] = None,
    ):
        """Create the exception."""
        super().__init__()
        self.message = message
        self.error_code = error_code or ErrorCodes.UNKNOWN_ERROR
        self.status_code = self._status_code
        self.payload = payload

    def to_dict(self):
        """Coerce to dict."""
        rv = dict(self.payload or ())
        rv["error"] = self.message
        rv["error_code"] = self.error_code.value
        return rv
