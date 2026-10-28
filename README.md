# Aqara Cube Light Remote for Home Assistant (Matter)

[![Tests](https://github.com/Derinbay-Labs/ha-aqara-cube-blueprint/actions/workflows/tests.yml/badge.svg)](https://github.com/Derinbay-Labs/ha-aqara-cube-blueprint/actions/workflows/tests.yml)
[![Community forum](https://img.shields.io/badge/community-forum-41BDF5)](https://community.home-assistant.io/t/aqara-cube-light-remote-over-matter-hub-m2-signal-sync/1030703)

An automation blueprint that turns an Aqara Cube into a light remote, for cubes that
are paired to an Aqara hub and reach Home Assistant over Matter.

Existing cube blueprints expect the cube to be paired directly to Home Assistant
through ZHA or Zigbee2MQTT, where every gesture arrives as an event. When the cube
stays on an Aqara hub and the hub is shared with Home Assistant as a Matter bridge,
the gestures are not exposed at all. The hub can still forward them: an automation in
the Aqara app turns on a *signal sync* device for each gesture, and Home Assistant
sees that device as a binary sensor. This blueprint listens to those sensors.

| Gesture    | Action |
|------------|--------|
| Flip 90°   | Toggles the main lights: off if any of them is on, otherwise on. |
| Rotate     | Raises the main lights' brightness by one step (25 → 50 → 75 → 100 % with the default step), then wraps to the first step. |
| Double tap | Turns on the main and the extra lights. |
| Shake      | Turns off the main and the extra lights. |

Every gesture is optional; leave one empty to keep it for something else.

## Requirements

- Home Assistant 2024.10 or newer, with the
  [Matter integration](https://www.home-assistant.io/integrations/matter/) set up.
- An Aqara hub with Matter bridging and signal sync, such as the Hub M2, already
  added to Home Assistant as a Matter bridge.
- An Aqara Cube paired to that hub.

## Installation

[![Open your Home Assistant instance and show the blueprint import dialog with this blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDerinbay-Labs%2Fha-aqara-cube-blueprint%2Fblob%2Fmaster%2Fblueprints%2Fautomation%2Fderinbay%2Faqara_cube_matter_lights.yaml)

Or go to **Settings > Automations & scenes > Blueprints > Import blueprint** and paste:

```text
https://github.com/Derinbay-Labs/ha-aqara-cube-blueprint/blob/master/blueprints/automation/derinbay/aqara_cube_matter_lights.yaml
```

## Setup

### 1. Forward the gestures in the Aqara app

Do this once for each gesture you want to use.

1. Create a signal sync device on the hub and give it a name that says which gesture
   it carries, for example *Cube rotate*. Where signal sync sits in the menu differs
   between Aqara app versions.
2. Create an automation in the Aqara app: **if** the cube reports the gesture
   (*flip 90°*, *rotate*, *double tap* or *shake*), **then** turn on that signal sync
   device.
3. Make sure the new device is shared with Home Assistant through the hub's Matter
   bridge.

Home Assistant adds each signal sync device as a binary sensor, usually with the
*occupancy* device class. The hub turns it on briefly every time the gesture
happens, and it falls back to off on its own.

To check a sensor, open it in Home Assistant and perform the gesture: the history
should show a short *Detected* pulse.

### 2. Create the automation

Create an automation from the blueprint and fill in:

| Input | Required | Description |
|-------|----------|-------------|
| Flip 90° | No | Signal sync sensor for the flip gesture. |
| Rotate | No | Signal sync sensor for the rotate gesture. |
| Double tap | No | Signal sync sensor for the double tap gesture. |
| Shake | No | Signal sync sensor for the shake gesture. |
| Main lights | Yes | Lights that a flip toggles and a rotation dims. |
| Extra lights | No | Lights that only a double tap and a shake switch, such as a ceiling light. |
| Brightness step | No | How far each rotation raises the brightness, 5–50 %. Default 25 %. |

## Behaviour details

- **Rising edge only.** An action runs when a sensor goes from off to on. A sensor
  coming back from *unavailable*, for example after a hub restart, does not trigger
  anything.
- **Rotation follows the brightest light.** The next step is computed from the
  brightest main light that is on, and every main light is set to that step. If all
  main lights are off, a rotation turns them on at the first step.
- **One step per rotation.** A signal sync sensor only says that the cube was rotated,
  not in which direction or how far. Turning left and right both step up.
- **Queued.** Gestures made in quick succession run in order, up to five at a time;
  further gestures are dropped until the queue drains.

## Limitations

- **Latency.** Each gesture travels from the cube to the hub, through an Aqara
  automation, and over Matter to Home Assistant, so it is slower than a cube paired
  directly to Home Assistant.
- **Double tap.** Aqara automations do not always fire on a double tap. If the
  double tap sensor never pulses while the others do, the gesture is not leaving the
  hub, and the blueprint cannot work around that.
- **No direction or angle.** See *One step per rotation* above. For dimming in both
  directions, pair the cube directly to Home Assistant and use a ZHA or Zigbee2MQTT
  blueprint instead.

## Support

Questions and setup help: the
[community forum topic](https://community.home-assistant.io/t/aqara-cube-light-remote-over-matter-hub-m2-signal-sync/1030703).
Bugs and feature requests:
[GitHub issues](https://github.com/Derinbay-Labs/ha-aqara-cube-blueprint/issues).

## Development

The tests load the blueprint into a real Home Assistant core, create an automation
from it and check the light service calls for each gesture. Home Assistant core runs
on Linux and macOS.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements_test.txt
pytest
```

## Disclaimer

This project is not affiliated with, endorsed by or supported by Aqara, Lumi United
Technology or the Home Assistant project. Aqara is a trademark of Lumi United
Technology Co., Ltd.

## License

[MIT](LICENSE)
