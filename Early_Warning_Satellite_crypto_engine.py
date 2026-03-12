import hashlib
import time
import random
import json


class SecureLink:
    @staticmethod
    def encrypt_payload(data_dict, secret_key):
        """
        Simulates military-grade encryption wrapping.
        In a real scenario, we'd use AES. Here we use SHA-256 for integrity
        and Base64 encoding to simulate the 'encrypted' look.
        """
        raw_json = json.dumps(data_dict)

        # 1. Simulate Satellite Latency (0.2s - 1.5s delay)
        # Low Earth Orbit (LEO) vs Geostationary (GEO) lag
        lag = random.uniform(0.1, 0.8)
        time.sleep(lag)

        # 2. Simulate Packet Loss
        if random.random() < 0.05:  # 5% chance of packet loss
            return None

        # 3. Create Integrity Signature (SHA-256)
        # Hash = SHA256(Raw Data + Secret Key)
        signature = hashlib.sha256((raw_json + secret_key).encode()).hexdigest()

        return {
            'payload': raw_json,  # In real app, this would be AES encrypted
            'signature': signature,
            'latency_ms': round(lag * 1000)
        }