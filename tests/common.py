"""Shared test helpers."""

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch


@contextmanager
def patch_session(mock_data=None, side_effect=None):
    """Patch the async_get_clientsession to return a mock session with data."""
    with patch(
        "custom_components.db_infoscreen.async_get_clientsession"
    ) as mock_get_session:
        # Mock Response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=mock_data)

        # Async context manager protocol
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        # Mock Session
        mock_session = MagicMock()

        # session.get needs to return a context manager directly
        def mock_get(*args, **kwargs):
            if side_effect:
                res = side_effect(*args, **kwargs)
                # If side_effect returns raw data, wrap it in an ACM shim
                if isinstance(res, (dict, list)):
                    shim = MagicMock()
                    shim.status = 200
                    shim.raise_for_status = MagicMock()
                    shim.json = AsyncMock(return_value=res)
                    shim.__aenter__ = AsyncMock(return_value=shim)
                    shim.__aexit__ = AsyncMock(return_value=None)
                    return shim
                return res
            return mock_response

        mock_session.get = MagicMock(side_effect=mock_get)

        mock_get_session.return_value = mock_session
        yield mock_session
