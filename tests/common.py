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

        async def __mock_aenter__(*args, **kwargs):
            return mock_response
        async def __mock_aexit__(*args, **kwargs):
            return None

        mock_response.__aenter__ = __mock_aenter__
        mock_response.__aexit__ = __mock_aexit__

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

                    async def __shim_aenter__(*args, **kwargs):
                        return shim
                    async def __shim_aexit__(*args, **kwargs):
                        return None

                    shim.__aenter__ = __shim_aenter__
                    shim.__aexit__ = __shim_aexit__
                    return shim
                return res
            return mock_response

        mock_session.get = MagicMock(side_effect=mock_get)

        mock_get_session.return_value = mock_session
        yield mock_session
