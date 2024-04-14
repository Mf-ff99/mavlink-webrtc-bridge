# import asyncio
# import json
# from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
# import websockets
# from mavsdk import System
# import usb.core
# import usb.util
# import os
# from os import system
# import subprocess
# import time
# from pymavlink import mavutil

# drone = None
# drone = System()

# pixhawkConnectionType = ["udp", "serial"]

# # configure for different vehicle connection types
# def check_usb_devices():
#     try:
#         # Query serial USB device IDs
#         output = os.listdir('/dev/serial/by-id')

#         # Checks if the word 'Orange' is in the output
#         for file in output:
#             if 'Orange' in file:
#                 return 'CubeOrange'
#             else:
#                 print("No compatible hardware devices are connected. Searching...")
#                 time.sleep(1)
#                 check_usb_devices()
#     except Exception as e:
#         print(f"An error occurred while searching for a serial connection. Are you sure the device is plugged in? : {e}")


# async def init_drone():
#     usbDevice = None
#     usbDevice = check_usb_devices()

#     if usbDevice == 'CubeOrange':
#         drone = mavutil.mavlink_connection('/dev/ttyACM0', baud=57600)
#         print("Connected to CubeOrange on /dev/ttyACM0:57600!")
#     else:
#         print(f"no devices found, checking again in 1 second(s)")
#         asyncio.sleep(1)
#         return
#     return

# async def continuous_data_sender(channel, drone):
#     """A coroutine to send data continuously over an open data channel."""

#     while True:
#         if (channel.readyState == "open") and drone:
#             print('datachannel active')

            
#             async for telemetry in drone.telemetry.attitude_euler():
#                 if channel.readyState == "open":
#                     message = f"Yaw: {telemetry.yaw_deg}, Pitch: {telemetry.pitch_deg}, Roll: {telemetry.roll_deg}"
#                     channel.send(message)
#                 else:
#                     print("Data channel is closed. Stopping telemetry stream.")
#                     break
#         await asyncio.sleep(.01)

# async def websocket_handler(websocket, path):
#     pc = RTCPeerConnection()
#     data_channel = None

#     @pc.on("datachannel")
#     async def on_data_channel(channel):
#         nonlocal data_channel
#         data_channel = channel
#         print("Data channel received:", channel.label)
#         await continuous_data_sender(data_channel, drone)

#     async for message in websocket:
#         data = json.loads(message)
#         if 'sdp' in data:
#             sdp = RTCSessionDescription(sdp=data['sdp']['sdp'], type=data['sdp']['type'])
#             await pc.setRemoteDescription(sdp)
#             if sdp.type == 'offer':
#                 await pc.setLocalDescription(await pc.createAnswer())
#                 await websocket.send(json.dumps({'sdp': {'sdp': pc.localDescription.sdp, 'type': pc.localDescription.type}}))
#         elif 'candidate' in data:
#             candidate = RTCIceCandidate(**data['candidate'])
#             await pc.addIceCandidate(candidate)

# async def main():
#     server = await websockets.serve(websocket_handler, 'localhost', 8765)
#     print("Server running at ws://localhost:8765")
#     drone = await init_drone()
#     await server.wait_closed()

# if __name__ == "__main__":
#     asyncio.run(main())

import asyncio
import json
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
import websockets
from mavsdk import System
import usb.core
import usb.util
from os import system
import subprocess
import time

drone = None
drone = System()

pixhawkConnectionType = ["udp", "serial"]

# configure for different vehicle connection types
def check_usb_devices():
    try:
        # Run the 'lsusb' command and capture its output
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        output = result.stdout

        # Check if the word 'Orange' is in the output
        if 'Orange' in output:
            return 'CubeOrange'
        else:
            print("No compatible hardware devices are connected. Searching...")
            time.sleep(1000)
            check_usb_devices()
    except Exception as e:
        print(f"An error occurred: {e}")


async def init_drone():
    usbDevice = None
    usbDevice = check_usb_devices()

    if usbDevice == 'CubeOrange':
        await drone.connect(system_address="serial:///dev/ttyACM0:57600")
        print("Connected to CubeOrange on /dev/ttyACM0:57600!")
    return

async def continuous_data_sender(channel, drone):
    """A coroutine to send data continuously over an open data channel."""

    while True:
        if (channel.readyState == "open") and drone:
            print('datachannel active')
            async for telemetry in drone.telemetry.attitude_euler():
                if channel.readyState == "open":
                    message = f"Yaw: {telemetry.yaw_deg}, Pitch: {telemetry.pitch_deg}, Roll: {telemetry.roll_deg}"
                    channel.send(message)
                else:
                    print("Data channel is closed. Stopping telemetry stream.")
                    break
        await asyncio.sleep(.1)

async def websocket_handler(websocket, path):
    pc = RTCPeerConnection()
    data_channel = None

    @pc.on("datachannel")
    async def on_data_channel(channel):
        nonlocal data_channel
        data_channel = channel
        print("Data channel received:", channel.label)
        await continuous_data_sender(data_channel, drone)

    async for message in websocket:
        data = json.loads(message)
        if 'sdp' in data:
            sdp = RTCSessionDescription(sdp=data['sdp']['sdp'], type=data['sdp']['type'])
            await pc.setRemoteDescription(sdp)
            if sdp.type == 'offer':
                await pc.setLocalDescription(await pc.createAnswer())
                await websocket.send(json.dumps({'sdp': {'sdp': pc.localDescription.sdp, 'type': pc.localDescription.type}}))
        elif 'candidate' in data:
            candidate = RTCIceCandidate(**data['candidate'])
            await pc.addIceCandidate(candidate)

async def main():
    server = await websockets.serve(websocket_handler, 'localhost', 8765)
    print("Server running at ws://localhost:8765")
    drone = await init_drone()
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())