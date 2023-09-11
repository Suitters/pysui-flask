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

"""Execution module."""

from typing import Any
from pysui_flask.db_tables import (
    db,
    User,
    UserRole,
    SigningAs,
    SignerStatus,
    SignatureStatus,
    SignatureRequest,
    SignatureTrack,
)
from pysui_flask.api.xchange.payload import SigningResponse


def _update_tracker(*, session_key: str, sig_req: SignatureRequest) -> Any:
    """."""
    track: SignatureTrack = SignatureTrack.query.filter(
        SignatureTrack.id == sig_req.tracking
    ).one()
    return None


def _update_signatures(
    *, session_key: str, sig_req: SignatureRequest, sig_resp: SigningResponse
) -> Any:
    """Handles state change on signature.

    Walks up to tracker and sets status accordingly

    :param session_key: The account key of user session
    :type session_key: str
    :param siq_req: The signing request row
    :type siq_req: SignatureRequest
    :return: Some result
    :rtype: Any
    """
    # Set the request state and commit
    sstatus = SignerStatus.signed if sig_resp.approved else SignerStatus.denied

    sig_req.status = sstatus
    if sstatus == SignerStatus.signed:
        sig_req.signature = sig_resp.outcome.signature
    db.session.commit()
    _update_tracker(session_key=session_key, sig_req=sig_req)
    return "Signed"


def signature_update(*, session_key: str, sig_resp: SigningResponse) -> Any:
    """."""
    sign_request: SignatureRequest = SignatureRequest.query.filter(
        SignatureRequest.id == sig_resp.request_id
    ).one()
    # Confirm that the user session aligns with signing response
    if sign_request.signer_account_key == session_key:
        # user: User = User.query.filter(
        #     User.account_key == session["user_key"]
        # ).first()
        result = _update_signatures(
            session_key=session_key,
            sig_req=sign_request,
            sig_resp=sig_resp,
        )
    return result
