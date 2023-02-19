# BuzzyTux

A linux -> lib buttplug shim which sends gamepad controller events
to your favorite sex toys!

# Deps 
- [python evdev](https://python-evdev.readthedocs.io/en/latest/tutorial.html)
- [buttplugpy](https://github.com/Siege-Wizard/buttplug-py)

# More notes
https://github.com/buttplugio/awesome-buttplug


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