import asyncio
import json
import sys
import threading
import random
import webview  # type: ignore
import websockets  # type: ignore
from cryptography.hazmat.primitives.asymmetric import rsa, padding  # type: ignore
from cryptography.hazmat.primitives import hashes, serialization  # type: ignore

NODE_NAME = sys.argv[1] if len(sys.argv) > 1 else "UnknownNode"
MY_MESH_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8001
NEIGHBOR_PORTS = [int(p) for p in sys.argv[3:]]

# Auto-compute dynamic UI bridge ports to prevent address bind collisions
MY_UI_PORT = 18000 + (MY_MESH_PORT % 1000)

SEEN_MESSAGES = set()
BLOCK_LIST = set()
UI_CLIENTS = set()
PEER_PUBLIC_KEYS = {}
PEER_LOCATIONS = {}  
WINDOW_INSTANCE = None

# Cryptographic Token Assembly
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=1024)
PUBLIC_KEY = PRIVATE_KEY.public_key()
MY_PUB_KEY_STR = PUBLIC_KEY.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')

def encrypt_message(message: str, target_pub_key_str: str) -> str:
    try:
        target_key = serialization.load_pem_public_key(target_pub_key_str.encode('utf-8'))
        return target_key.encrypt(
            message.encode('utf-8'),
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
        ).hex()
    except:
        return message

def decrypt_message(encrypted_hex: str) -> str:
    try:
        return PRIVATE_KEY.decrypt(
            bytes.fromhex(encrypted_hex),
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
        ).decode('utf-8')
    except:
        return "[Encrypted Content]"

async def external_peer_handler(websocket):
    async for raw_data in websocket:
        packet = json.loads(raw_data)
        msg_id = packet["id"]
        sender = packet["sender"]
        msg_type = packet["type"]
        payload = packet["payload"]
        ttl = packet["ttl"]

        if sender and packet.get("sender_pub_key"):
            PEER_PUBLIC_KEYS[sender] = packet["sender_pub_key"]
            if sender not in PEER_LOCATIONS:
                PEER_LOCATIONS[sender] = {
                    "angle": random.uniform(0, 360),
                    "distance": random.uniform(45, 135)
                }

        if sender in BLOCK_LIST and msg_type != "EMERGENCY":
            continue
        if msg_id in SEEN_MESSAGES:
            continue
        SEEN_MESSAGES.add(msg_id)

        if msg_type == "DM" and packet["target"] == NODE_NAME:
            payload = decrypt_message(payload)

        if msg_type == "EMERGENCY" and WINDOW_INSTANCE:
            WINDOW_INSTANCE.create_confirmation_dialog(
                "🚨 MESH SOS ALERT 🚨", 
                f"Node [{sender}] has placed an active emergency distress ping near you!"
            )

        packet["payload"] = payload
        packet["is_me"] = False
        packet["peers_map"] = PEER_LOCATIONS
        
        websockets.broadcast(UI_CLIENTS, json.dumps(packet))

        if ttl > 1:
            packet["ttl"] -= 1
            await relay_to_neighbors(packet)

async def ui_bridge_handler(websocket):
    UI_CLIENTS.add(websocket)
    try:
        await websocket.send(json.dumps({
            "type": "SET_NAME", 
            "payload": NODE_NAME,
            "peers_map": PEER_LOCATIONS
        }))
        
        async for raw_data in websocket:
            data = json.loads(raw_data)
            msg_type = data["type"]
            payload = data["payload"]
            target_peer = data.get("target", "")

            if msg_type == "BLOCK":
                BLOCK_LIST.add(payload)
                continue

            network_packet = {
                "id": f"{NODE_NAME}_{asyncio.get_event_loop().time()}",
                "sender": NODE_NAME,
                "sender_pub_key": MY_PUB_KEY_STR,
                "type": msg_type,
                "payload": payload,
                "target": target_peer,
                "ttl": 4
            }

            if msg_type == "DM":
                if target_peer in PEER_PUBLIC_KEYS:
                    network_packet["payload"] = encrypt_message(payload, PEER_PUBLIC_KEYS[target_peer])
                else:
                    await websocket.send(json.dumps({
                        "type": "SYSTEM_ERR", 
                        "payload": f"❌ Error: Send a standard 'Broadcast' from '{target_peer}' first to map security tokens."
                    }))
                    continue

            SEEN_MESSAGES.add(network_packet["id"])
            network_packet["is_me"] = True
            network_packet["payload"] = payload
            network_packet["peers_map"] = PEER_LOCATIONS
            
            await websocket.send(json.dumps(network_packet))
            await relay_to_neighbors(network_packet)
    finally:
        UI_CLIENTS.remove(websocket)

async def relay_to_neighbors(packet):
    for port in NEIGHBOR_PORTS:
        try:
            async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
                await ws.send(json.dumps(packet))
        except (ConnectionRefusedError, OSError):
            pass

async def main_server_entry():
    async with websockets.serve(ui_bridge_handler, "127.0.0.1", MY_UI_PORT), \
               websockets.serve(external_peer_handler, "127.0.0.1", MY_MESH_PORT):
        await asyncio.Future() 

def start_thread_loop():
    asyncio.run(main_server_entry())

if __name__ == "__main__":
    try:
        # Added encoding='utf-8' here to fix the charmap crash
        with open("index.html", "r", encoding="utf-8") as file: 
            html_content = file.read()
        import re
        html_content = re.sub(r"ws://127.0.0.1:\d+", f"ws://127.0.0.1:{MY_UI_PORT}", html_content)
        # Added encoding='utf-8' here too
        with open(f"index_{NODE_NAME}.html", "w", encoding="utf-8") as file: 
            file.write(html_content)
    except Exception as e: 
        print(f"File system mapping anomaly: {e}")

    threading.Thread(target=start_thread_loop, daemon=True).start()

    WINDOW_INSTANCE = webview.create_window(f"Concert Mesh - {NODE_NAME}", f"index_{NODE_NAME}.html", width=400, height=730)
    webview.start()