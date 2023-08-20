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

"""Route package init."""

import base64
import hashlib
from typing import Union
from pysui_flask.db_tables import User, UserRole
from pysui_flask.api_error import APIError, ErrorCodes


def str_to_hash_hex(indata: str) -> str:
    """."""
    encoded_pwd = str.encode(indata)
    return hashlib.blake2b(encoded_pwd, digest_size=32).hexdigest()


def verify_credentials(
    *,
    username: str,
    user_password: str,
    expected_role: UserRole = UserRole.user,
) -> Union[User, APIError]:
    """_summary_ Verifies credentials match database for user.

    :param user_name: Submitted name
    :type user_name: str
    :param user_password: Submitted password
    :type user_password: str
    :param expected_role: The expected role set by route
    :type expected_role: UserRole
    :raises CredentialError: If username or password lengths are invalid
    :raises CredentialError: If failure to resolve user based on passed in credentials
    :return: The User row from DB
    :rtype: User
    """
    # Find user
    result: User = User.query.filter_by(user_name_or_email=username).first()
    # Verify credentials
    if result:
        if result.user_role == expected_role:
            pwd_hashed = str_to_hash_hex(user_password)
            if pwd_hashed == result.password:
                return result
    raise APIError(
        f"Unable to verify credentials for {username}",
        ErrorCodes.CREDENTIAL_ERROR,
    )
