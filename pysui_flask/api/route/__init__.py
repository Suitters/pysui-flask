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

import hashlib
from typing import Union
from pysui_flask.db_tables import User, UserRole, UserConfiguration, ConfigKeys
from pysui_flask.api_error import CredentialError


def verify_credentials(
    *, user_name: str, user_password: str, expected_role: UserRole
) -> Union[User, CredentialError]:
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
    # TODO: Generalize constraint length vs hardcoded
    if (not (7 < len(user_name) < 255)) or (not (7 < len(user_password) < 15)):
        raise CredentialError("Credential length error")

    result: User = User.query.filter_by(user_name_or_email=user_name).first()
    # Verify credentials
    if result:
        if result.user_role == expected_role:
            encoded_pwd = str.encode(user_password)
            pwd_hashed = hashlib.blake2b(
                encoded_pwd, digest_size=32
            ).hexdigest()
            if pwd_hashed == result.password:
                return result
    raise CredentialError(f"Unable to verify credentials for {user_name}")
