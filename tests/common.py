"""Shared test helpers."""

from contextlib import contextmanager
from unittest.mock import MagicMock, AsyncMock, patch
import custom_components.db_infoscreen as db_mod


@contextmanager
def patch_session(mock_data=None, side_effect=None):
    """Patch the async_get_clientsession to return a mock session with data."""

    # 1. Create the base response mock
    def create_mock_response(data):
        resp = MagicMock()
        resp.status = 200
        resp.json = AsyncMock(return_value=data)
        resp.raise_for_status = MagicMock()
        resp.__aenter__ = AsyncMock(return_value=resp)
        resp.__aexit__ = AsyncMock(return_value=None)
        return resp

    # 2. Setup the session mock
    mock_session = MagicMock()

    default_response = create_mock_response(mock_data if mock_data is not None else {})

    def get_side_effect(url, **kwargs):
        if side_effect:
            res = side_effect(url, **kwargs)
            if isinstance(res, (dict, list)):
                return create_mock_response(res)
            return res
        return default_response

    mock_session.get = MagicMock(side_effect=get_side_effect)

    # Patch in both the component and the HA source
    with patch.object(db_mod, "async_get_clientsession") as p1, patch(
        "homeassistant.helpers.aiohttp_client.async_get_clientsession"
    ) as p2:

        p1.return_value = mock_session
        p2.return_value = mock_session

        yield mock_session
