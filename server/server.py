from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceCandidate, VideoStreamTrack, MediaStreamTrack
from aiortc.contrib.media import MediaPlayer
from os import system
from mavsdk import System
import asyncio
import json
import websockets
import usb.core
import usb.util
import subprocess
import time
import cv2

drone = None
drone = System()

pixhawkConnectionType = ["udp", "serial"]

# camera id goes here -> /dev/v4l/by-id/<ID here>
cameraPath = 2

config = RTCConfiguration()
config.iceServers = { 'urls': 'stun:stun.l.google.com:19302?transport=udp'}

def create_media_player(device_index=0):
    camera_device = f"/dev/video{device_index}"
    return MediaPlayer(f"{camera_device}", format="v4l2", options={"framerate": "30", "video_size": "640x480"})


class CameraVideoTrack(VideoStreamTrack):
    def __init__(self, player):
        super().__init__()
        self.player = player

    async def recv(self):
        frame = await self.player.video.recv()
        return frame

# configure for different mavlink connection types
def check_usb_devices():
    try:
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        output = result.stdout

        # check if the word 'Orange' is in the output
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

    if drone is None:
        return

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
    video_track = None

    mediaPlayer = create_media_player(device_index=2)

    video_track = CameraVideoTrack(mediaPlayer)
    
    pc.addTrack(video_track)

    # addTrack created from cameraID to PeerConnection

    @pc.on("datachannel")
    async def on_data_channel(channel):
        nonlocal data_channel
        data_channel = channel
        print("Data channel received:", channel.label)
        # if drone is not None:
        #     await continuous_data_sender(data_channel, drone)

    async for message in websocket:
        data = json.loads(message)
        if 'sdp' in data:
            sdp = RTCSessionDescription(sdp=data['sdp']['sdp'], type=data['sdp']['type'])
            # print('sdp', sdp)
            await pc.setRemoteDescription(sdp)
            if sdp.type == 'offer':
                await pc.setLocalDescription(await pc.createAnswer())
                await websocket.send(json.dumps({'sdp': {'sdp': pc.localDescription.sdp, 'type': pc.localDescription.type}}))
        elif 'candidate' in data:
            candidate = RTCIceCandidate(**data['candidate'])
            await pc.addIceCandidate(candidate)

async def main():
    server = await websockets.serve(websocket_handler, '0.0.0.0', 8765)
    print("Server running at ws://0.0.0.0:8765")
    # drone = await init_drone()
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
