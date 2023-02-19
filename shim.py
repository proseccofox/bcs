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
    self.rumble_effect = 0
    self.ignored_events = 0

  async def read_gamepad_input(self): # asyncronus read-out of events
    print("reading gamepad input")
    async for event in self.device_file.async_read_loop():
      if not(self.power_on): #stop reading device when power_on = false
        break

      if event.type == ecodes.EV_FF:
        print("Got FF event!")
        print(event)
        #dump(event)
        self.rumble_effect = 1
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

  async def send_rumbles(self): # asyncronus control of force feed back effects
    old_rumble_effect = self.rumble_effect
    while self.power_on:
      if old_rumble_effect != self.rumble_effect:
        # send to bp
        old_rumble_effect = self.rumble_effect
        print ("rumble effect changed to ", self.rumble_effect)
      await asyncio.sleep(0.2)

if __name__ == "__main__":
  logging.basicConfig(stream=sys.stdout, level=logging.INFO)
  main_power_on = True
  #bp_scan = False
  cpath_to_shim = {}
  cpath_to_bpdevice = {}

  async def controller_manager():
    global main_power_on
    cpath_to_read_input = {}
    cpath_to_send_output = {}
    while main_power_on:
      #print("controller manager loop")
      all_devices = [InputDevice(path) for path in list_devices()]
      ff_devices = [dev for dev in all_devices if ecodes.EV_FF in dev.capabilities()]
      new_connected_devs = [dev for dev in ff_devices if dev.path not in cpath_to_shim.keys()]
      new_disconnected_paths = [path for path in cpath_to_shim.keys() if path not in [dev.path for dev in ff_devices]]

      for dev in new_connected_devs:
        print("new controller connected:", dev)
        cpath_to_shim[dev.path] = gamepad_bp_shim(file = dev)
        cpath_to_read_input[dev.path] = asyncio.get_event_loop().create_task(cpath_to_shim[dev.path].read_gamepad_input())
        cpath_to_send_output[dev.path] = asyncio.get_event_loop().create_task(cpath_to_shim[dev.path].send_rumbles())

      for path in new_disconnected_paths:
        print("controller disconnected:", path)
        cpath_to_shim[path].power_on = False
        cpath_to_read_input.pop(path).cancel()
        cpath_to_send_output.pop(path).cancel()
        cpath_to_shim.pop(path)
        cpath_to_bpdevice.pop(path, None) # remove if exists

      await asyncio.sleep(5) # loop for new controllers every 5 seconds

    print("stopping controllers (may need to wake each controller)")
    for s in cpath_to_shim.values():
      s.power_on = False
    for t in cpath_to_read_input.values():
      t.cancel()
    for t in cpath_to_send_output.values():
      t.cancel()
    print("sum of ignored events:", sum(dev.ignored_events for dev in cpath_to_shim.values()))

  #async def bpmanager():
  #  global main_power_on
  #  global bp_scan

  #  bpclient = Client("BPS Client", ProtocolSpec.v3)
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
    #global bp_scan

    bpclient = Client("BPS Client", ProtocolSpec.v3)
    bpconnector = WebsocketConnector("ws://127.0.0.1:12345", logger=bpclient.logger)
    try:
      await bpclient.connect(bpconnector)
    except Exception as e:
      logging.error(f"Could not connect to intiface server, exiting: {e}")
      main_power_on = False
      return

    print("h for help, q to quit")

    while main_power_on:
      user_input = await aioconsole.ainput("BPS> ")
      if user_input == "q" or user_input == "quit":
        print("shitting down")
        main_power_on = False
        break
      if user_input == "h" or user_input == "help":
        print("""Buttplug Controller Shim BCS v0.1
        
        (h)elp, (q)uit, (p)air controller to buttplug

        buttplug helper commands:
        (bs)can for buttplugs, (bl)ist buttplugs, (bv)ibrate buttplug

        controller helper commands:
        (cl)ist controllers, (cv)ibrate controller
        """)
      elif user_input == "p" or user_input == "pair":
        cid = await aioconsole.ainput("  controller index> ")
        if (cid == "q" or bid == "quit"):
          print("  cancelled pairing")
          continue
        bid = await aioconsole.ainput("  buttplug index> ")
        if (bid in {"q", "quit", "c", "cancel"}):
          print("  cancelled pairing")
          continue
        if (cid > len(cpath_to_shim) or bid > len(cpath_to_bpdevice)):
          print("  invalid index")
          continue
      elif user_input in {"s", "bs", "scan"}:
        #bp_scan = True
        print("scanning for new buttplugs...")
        await bpclient.start_scanning()
        await asyncio.sleep(10)
        await bpclient.stop_scanning()
        print("...done scanning for buttplugs")
        bpclient.logger.info(f"Buttplug Devices: {bpclient.devices}")
        continue
      elif user_input in {"bl", "list buttplugs"}:
        #TODO get access to bpclient.devices
        for i, dev in enumerate(bpclient.devices):
          print(f"  {i}: {dev.name}")
        continue
      elif user_input in {"bv", "vibrate buttplugs"}:
        bid = await aioconsole.ainput("  buttplug index> ")
        if (bid in {"q", "quit", "c", "cancel"}):
          print("  cancelled vibrate buttplug")
          continue
        if (bid >= len(cpath_to_bpdevice)):
          print("  invalid index")
          continue
        # TODO get access to bpclient
        #await bpclient.devices[bid].rotatory_actuators[0].command(0.5, True)
        #await asyncio.sleep(1)
        #await bpclient.devices[bid].rotatory_actuators[0].command(0, True)
        break
      elif user_input in {"cl", "list controllers"}:
        for i, dev in enumerate(cpath_to_shim.values()):
          print(f"  {i}: {dev}")
        continue
      elif user_input in {"cv", "vibrate controller"}:
        print("  not implemented yet")
        continue
        #cid = await aioconsole.ainput("  controller index> ")
        #if (cid in {"q", "quit", "c", "cancel"}):
        #  print("  cancelled vibrate controller")
        #  continue
        #if (cid >= len(cpath_to_shim)):
        #  print("  invalid index")
        #  continue
    await bpclient.disconnect()

  futures = [ console_input(), controller_manager() ] #, bpmanager() ]
  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)
  loop.run_until_complete(asyncio.wait(futures))
  loop.close()

  print(" ")