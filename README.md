# Buttplug Controller Shim (BCS)

A linux -> lib buttplug shim which sends gamepad rumble events (force feedback) to your favorite sex toys!

This is basically a linux version of the [Intiface Game Haptics Router](https://github.com/intiface/intiface-game-haptics-router)

Here's a [demo](https://www.youtube.com/watch?v=gPlhEoa3Fcg) taken from qdot's windows version but the concept is the same.

## Deps 
- [python evdev](https://python-evdev.readthedocs.io/en/latest/tutorial.html)
- [buttplugpy](https://github.com/Siege-Wizard/buttplug-py)
- [xpadneo](https://github.com/atar-axis/xpadneo)

## Getting Started
Install xpadneo driver (required to read force feedback via xev.)
Requires rebooting after installation (not in instructions.)
Tested on driver version v0.9.5, with xbox one controller BLE firmware 5.13.

Then install deps
```
pip3 install evdev aioconsole
```
and run the bcs console (expects to connect to the intiface server on localhost)
```
python3 shim.py
```

Workflow is as follows:
1. Connect your controller to the pc, bcs should automatically find it.
1. Scan for buttplugs with the `bs` command
1. Pair the controller to the buttplug with the `p` command.
  Here you type the controller evdev number (e.g. 262), then the buttplug index.
  The `bl` and `cl` commands should help you with this.

## Handy Test Command
to force your controller to vibrate (and a paired buttplug)
```
fftest /dev/input/event262
```
