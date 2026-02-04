"""Shared test helpers."""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch
import custom_components.db_infoscreen as db_mod


@contextmanager
def patch_session(mock_data=None, side_effect=None):
    """Patch the async_get_clientsession to return a mock session with data."""

    # 1. Create the base response mock
    def create_mock_response(data):
        resp = MagicMock()
        resp.status = 200

        async def json_func():
            return data

        resp.json = MagicMock(side_effect=json_func)

        resp.raise_for_status = MagicMock()

        async def enter_func():
            return resp

        async def exit_func(exc_type, exc, tb):
            return None

        resp.__aenter__ = MagicMock(side_effect=enter_func)
        resp.__aexit__ = MagicMock(side_effect=exit_func)
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
