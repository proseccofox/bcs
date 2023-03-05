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

if __name__ == "__main__":
  logging.basicConfig(stream=sys.stdout, level=logging.INFO)
  main_power_on = True
  cpath_to_shim = {}

  async def controller_manager():
    global main_power_on
    cpath_to_read_input = {}
    cpath_to_send_output = {}
    while main_power_on:
      all_devices = [InputDevice(path) for path in list_devices()]
      ff_devices = [dev for dev in all_devices if ecodes.EV_FF in dev.capabilities()]
      new_connected_devs = [dev for dev in ff_devices if dev.path not in cpath_to_shim.keys()]
      new_disconnected_paths = [path for path in cpath_to_shim.keys() if path not in [dev.path for dev in ff_devices]]

      for dev in new_connected_devs:
        print("new controller connected:", dev)
        cpath_to_shim[dev.path] = gamepad_bp_shim(file = dev)
        cpath_to_read_input[dev.path] = asyncio.get_event_loop().create_task(cpath_to_shim[dev.path].read_gamepad_input())
        cpath_to_send_output[dev.path] = asyncio.get_event_loop().create_task(cpath_to_shim[dev.path].rumble_buttplug())

      for path in new_disconnected_paths:
        print("controller disconnected:", path)
        cpath_to_shim[path].power_on = False
        cpath_to_read_input.pop(path).cancel()
        cpath_to_send_output.pop(path).cancel()
        cpath_to_shim.pop(path)

      await asyncio.sleep(5) # loop for new controllers every 5 seconds

    print("stopping controllers (may need to wake each controller)")
    for s in cpath_to_shim.values():
      s.power_on = False
    for t in cpath_to_read_input.values():
      t.cancel()
    for t in cpath_to_send_output.values():
      t.cancel()
    #print("sum of ignored events:", sum(dev.ignored_events for dev in cpath_to_shim.values()))

  #async def bpmanager():
  #  global main_power_on
  #  global bp_scan

  #  bpclient = Client("BCS Client", ProtocolSpec.v3)
  #  bpconnector = WebsocketConnector("ws://127.0.0.1:12345", logger=bpclient.logger)
  #  try:
  #    await bpclient.connect(bpconnector)
  #  except Exception as e:
  #    logging.error(f"Could not connect to intiface server, exiting: {e}")
  #    exit

  #  while main_power_on:
  #    print("bpmanager loop")
  #    if bp_scan:
  #      bp_scan = False
  #      print("scanning for new buttplugs...")
  #      await bpclient.start_scanning()
  #      await asyncio.sleep(10)
  #      await bpclient.stop_scanning()
  #      print("...done scanning for buttplugs")
  #      bpclient.logger.info(f"Buttplug Devices: {bpclient.devices}")
  #    await asyncio.sleep(5)
  #  await bpclient.disconnect()

  async def console_input():
    global main_power_on

    bpclient = Client("BCS Client", ProtocolSpec.v3)
    bpconnector = WebsocketConnector("ws://127.0.0.1:12345", logger=bpclient.logger)
    try:
      await bpclient.connect(bpconnector)
    except Exception as e:
      logging.error(f"Could not connect to intiface server, exiting: {e}")
      main_power_on = False
      return

    print("h for help, q to quit")

    while main_power_on:
      user_input = await aioconsole.ainput("BCS> ")
      if user_input == "q" or user_input == "quit":
        print("shitting down")
        main_power_on = False
        break
      elif user_input == "h" or user_input == "help":
        print("""Buttplug Controller Shim BCS v0.1

(h)elp, (q)uit, (p)air controller to buttplug

buttplug helper commands:
(bs)can for buttplugs, (bl)ist buttplugs, (bv)ibrate buttplug

controller helper commands:
(cl)ist controllers, (cv)ibrate controller
""")
      elif user_input == "p" or user_input == "pair":
        cid = await aioconsole.ainput("  controller event id> ")
        if (cid in {"q", "quit", "c", "cancel"}):
          print("  cancelled pairing")
          continue
        bid = await aioconsole.ainput("  buttplug index> ")
        if (bid in {"q", "quit", "c", "cancel"}):
          print("  cancelled pairing")
          continue
        path = f"/dev/input/event{cid}"
        if (cpath_to_shim[path] == None):
          print("  invalid controller event id")
          continue
        if (int(bid) > len(bpclient.devices)):
          print("  invalid buttplug index")
          continue
        print(f"  connecting controller {path} to buttplug {bid} - {bpclient.devices[int(bid)].name}...")
        cpath_to_shim[path].bpdevice = bpclient.devices[int(bid)]
        await cpath_to_shim[path].rumble_gamepad()
        # TODO vibrate controller and buttplug to indicate success

      elif user_input in {"s", "bs", "scan"}:
        print("  scanning for new buttplugs...")
        await bpclient.start_scanning()
        await asyncio.sleep(10)
        await bpclient.stop_scanning()
        print("    ...done scanning for buttplugs")
        for i in range(len(bpclient.devices)):
          print(f"  {i}: {bpclient.devices[int(i)].name}")
        continue
      elif user_input in {"bl", "list buttplugs"}:
        for i in range(len(bpclient.devices)):
          print(f"  {i}: {bpclient.devices[int(i)].name}")
        continue
      elif user_input in {"bv", "vibrate buttplugs"}:
        bid = await aioconsole.ainput("  buttplug index> ")
        if (bid in {"q", "quit", "c", "cancel"}):
          print("  cancelled vibrate buttplug")
          continue
        if (int(bid) > len(bpclient.devices)):
          print("  invalid index")
          continue
        device = bpclient.devices[int(bid)];
        print(f"  vibrating {device.name}")
        await device.actuators[0].command(0.5)
        await asyncio.sleep(.5)
        await device.actuators[0].command(0)
        continue

      elif user_input in {"cl", "list controllers"}:
        for i, dev in enumerate(cpath_to_shim.values()):
          print(f"  {dev.device_file.path}")
        continue
      elif user_input in {"cv", "vibrate controller"}:
        cid = await aioconsole.ainput("  controller event id> ")
        if (cid in {"q", "quit", "c", "cancel"}):
          print("  cancelled vibrate controller")
          continue
        path = f"/dev/input/event{cid}"
        if (cpath_to_shim[path] == None):
          print("  invalid controller event id")
        print(f"  vibrating {path}")
        await cpath_to_shim[path].rumble_gamepad()
      else:
        continue
    await bpclient.disconnect()

  futures = [ console_input(), controller_manager() ] #, bpmanager() ]
  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)
  loop.run_until_complete(asyncio.wait(futures))
  loop.close()

  print(" ")
