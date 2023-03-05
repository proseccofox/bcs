# Buttplug Controller Shim (BCS) 🍑🐝
This program snoops gamepad rumble events (linux calls them force feedback events) and forwards them to your favorite sex toys!

This is basically a linux version of the [Intiface Game Haptics Router](https://github.com/intiface/intiface-game-haptics-router)

Here's a [demo](https://www.youtube.com/watch?v=gPlhEoa3Fcg) taken from qdot's windows version. The concept is the same but runs on linux.

## Features

- When a controller vibrates so do you.
- Pair multiple buttplugs to a controller.
- Pair multiple controllers to a buttplug.
- Xbox controllers are automatically discovered

## Deps

- [python evdev](https://python-evdev.readthedocs.io/en/latest/tutorial.html)
- [buttplugpy](https://github.com/Siege-Wizard/buttplug-py)
- [xpadneo](https://github.com/atar-axis/xpadneo) (for Xbox controllers)

## Getting Started

Install xpadneo driver which required for force feedback on Xbox controllers.
Note this may require rebooting after installation which is not in their
installation instructions.
Tested on driver version v0.9.5, with Xbox one controller BLE firmware 5.13.

Install dependencies:

```bash
pip3 install evdev aioconsole
```

Workflow is as follows:

1. Start the intiface server.
1. Run the BCS console

  ```bash
  python3 console.py
  ```

1. Connect your controller to the pc, bcs should automatically find it.
1. Scan for buttplugs with the `bs` command
1. Pair the controller to the buttplug with the `p` command.
  Here you type the controller evdev number (e.g. 262), then the buttplug index.
  The `bl` and `cl` commands should help with this.

## Acknowledgements

To my loving bf. Happy birthday :)
