import psycopg2
import time
import random
import io
import threading
from datetime import datetime

# DB CONFIG
DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "varrie75",
    "host": "localhost"
}


class MarketMaker:
    def __init__(self):
        self.running = True
        self.symbols = {
            1: {'ticker': 'AAPL', 'price': 150.00},
            2: {'ticker': 'GOOGL', 'price': 2800.00},
            3: {'ticker': 'TSLA', 'price': 700.00},
            4: {'ticker': 'AMZN', 'price': 3300.00},
            5: {'ticker': 'MSFT', 'price': 290.00}
        }

    def generate_batch(self):
        """
        Generates a CSV-like buffer in memory for high-speed COPY ingestion.
        """
        output = io.StringIO()

        # Simulate 100 micro-trades per batch
        for _ in range(100):
            sym_id = random.randint(1, 5)
            curr_price = self.symbols[sym_id]['price']

            # Random walk price movement
            change = random.uniform(-0.5, 0.5)
            new_price = round(curr_price + change, 2)
            self.symbols[sym_id]['price'] = new_price  # Update state

            volume = random.randint(1, 1000)
            now = datetime.now()

            # Format: symbol_id | price | volume | time
            output.write(f"{sym_id}\t{new_price}\t{volume}\t{now}\n")

        output.seek(0)
        return output

    def start_engine(self):
        print("🚀 HFT Engine Started. Blasting data using COPY protocol...")

        try:
            conn = psycopg2.connect(**DB_CONFIG)

            while self.running:
                # 1. Generate Data in RAM
                data_buffer = self.generate_batch()

                # 2. Use COPY (Bulk Load) instead of INSERT
                # This is 10x-100x faster than standard SQL inserts
                cursor = conn.cursor()
                cursor.copy_from(data_buffer, 'market_ticks', columns=('symbol_id', 'price', 'volume', 'tick_time'))
                conn.commit()
                cursor.close()

                print(f"⚡ Batch Ingested: {datetime.now().strftime('%H:%M:%S.%f')}")

                # Simulate frequency (HFT is fast, but we slow it slightly for visual demo)
                time.sleep(0.5)

        except Exception as e:
            print(f"Engine Crash: {e}")
        finally:
            conn.close()


if __name__ == "__main__":
    engine = MarketMaker()
    engine.start_engine()