# README

# install pre-reqs
python 3.8.10 or greater

sudo pip install aiortc websockets asyncio httpserver

# start the webrtc-mavlink bridge
python3 ./server/server.py

cd ./client && python3 -m http.server 8080

access the webpage at http://localhost:8080



