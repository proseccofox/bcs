#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Look for gamepad force feedback events and send them to the BP
"""
import sys
import logging
import asyncio
import aioconsole
from evdev import InputDevice, ff, ecodes, list_devices
from buttplug import Client, WebsocketConnector, ProtocolSpec

class gamepad_bp_shim():
  def __init__(self, file = '/dev/input/event0'):
    self.power_on = True
    self.device_file = InputDevice(file)
    print("opened device file", self.device_file.path)
    self.bpdevice = None
    self.rumble_effect = 0
    self.ignored_events = 0

    # setup test rumble effect
    rumble = ff.Rumble(strong_magnitude=0xc000, weak_magnitude=0x0000)
    duration_ms = 200
    effect = ff.Effect(ecodes.FF_RUMBLE, -1, 0, ff.Trigger(0, 0), ff.Replay(duration_ms, 0), ff.EffectType(ff_rumble_effect=rumble))
    self.test_effect_id = self.device_file.upload_effect(effect)

  async def read_gamepad_input(self):
    print("reading gamepad input")
    async for event in self.device_file.async_read_loop():
      if not(self.power_on): #stop reading device when power_on = false
        break

      if event.type == ecodes.EV_FF:
        print("Got FF event!")
        print(event)
        #dump(event)
        self.rumble_effect += 1
      elif event.type == ecodes.EV_FF_STATUS:
        print("FF status event")
      elif event.type in {ecodes.EV_KEY, ecodes.EV_MSC, ecodes.EV_ABS, ecodes.EV_SYN}:
        self.ignored_events += 1
      else:
        print("got unrecognized event type:", event.type)
        #EV_SYN 0
        #EV_KEY 1 buttons?
        #EV_REL 2
        #EV_ABS 3 analog trigger or joystick
        #EV_MSC 4 buttons?
        #EV_SW  5

  async def rumble_gamepad(self):
    repeat_count = 1
    self.device_file.write(ecodes.EV_FF, self.test_effect_id, repeat_count)
    self.rumble_effect = 10

  async def rumble_buttplug(self): # asyncronus control of force feedback effects
    while self.power_on:
      if self.rumble_effect > 0:
        if (self.bpdevice == None):
          print("No buttplug device connected, skipping rumble")
        else:
          print(f"  vibrating {self.bpdevice.name}")
          await self.bpdevice.actuators[0].command(0.05)
          await asyncio.sleep(.1)
          await self.bpdevice.actuators[0].command(0)
        self.rumble_effect -= 2
      else:
        await asyncio.sleep(.2)

class controller_manager():
  def __init__(self):
    self.power_on = True
    self.cpath_to_read_input = {}
    self.cpath_to_send_output = {}
    self.cpath_to_shim = {}

  async def run(self):
    while self.power_on:
      all_devices = [InputDevice(path) for path in list_devices()]
      ff_devices = [dev for dev in all_devices if ecodes.EV_FF in dev.capabilities()]
      new_connected_devs = [dev for dev in ff_devices if dev.path not in self.cpath_to_shim.keys()]
      new_disconnected_paths = [path for path in self.cpath_to_shim.keys() if path not in [dev.path for dev in ff_devices]]

      for dev in new_connected_devs:
        print("new controller connected:", dev)
        self.cpath_to_shim[dev.path] = gamepad_bp_shim(file = dev)
        self.cpath_to_read_input[dev.path] = asyncio.get_event_loop().create_task(self.cpath_to_shim[dev.path].read_gamepad_input())
        self.cpath_to_send_output[dev.path] = asyncio.get_event_loop().create_task(self.cpath_to_shim[dev.path].rumble_buttplug())

      for path in new_disconnected_paths:
        print("controller disconnected:", path)
        self.cpath_to_shim[path].power_on = False
        self.cpath_to_read_input.pop(path).cancel()
        self.cpath_to_send_output.pop(path).cancel()
        self.cpath_to_shim.pop(path)

      await asyncio.sleep(5) # loop for new controllers every 5 seconds

  async def shutdown(self):
    print("stopping controllers (may need to wake each controller)")
    self.power_on = False
    for s in self.cpath_to_shim.values():
      s.power_on = False
    for t in self.cpath_to_read_input.values():
      t.cancel()
    for t in self.cpath_to_send_output.values():
      t.cancel()
    #print("sum of ignored events:", sum(dev.ignored_events for dev in self.cpath_to_shim.values()))

class buttplug_manager():
  def __init__(self):
    self.bpclient = None
    self.bpconnector = None

  async def run(self):
    self.bpclient = Client("BCS Client", ProtocolSpec.v3)
    self.bpconnector = WebsocketConnector("ws://127.0.0.1:12345", logger=self.bpclient.logger)
    try:
      await self.bpclient.connect(self.bpconnector)
    except Exception as e:
      logging.error(f"Could not connect to intiface server, exiting: {e}")
      exit

  async def scan(self):
    print("scanning for new buttplugs...")
    await self.bpclient.start_scanning()
    await asyncio.sleep(10)
    await self.bpclient.stop_scanning()
    print(f"  ...done scanning. Found {len(self.bpclient.devices)} buttplugs")
    #self.bpclient.logger.info(f"Buttplug Devices: {self.bpclient.devices}")

  async def shutdown(self):
    print("stopping buttplug client")
    await self.bpclient.disconnect()