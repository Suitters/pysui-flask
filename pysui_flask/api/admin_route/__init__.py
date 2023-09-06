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

"""Administrator route package."""

from flask import Blueprint, session
from pysui_flask.db_tables import User, UserRole, UserConfiguration
from pysui_flask.api_error import APIError, ErrorCodes


def admin_login_required():
    """Verify through session that admin is logged in."""
    if not session.get("admin_logged_in"):
        raise APIError("Admin must login first", ErrorCodes.LOGIN_REQUIRED)


admin_api = Blueprint("admin", __name__, url_prefix="/admin")

from . import admin
from . import ms_admin