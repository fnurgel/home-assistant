"""Test Hue setup process."""
from unittest.mock import Mock

import pytest

from homeassistant import config_entries
from homeassistant.components import hue
from homeassistant.setup import async_setup_component

from tests.async_mock import AsyncMock, patch
from tests.common import MockConfigEntry


@pytest.fixture
def mock_bridge_setup():
    """Mock bridge setup."""
    with patch.object(hue, "HueBridge") as mock_bridge:
        mock_bridge.return_value.async_setup = AsyncMock(return_value=True)
        mock_bridge.return_value.api.config = Mock(bridgeid="mock-id")
        yield mock_bridge.return_value


async def test_setup_with_no_config(hass):
    """Test that we do not discover anything or try to set up a bridge."""
    assert await async_setup_component(hass, hue.DOMAIN, {}) is True

    # No flows started
    assert len(hass.config_entries.flow.async_progress()) == 0

    # No configs stored
    assert hass.data[hue.DOMAIN] == {}


async def test_setup_defined_hosts_known_auth(hass):
    """Test we don't initiate a config entry if config bridge is known."""
    MockConfigEntry(domain="hue", data={"host": "0.0.0.0"}).add_to_hass(hass)

    with patch.object(hue, "async_setup_entry", return_value=True):
        assert (
            await async_setup_component(
                hass,
                hue.DOMAIN,
                {
                    hue.DOMAIN: {
                        hue.CONF_BRIDGES: [
                            {
                                hue.CONF_HOST: "0.0.0.0",
                                hue.CONF_ALLOW_HUE_GROUPS: False,
                                hue.CONF_ALLOW_UNREACHABLE: True,
                            },
                            {hue.CONF_HOST: "1.1.1.1"},
                        ]
                    }
                },
            )
            is True
        )

    # Flow started for discovered bridge
    assert len(hass.config_entries.flow.async_progress()) == 1

    assert len(hass.services.async_services()) == 1

    # Config stored for domain.
    assert hass.data[hue.DATA_CONFIGS] == {
        "0.0.0.0": {
            hue.CONF_HOST: "0.0.0.0",
            hue.CONF_ALLOW_HUE_GROUPS: False,
            hue.CONF_ALLOW_UNREACHABLE: True,
        },
        "1.1.1.1": {hue.CONF_HOST: "1.1.1.1"},
    }


GROUP_RESPONSE = {
    "1": {
        "name": "Group 1",
        "lights": ["1", "2"],
        "type": "LightGroup",
        "action": {
            "on": True,
            "bri": 254,
            "hue": 10000,
            "sat": 254,
            "effect": "none",
            "xy": [0.5, 0.5],
            "ct": 250,
            "alert": "select",
            "colormode": "ct",
        },
        "state": {"any_on": True, "all_on": False},
    },
    "2": {
        "name": "Group 2",
        "lights": ["3", "4", "5"],
        "type": "LightGroup",
        "action": {
            "on": True,
            "bri": 153,
            "hue": 4345,
            "sat": 254,
            "effect": "none",
            "xy": [0.5, 0.5],
            "ct": 250,
            "alert": "select",
            "colormode": "ct",
        },
        "state": {"any_on": True, "all_on": False},
    },
}


async def test_setup_multiple(hass, mock_bridge):
    """Test we don't initiate a config entry if config bridge is known."""
    MockConfigEntry(domain="hue", data={"host": "0.0.0.0"}).add_to_hass(hass)

    with patch.object(hue, "async_setup_entry", return_value=True):
        assert (
            await async_setup_component(
                hass,
                hue.DOMAIN,
                {
                    hue.DOMAIN: {
                        hue.CONF_BRIDGES: [
                            {
                                hue.CONF_HOST: "0.0.0.0",
                                hue.CONF_ALLOW_HUE_GROUPS: True,
                                hue.CONF_ALLOW_UNREACHABLE: True,
                            },
                            {hue.CONF_HOST: "1.1.1.1"},
                        ]
                    }
                },
            )
            is True
        )

    mock_bridge.allow_groups = True
    mock_bridge.mock_light_responses.append({})
    mock_bridge.mock_group_responses.append(GROUP_RESPONSE)

    await setup_bridge(hass, mock_bridge)

    # mock_bridge2 = create_mock_bridge(hass)
    # mock_bridge2.allow_groups = True
    # mock_bridge2.mock_light_responses.append({})
    # mock_bridge2.mock_group_responses.append({})

    # await setup_bridge(hass, mock_bridge2)

    # Flow started for discovered bridge
    #    assert len(hass.config_entries.flow.async_progress()) == 1

    assert len(hass.services.async_services()) == 2

    # Config stored for domain.
    assert hass.data[hue.DATA_CONFIGS] == {
        "0.0.0.0": {
            hue.CONF_HOST: "0.0.0.0",
            hue.CONF_ALLOW_HUE_GROUPS: True,
            hue.CONF_ALLOW_UNREACHABLE: True,
        },
        "1.1.1.1": {hue.CONF_HOST: "1.1.1.1"},
    }

    await hass.services.async_call(
        "hue",
        "hue_activate_scene",
        {"group_name": "group_1", "scene_name": "my_scene"},
        blocking=True,
    )

    #    assert len(hass.states.async_all()) == 2

    new_group = hass.states.get("light.group_1")
    assert new_group is not None
    assert new_group.state == "on"


