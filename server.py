import asyncio
import json
import sys
import numpy as np
import sounddevice as sd
import websockets

# --- CONFIGURATION ---
HOST = "127.0.0.1"
PORT = 8765
SAMPLE_RATE = 44100
BLOCK_SIZE = 1024
# Increase MIC_SENSITIVITY (e.g. to 4.5 or 6.0) if your mic bar barely moves
MIC_SENSITIVITY = 3.5
# Set to a specific device number from the console list if Windows uses the wrong mic
DEVICE_INDEX = None

current_volume = 0.0
connected_clients = set()


def audio_callback(indata, frames, time, status):
    global current_volume
    if status:
        print(f"Audio status: {status}", file=sys.stderr)

    # Calculate RMS volume and scale to 0-100 to match the overlay's threshold
    rms = float(np.sqrt(np.mean(np.square(indata))))
    scaled = min(100.0, (rms * 100.0 * MIC_SENSITIVITY))

    # Smooth sudden drops slightly so speech feels natural
    current_volume = (current_volume * 0.2) + (scaled * 0.8)


async def ws_handler(websocket):
    connected_clients.add(websocket)
    print(f"\n[Overlay Connected] Active overlays: {len(connected_clients)}")
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.discard(websocket)
        print(f"\n[Overlay Disconnected] Active overlays: {len(connected_clients)}")


async def broadcast_volume():
    while True:
        vol_int = int(round(current_volume))
        # Live terminal meter so you can verify your mic before opening OBS
        bar = "#" * (vol_int // 4)
        sys.stdout.write(f"\rMic Vol: {vol_int:3d}/100 [{bar:<25}] ")
        sys.stdout.flush()

        if connected_clients:
            payload = json.dumps({"volume": vol_int})
            await asyncio.gather(
                *[client.send(payload) for client in list(connected_clients)],
                return_exceptions=True,
            )

        await asyncio.sleep(0.033)  # ~30 updates per second


async def main():
    print("=== Reactive Avatar Microphone Service ===")
    default_in = sd.query_devices(kind="input")
    print(f"Using Windows Input Device: {default_in['name']}")
    print(f"Starting WebSocket server on ws://{HOST}:{PORT}\n")

    while True:
        try:
            with sd.InputStream(
                device=DEVICE_INDEX,
                channels=1,
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_SIZE,
                callback=audio_callback,
            ):
                async with websockets.serve(ws_handler, HOST, PORT):
                    await broadcast_volume()
        except Exception as err:
            print(f"\n[Warning] Audio/WebSocket error: {err}. Retrying in 3 seconds...")
            await asyncio.sleep(3)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nService stopped.")
