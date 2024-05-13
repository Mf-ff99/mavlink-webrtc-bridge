from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer, RTCIceCandidate, VideoStreamTrack, MediaStreamTrack
from aiortc.contrib.media import MediaPlayer
from os import system
from mavsdk import System
import asyncio
import json
import websockets
import usb.core
import usb.util
import subprocess
import threading
import time
import cv2
import ssl

drone = None
drone = System()

pixhawkConnectionType = ["udp", "serial"]

# websocket ssl
# ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
# ssl_context.load_cert_chain('/domain.crt', '/key.pem')

# camera id goes here -> /dev/v4l/by-id/<ID here>
cameraPath = 2

# camera device index ie /dev/video2 would be 2
camera_id = 0

# configure STUN endpoints
ice_servers = [
    RTCIceServer(urls="stun:stun.l.google.com:19302")
]

config = RTCConfiguration(ice_servers)

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

        if 'Orange' in output:
            print('CubeOrange fmu found')
            return 'CubeOrange'
        if 'PX4' in output:
            print('PX4 fmu found')
            return 'PX4'
        else:
            print("No compatible MAVlink devices are connected. Searching...")
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
    if usbDevice == 'PX4':
        print('trying to connect to px4')
        await drone.connect(system_address="serial:///dev/ttyACM0:57600")
        print("Connected to ARK FMU on /dev/ttyACM0:57600!")
    return

async def close_peer_connection(pc, mediaPlayer, video_track):
    print(pc, 'pc')
    if pc:
        for sender in pc.getSenders():
            if sender:
                await sender.stop()
                print('sender stopped')

        # close the peer connection and video stream
        await pc.close()
        mediaPlayer.video.stop()
        pc = None
        return

async def continuous_data_sender(channel, drone, pc, mediaPlayer, video_track):
    """A coroutine to send data continuously over an open data channel."""
    if drone is None:
        return
    
    async def send_telemetry(telemetry_type, format_func):
        """Send formatted telemetry data over the data channel."""
        async for telemetry in telemetry_type:
            if channel.readyState == "open":
                message = format_func(telemetry)
                channel.send(message)
            else:
                print("Data channel is closed. Stopping all streams")
                await close_peer_connection(pc, mediaPlayer, video_track)
                break

    attitude_format = lambda t: f"Yaw: {t.yaw_deg}, Pitch: {t.pitch_deg}, Roll: {t.roll_deg}"
    gps_format = lambda t: f"Latitude: {t.latitude_deg}, Longitude: {t.longitude_deg}, Altitude: {t.absolute_altitude_m}"
    
    while True:
        if channel.readyState == "open" and drone:
            print('datachannel active')
            await asyncio.gather(
                send_telemetry(drone.telemetry.attitude_euler(), attitude_format),
                send_telemetry(drone.telemetry.position(), gps_format)
            )
        await asyncio.sleep(0.1)

# mediaPlayer = run_media_player(device_index=0)
async def websocket_handler(websocket, path):
    # pass iceServers config to PeerConnection
    mediaPlayer = create_media_player(camera_id)

    pc = RTCPeerConnection(config)
    data_channel = None
    video_track = None

    video_track = CameraVideoTrack(mediaPlayer)
    
    pc.addTrack(video_track)

    if video_track is not None:
        print('video track created')

    # addTrack created from cameraID to PeerConnection

    @pc.on("datachannel")
    async def on_data_channel(channel):
        nonlocal data_channel
        data_channel = channel
        print("Data channel received:", channel.label)
        if drone is not None:
            await continuous_data_sender(data_channel, drone, pc, mediaPlayer, video_track)

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
    drone = await init_drone()
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())