async def setup_bridge(hass, mock_bridge):
    """Load the Hue light platform with the provided bridge."""
    hass.config.components.add(hue.DOMAIN)
    config_entry = config_entries.ConfigEntry(
        1,
        hue.DOMAIN,
        "Mock Title",
        {"host": "mock-host"},
        "test",
        config_entries.CONN_CLASS_LOCAL_POLL,
        system_options={},
    )
    mock_bridge.config_entry = config_entry
    hass.data[hue.DOMAIN] = {config_entry.entry_id: mock_bridge}
    await hass.config_entries.async_forward_entry_setup(config_entry, "light")
    # To flush out the service call to update the group
    await hass.async_block_till_done()


async def test_setup_defined_hosts_no_known_auth(hass):
    """Test we initiate config entry if config bridge is not known."""
    assert (
        await async_setup_component(
            hass,
            hue.DOMAIN,
            {
                hue.DOMAIN: {
                    hue.CONF_BRIDGES: {
                        hue.CONF_HOST: "0.0.0.0",
                        hue.CONF_ALLOW_HUE_GROUPS: False,
                        hue.CONF_ALLOW_UNREACHABLE: True,
                    }
                }
            },
        )
        is True
    )

    # Flow started for discovered bridge
    assert len(hass.config_entries.flow.async_progress()) == 1

    # Config stored for domain.
    assert hass.data[hue.DATA_CONFIGS] == {
        "0.0.0.0": {
            hue.CONF_HOST: "0.0.0.0",
            hue.CONF_ALLOW_HUE_GROUPS: False,
            hue.CONF_ALLOW_UNREACHABLE: True,
        }
    }


async def test_config_passed_to_config_entry(hass):
    """Test that configured options for a host are loaded via config entry."""
    entry = MockConfigEntry(domain=hue.DOMAIN, data={"host": "0.0.0.0"})
    entry.add_to_hass(hass)
    mock_registry = Mock()
    with patch.object(hue, "HueBridge") as mock_bridge, patch(
        "homeassistant.helpers.device_registry.async_get_registry",
        return_value=mock_registry,
    ):
        mock_bridge.return_value.async_setup = AsyncMock(return_value=True)
        mock_bridge.return_value.api.config = Mock(
            mac="mock-mac",
            bridgeid="mock-bridgeid",
            modelid="mock-modelid",
            swversion="mock-swversion",
        )
        # Can't set name via kwargs
        mock_bridge.return_value.api.config.name = "mock-name"
        assert (
            await async_setup_component(
                hass,
                hue.DOMAIN,
                {
                    hue.DOMAIN: {
                        hue.CONF_BRIDGES: {
                            hue.CONF_HOST: "0.0.0.0",
                            hue.CONF_ALLOW_HUE_GROUPS: False,
                            hue.CONF_ALLOW_UNREACHABLE: True,
                        }
                    }
                },
            )
            is True
        )

    assert len(mock_bridge.mock_calls) == 2
    p_hass, p_entry = mock_bridge.mock_calls[0][1]

    assert p_hass is hass
    assert p_entry is entry

    assert len(mock_registry.mock_calls) == 1
    assert mock_registry.mock_calls[0][2] == {
        "config_entry_id": entry.entry_id,
        "connections": {("mac", "mock-mac")},
        "identifiers": {("hue", "mock-bridgeid")},
        "manufacturer": "Signify",
        "name": "mock-name",
        "model": "mock-modelid",
        "sw_version": "mock-swversion",
    }


