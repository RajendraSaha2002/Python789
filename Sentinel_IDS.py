
import os
import json
import asyncio
import datetime
import psycopg2
import websockets
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- CONFIGURATION ---
MONITOR_PATH = "./secure_vault"  # Folder to watch
CRITICAL_FILES = ["config.sys", "secrets.txt"]  # Trigger lockout if touched
DB_CONFIG = {
    "dbname": "sentinel_db",
    "user": "postgres",
    "password": "varrie75",
    "host": "localhost"
}

# Global set of connected websocket clients
CONNECTED_CLIENTS = set()

# Ensure monitor path exists
if not os.path.exists(MONITOR_PATH):
    os.makedirs(MONITOR_PATH)


def log_to_db(event_type, path, severity):
    """Inserts event into the partitioned Postgres table."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO security_logs (event_type, file_path, severity, details) VALUES (%s, %s, %s, %s)",
            (event_type, path, severity, f"Sentinel detected {event_type} on {path}")
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database Error: {e}")


class SentinelHandler(FileSystemEventHandler):
    """Watchdog handler that translates file events to JSON alerts."""

    def on_any_event(self, event):
        if event.is_directory:
            return

        filename = os.path.basename(event.src_path)
        severity = "CRITICAL" if filename in CRITICAL_FILES else "LOW"

        alert = {
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
            "event": event.event_type.upper(),
            "file": filename,
            "severity": severity
        }

        # 1. Log to Partitioned Database
        log_to_db(event.event_type, event.src_path, severity)

        # 2. Broadcast to UI via WebSockets
        if CONNECTED_CLIENTS:
            message = json.dumps(alert)
            asyncio.run_coroutine_threadsafe(broadcast(message), loop)


async def broadcast(message):
    for websocket in CONNECTED_CLIENTS:
        try:
            await websocket.send(message)
        except:
            pass


async def ws_handler(websocket, path):
    """Registers new UI clients for the real-time stream."""
    CONNECTED_CLIENTS.add(websocket)
    print(f"UI Client Connected. Active Monitors: {len(CONNECTED_CLIENTS)}")
    try:
        await websocket.wait_closed()
    finally:
        CONNECTED_CLIENTS.remove(websocket)


def start_watchdog():
    observer = Observer()
    observer.schedule(SentinelHandler(), MONITOR_PATH, recursive=False)
    observer.start()
    print(f"Sentinel Monitor active on: {MONITOR_PATH}")


async def main():
    global loop
    loop = asyncio.get_running_loop()

    # Start the directory observer in the background
    start_watchdog()

    # Start WebSocket Server on port 8765
    async with websockets.serve(ws_handler, "localhost", 8765):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())