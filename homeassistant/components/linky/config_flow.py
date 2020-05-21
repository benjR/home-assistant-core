"""Config flow to configure the Linky integration."""
import logging

from pylinky import AbstractAuth, LinkyAPI
from pylinky.exceptions import (
    PyLinkyAccessException,
    PyLinkyEnedisException,
    PyLinkyException,
    PyLinkyWrongLoginException,
)
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.helpers.network import get_url

from .const import DOMAIN  # pylint: disable=unused-import

_LOGGER = logging.getLogger(__name__)


class LinkyFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def _show_setup_form(self, user_input=None, errors=None):
        """Show the setup form to the user."""

        if user_input is None:
            user_input = {}

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CLIENT_ID, default=user_input.get(CONF_CLIENT_ID, "")
                    ): str,
                    vol.Required(
                        CONF_CLIENT_SECRET,
                        default=user_input.get(CONF_CLIENT_SECRET, ""),
                    ): str,
                }
            ),
            errors=errors or {},
        )

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        errors = {}

        if user_input is None:
            return self._show_setup_form(user_input, None)

        client_id = user_input[CONF_CLIENT_ID]
        client_secret = user_input[CONF_CLIENT_SECRET]

        # Check if already configured
        if self.unique_id is None:
            await self.async_set_unique_id(user_input.get("usage_point_id"))
            self._abort_if_unique_id_configured()

        auth = AbstractAuth(client_id, client_secret, get_url(self.hass))
        api = LinkyAPI(auth)
        try:
            await self.hass.async_add_executor_job(api.get_authorisation_url)
            await self.hass.async_add_executor_job(api.get_usage_point_ids)
        except PyLinkyAccessException as exp:
            _LOGGER.error(exp)
            errors["base"] = "access"
            return self._show_setup_form(user_input, errors)
        except PyLinkyEnedisException as exp:
            _LOGGER.error(exp)
            errors["base"] = "enedis"
            return self._show_setup_form(user_input, errors)
        except PyLinkyWrongLoginException as exp:
            _LOGGER.error(exp)
            errors["base"] = "wrong_login"
            return self._show_setup_form(user_input, errors)
        except PyLinkyException as exp:
            _LOGGER.error(exp)
            errors["base"] = "unknown"
            return self._show_setup_form(user_input, errors)
        finally:
            api.close_session()

        return self.async_create_entry(
            title="usage_point",
            data={
                CONF_CLIENT_ID: client_id,
                CONF_CLIENT_SECRET: client_secret,
                "usage_point_id": user_input.get("usage_point_id"),
            },
        )

    async def async_step_import(self, user_input=None):
        """Import a config entry."""
        return await self.async_step_user(user_input)