async def test_unload_entry(hass, mock_bridge_setup):
    """Test being able to unload an entry."""
    entry = MockConfigEntry(domain=hue.DOMAIN, data={"host": "0.0.0.0"})
    entry.add_to_hass(hass)

    assert await async_setup_component(hass, hue.DOMAIN, {}) is True
    assert len(mock_bridge_setup.mock_calls) == 1

    mock_bridge_setup.async_reset = AsyncMock(return_value=True)
    assert await hue.async_unload_entry(hass, entry)
    assert len(mock_bridge_setup.async_reset.mock_calls) == 1
    assert hass.data[hue.DOMAIN] == {}


async def test_setting_unique_id(hass, mock_bridge_setup):
    """Test we set unique ID if not set yet."""
    entry = MockConfigEntry(domain=hue.DOMAIN, data={"host": "0.0.0.0"})
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, hue.DOMAIN, {}) is True
    assert entry.unique_id == "mock-id"


async def test_fixing_unique_id_no_other(hass, mock_bridge_setup):
    """Test we set unique ID if not set yet."""
    entry = MockConfigEntry(
        domain=hue.DOMAIN, data={"host": "0.0.0.0"}, unique_id="invalid-id"
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, hue.DOMAIN, {}) is True
    assert entry.unique_id == "mock-id"


async def test_fixing_unique_id_other_ignored(hass, mock_bridge_setup):
    """Test we set unique ID if not set yet."""
    MockConfigEntry(
        domain=hue.DOMAIN,
        data={"host": "0.0.0.0"},
        unique_id="mock-id",
        source=config_entries.SOURCE_IGNORE,
    ).add_to_hass(hass)
    entry = MockConfigEntry(
        domain=hue.DOMAIN,
        data={"host": "0.0.0.0"},
        unique_id="invalid-id",
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, hue.DOMAIN, {}) is True
    await hass.async_block_till_done()
    assert entry.unique_id == "mock-id"
    assert hass.config_entries.async_entries() == [entry]


async def test_fixing_unique_id_other_correct(hass, mock_bridge_setup):
    """Test we remove config entry if another one has correct ID."""
    correct_entry = MockConfigEntry(
        domain=hue.DOMAIN,
        data={"host": "0.0.0.0"},
        unique_id="mock-id",
    )
    correct_entry.add_to_hass(hass)
    entry = MockConfigEntry(
        domain=hue.DOMAIN,
        data={"host": "0.0.0.0"},
        unique_id="invalid-id",
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, hue.DOMAIN, {}) is True
    await hass.async_block_till_done()
    assert hass.config_entries.async_entries() == [correct_entry]


async def test_security_vuln_check(hass):
    """Test that we report security vulnerabilities."""
    assert await async_setup_component(hass, "persistent_notification", {})
    entry = MockConfigEntry(domain=hue.DOMAIN, data={"host": "0.0.0.0"})
    entry.add_to_hass(hass)

    config = Mock(bridgeid="", mac="", modelid="BSB002", swversion="1935144020")
    config.name = "Hue"

    with patch.object(
        hue,
        "HueBridge",
        Mock(
            return_value=Mock(
                async_setup=AsyncMock(return_value=True), api=Mock(config=config)
            )
        ),
    ):

        assert await async_setup_component(hass, "hue", {})

    await hass.async_block_till_done()

    state = hass.states.get("persistent_notification.hue_hub_firmware")
    assert state is not None
    assert "CVE-2020-6007" in state.attributes["message"]


async def test_setup_multiple_defined_hosts(hass):
    """Test we don't initiate a config entry if config bridge is known."""
    MockConfigEntry(domain="hue", data={"host": "0.0.0.0"}).add_to_hass(hass)

    with patch.object(hue, "async_setup_entry", return_value=True):
        assert (
            await async_setup_component(
                hass,
                hue.DOMAIN,
                {
                    hue.DOMAIN: {
                        hue.CONF_BRIDGES: [
                            {
                                hue.CONF_HOST: "0.0.0.0",
                                hue.CONF_ALLOW_HUE_GROUPS: False,
                                hue.CONF_ALLOW_UNREACHABLE: True,
                            },
                            {hue.CONF_HOST: "1.1.1.1"},
                        ]
                    }
                },
            )
            is True
        )

    # Flow started for discovered bridge
    assert len(hass.config_entries.flow.async_progress()) == 1

    # Config stored for domain.
    assert hass.data[hue.DATA_CONFIGS] == {
        "0.0.0.0": {
            hue.CONF_HOST: "0.0.0.0",
            hue.CONF_ALLOW_HUE_GROUPS: False,
            hue.CONF_ALLOW_UNREACHABLE: True,
        },
        "1.1.1.1": {hue.CONF_HOST: "1.1.1.1"},
    }
