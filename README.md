# Buttplug Controller Shim (BCS)

A linux -> lib buttplug shim which sends gamepad rumble events (force feedback)
to your favorite sex toys!

# Deps 
- [python evdev](https://python-evdev.readthedocs.io/en/latest/tutorial.html)
- [buttplugpy](https://github.com/Siege-Wizard/buttplug-py)
- maybe [xpadneo]()

# Getting Started
Install xpadneo driver (required to read force feedback via xev.)
Requires rebooting after installation (not in instructions.)
Worked on v0.9.5, controller BLE firmware 5.13.

Then install deps
```
pip3 install evdev aioconsole
python3 shim.py
```

# Test
fftest /dev/input/event262
