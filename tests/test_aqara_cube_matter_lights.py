"""Run the blueprint in a real Home Assistant core and check the light calls."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch

from homeassistant.components import automation
from homeassistant.components.automation.config import AUTOMATION_BLUEPRINT_SCHEMA
from homeassistant.components.blueprint import models
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.setup import async_setup_component
from homeassistant.util.yaml import load_yaml_dict
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

BLUEPRINT = "derinbay/aqara_cube_matter_lights.yaml"
BLUEPRINT_FILE = Path(__file__).parents[1] / "blueprints" / "automation" / BLUEPRINT

FLIP = "binary_sensor.cube_flip"
ROTATE = "binary_sensor.cube_rotate"
DOUBLE_TAP = "binary_sensor.cube_double_tap"
SHAKE = "binary_sensor.cube_shake"
MAIN = ["light.ceiling", "light.lamp"]
EXTRA = ["light.desk"]


@pytest.fixture(autouse=True)
def load_blueprint_from_repo() -> Iterator[None]:
    """Serve the blueprint from this repository instead of the config folder."""

    def load(self: models.DomainBlueprints, path: str) -> models.Blueprint:
        assert path == BLUEPRINT
        return models.Blueprint(
            load_yaml_dict(BLUEPRINT_FILE),
            expected_domain=self.domain,
            path=path,
            schema=AUTOMATION_BLUEPRINT_SCHEMA,
        )

    with patch.object(models.DomainBlueprints, "_load_blueprint", load):
        yield


@pytest.fixture
def calls(hass: HomeAssistant) -> dict[str, list[ServiceCall]]:
    """Record light service calls without a light platform."""
    return {
        "turn_on": async_mock_service(hass, "light", "turn_on"),
        "turn_off": async_mock_service(hass, "light", "turn_off"),
    }


async def setup_blueprint(hass: HomeAssistant, **inputs: Any) -> None:
    """Create one automation from the blueprint."""
    inputs = {
        "flip_sensor": FLIP,
        "rotate_sensor": ROTATE,
        "double_tap_sensor": DOUBLE_TAP,
        "shake_sensor": SHAKE,
        "main_lights": MAIN,
        "extra_lights": EXTRA,
    } | inputs
    # None leaves an input out, so the blueprint default applies.
    inputs = {key: value for key, value in inputs.items() if value is not None}
    for sensor in (FLIP, ROTATE, DOUBLE_TAP, SHAKE):
        hass.states.async_set(sensor, "off")
    assert await async_setup_component(
        hass,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "id": "cube",
                "alias": "Cube",
                "use_blueprint": {"path": BLUEPRINT, "input": inputs},
            }
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get("automation.cube")


async def gesture(hass: HomeAssistant, sensor: str) -> None:
    """Pulse a signal sync sensor the way the hub does."""
    hass.states.async_set(sensor, "on")
    await hass.async_block_till_done()
    hass.states.async_set(sensor, "off")
    await hass.async_block_till_done()


def set_lights(hass: HomeAssistant, **brightness: int | None) -> None:
    """Set main lights by object id; None means off."""
    for object_id, value in brightness.items():
        if value is None:
            hass.states.async_set(f"light.{object_id}", "off")
        else:
            hass.states.async_set(f"light.{object_id}", "on", {"brightness": value})


async def test_flip_turns_on_when_all_off(hass: HomeAssistant, calls) -> None:
    set_lights(hass, ceiling=None, lamp=None)
    await setup_blueprint(hass)

    await gesture(hass, FLIP)

    assert len(calls["turn_on"]) == 1
    assert calls["turn_on"][0].data["entity_id"] == MAIN
    assert not calls["turn_off"]


async def test_flip_turns_off_when_any_on(hass: HomeAssistant, calls) -> None:
    set_lights(hass, ceiling=None, lamp=128)
    await setup_blueprint(hass)

    await gesture(hass, FLIP)

    assert len(calls["turn_off"]) == 1
    assert calls["turn_off"][0].data["entity_id"] == MAIN
    assert not calls["turn_on"]


@pytest.mark.parametrize(
    ("brightness", "expected"),
    [
        (None, 25),
        (64, 50),  # 25%
        (127, 75),  # 50%, rounded down
        (191, 100),  # 75%
        (230, 100),  # 90%
        (255, 25),  # 100% wraps
    ],
)
async def test_rotate_steps_brightness(
    hass: HomeAssistant, calls, brightness: int | None, expected: int
) -> None:
    set_lights(hass, ceiling=brightness, lamp=None)
    await setup_blueprint(hass)

    await gesture(hass, ROTATE)

    assert len(calls["turn_on"]) == 1
    assert calls["turn_on"][0].data["entity_id"] == MAIN
    assert calls["turn_on"][0].data["brightness_pct"] == expected


async def test_rotate_follows_brightest_light(hass: HomeAssistant, calls) -> None:
    set_lights(hass, ceiling=64, lamp=191)
    await setup_blueprint(hass)

    await gesture(hass, ROTATE)

    assert calls["turn_on"][0].data["brightness_pct"] == 100


@pytest.mark.parametrize(
    ("brightness", "expected"),
    [
        (77, 60),  # 30%
        (230, 100),  # 90%
        (255, 30),  # 100% wraps to the custom step
    ],
)
async def test_rotate_uses_custom_step(
    hass: HomeAssistant, calls, brightness: int, expected: int
) -> None:
    set_lights(hass, ceiling=brightness, lamp=None)
    await setup_blueprint(hass, brightness_step=30)

    await gesture(hass, ROTATE)

    assert calls["turn_on"][0].data["brightness_pct"] == expected


async def test_double_tap_turns_on_everything(hass: HomeAssistant, calls) -> None:
    await setup_blueprint(hass)

    await gesture(hass, DOUBLE_TAP)

    assert calls["turn_on"][0].data["entity_id"] == MAIN + EXTRA


async def test_shake_turns_off_everything(hass: HomeAssistant, calls) -> None:
    await setup_blueprint(hass)

    await gesture(hass, SHAKE)

    assert calls["turn_off"][0].data["entity_id"] == MAIN + EXTRA


async def test_only_rising_edge_triggers(hass: HomeAssistant, calls) -> None:
    set_lights(hass, ceiling=None, lamp=None)
    await setup_blueprint(hass)

    hass.states.async_set(FLIP, "unavailable")
    await hass.async_block_till_done()
    hass.states.async_set(FLIP, "on")
    await hass.async_block_till_done()

    assert not calls["turn_on"]


async def test_gestures_and_extra_lights_are_optional(
    hass: HomeAssistant, calls
) -> None:
    set_lights(hass, ceiling=None, lamp=None)
    await setup_blueprint(
        hass,
        rotate_sensor=None,
        double_tap_sensor=None,
        shake_sensor=None,
        extra_lights=None,
    )

    await gesture(hass, SHAKE)
    await gesture(hass, FLIP)

    assert not calls["turn_off"]
    assert calls["turn_on"][0].data["entity_id"] == MAIN
