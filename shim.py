#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Look for gamepad force feedback events and send them to the BP
"""
import logging
import asyncio
from evdev import InputDevice, ff, ecodes, list_devices
from buttplug import Client, WebsocketConnector, ProtocolSpec

class gamepad_bp_shim():
  def __init__(self, file = '/dev/input/event0'):
    self.device_file = InputDevice(file)
    print("opened device file", self.device_file.path)
    self.bpdevices = []
    self.bp_semaphores = []
    self.snoop_task = None
    self.ff_forwarder_tasks = []
    self.ignored_events = 0
    self.test_rumble_effect_id = 0
    self.buttplug_strength = 0.05

  def setup(self):
    assert self.snoop_task is None
    self.snoop_task = asyncio.create_task(self.read_gamepad_input())

    # setup test rumble effect
    rumble = ff.Rumble(strong_magnitude=0xc000, weak_magnitude=0x0000)
    duration_ms = 200
    effect = ff.Effect(ecodes.FF_RUMBLE, -1, 0, ff.Trigger(0, 0), ff.Replay(duration_ms, 0), ff.EffectType(ff_rumble_effect=rumble))
    self.test_rumble_effect_id = self.device_file.upload_effect(effect)

  async def read_gamepad_input(self):
    print("reading gamepad input")
    async for event in self.device_file.async_read_loop():
      if event.type == ecodes.EV_FF:
        #print("Got FF event!")
        #print(event)
        #dump(event)
        for s in self.bp_semaphores:
          s.release()
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

  def rumble_gamepad(self):
    repeat_count = 1
    self.device_file.write(ecodes.EV_FF, self.test_rumble_effect_id, repeat_count)
    for s in self.bp_semaphores:
      for i in range(5):
        s.release()

  def pair_to_buttplug(self, bpdevice):
    if bpdevice in self.bpdevices:
      print("buttplug already paired to this controller")
      return
    bpindex = len(self.bpdevices)
    self.bpdevices.append(bpdevice)
    self.bp_semaphores.append(asyncio.Semaphore(0))
    self.ff_forwarder_tasks.append(asyncio.create_task(self.forward_ff(bpindex)))

  async def forward_ff(self, bpindex):
    print(f"started ff forwarder task for index {bpindex}")
    while True:
      await self.bp_semaphores[bpindex].acquire()
      print(f"  vibrating {self.bpdevices[bpindex].name}")
      await self.bpdevices[bpindex].actuators[0].command(self.buttplug_strength)
      await asyncio.sleep(.1)
      await self.bpdevices[bpindex].actuators[0].command(0)

  def shutdown(self):
    for task in self.ff_forwarder_tasks:
      task.cancel()
    self.snoop_task.cancel()


class controller_manager():
  def __init__(self):
    self.cpath_to_shim = {}

  async def run(self):
    while True:
      all_devices = [InputDevice(path) for path in list_devices()]
      ff_devices = [dev for dev in all_devices if ecodes.EV_FF in dev.capabilities()]
      new_connected_devs = [dev for dev in ff_devices if dev.path not in self.cpath_to_shim.keys()]
      new_disconnected_paths = [path for path in self.cpath_to_shim.keys() if path not in [dev.path for dev in ff_devices]]

      for dev in new_connected_devs:
        print("new controller connected:", dev)
        self.cpath_to_shim[dev.path] = gamepad_bp_shim(file = dev)
        self.cpath_to_shim[dev.path].setup()

      for path in new_disconnected_paths:
        print("controller disconnected:", path)
        self.cpath_to_shim[path].shutdown()
        self.cpath_to_shim.pop(path)

      await asyncio.sleep(5) # check for new controllers every 5 seconds

  async def shutdown(self):
    print("stopping controllers")
    for shim in self.cpath_to_shim.values():
      shim.shutdown()
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