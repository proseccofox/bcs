#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Console app for BCS
"""
from shim import *

def printhelp():
  print("""Buttplug Controller Shim BCS v0.1

(h)elp, (q)uit, (p)air controller to buttplug

buttplug helper commands:
(bs)can for buttplugs, (bl)ist buttplugs, (bv)ibrate buttplug

controller helper commands:
(cl)ist controllers, (cv)ibrate controller
""")

async def console_app():
  cm = controller_manager()
  bm = buttplug_manager()

  cm_task = asyncio.create_task(cm.run())
  bm_task = asyncio.create_task(bm.run())

  await asyncio.sleep(1) # for console output

  printhelp()

  while True:
    user_input = await aioconsole.ainput("BCS> ")
    if user_input == "q" or user_input == "quit":
      print("shitting down")
      break
    elif user_input == "h" or user_input == "help":
      printhelp()
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
      if (cm.cpath_to_shim[path] == None):
        print("  invalid controller event id")
        continue
      if (int(bid) > len(bm.bpclient.devices)):
        print("  invalid buttplug index")
        continue
      print(f"  connecting controller {path} to buttplug {bid} - {bm.bpclient.devices[int(bid)].name}...")
      cm.cpath_to_shim[path].bpdevice = bm.bpclient.devices[int(bid)]
      await cm.cpath_to_shim[path].rumble_gamepad()

    elif user_input in {"s", "bs", "scan"}:
      await bm.scan()
    elif user_input in {"bl", "list buttplugs"}:
      for i in range(len(bm.bpclient.devices)):
        print(f"  {i}: {bm.bpclient.devices[int(i)].name}")
    elif user_input in {"bv", "vibrate buttplugs"}:
      bid = await aioconsole.ainput("  buttplug index> ")
      if (bid in {"q", "quit", "c", "cancel"}):
        print("  cancelled vibrate buttplug")
        continue
      if (int(bid) > len(bm.bpclient.devices)):
        print("  invalid index")
        continue
      device = bm.bpclient.devices[int(bid)];
      print(f"  vibrating {device.name}")
      await device.actuators[0].command(0.5)
      await asyncio.sleep(.5)
      await device.actuators[0].command(0)

    elif user_input in {"cl", "list controllers"}:
      for i, dev in enumerate(cm.cpath_to_shim.values()):
        print(f"  {dev.device_file.path}")
    elif user_input in {"cv", "vibrate controller"}:
      cid = await aioconsole.ainput("  controller event id> ")
      if (cid in {"q", "quit", "c", "cancel"}):
        print("  cancelled vibrate controller")
        continue
      path = f"/dev/input/event{cid}"
      if (cm.cpath_to_shim[path] == None):
        print("  invalid controller event id")
      print(f"  vibrating {path}")
      await cm.cpath_to_shim[path].rumble_gamepad()
    elif user_input == "":
      continue
    else:
      print("  invalid command (try 'h' for help)")
      continue

  cm_task.cancel()
  await cm.shutdown()
  bm_task.cancel()
  await bm.shutdown()

if __name__ == "__main__":
  logging.basicConfig(stream=sys.stdout, level=logging.INFO)
  main = [console_app()]
  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)
  loop.run_until_complete(asyncio.wait(main))
  loop.close()
