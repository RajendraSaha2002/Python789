from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn


# 1. Define the Input Data Model
class HouseFeatures(BaseModel):
    size_sqft: int
    bedrooms: int
    age_years: int
    location_score: int  # 1 to 10


# 2. Initialize the App
app = FastAPI()


# --- Root Endpoint (Good for checking if server is up) ---
@app.get("/")
def home():
    return {"message": "House Price AI is running! POST to /predict-house-price"}


# 3. The AI Logic Endpoint
@app.post("/predict-house-price")
def predict_price(features: HouseFeatures):
    print(f"Received request: {features}")

    # --- SIMULATED AI MODEL ---
    # In a real job, this would load a trained model (e.g., from scikit-learn)
    # Here, we use a logic-based formula to simulate a prediction.

    base_price = 50000  # Base land value
    price_per_sqft = 150
    bedroom_value = 15000
    location_premium = 5000
    age_penalty = 500

    estimated_price = (
            base_price +
            (features.size_sqft * price_per_sqft) +
            (features.bedrooms * bedroom_value) +
            (features.location_score * location_premium) -
            (features.age_years * age_penalty)
    )

    # Ensure price doesn't go below a minimum
    if estimated_price < 50000:
        estimated_price = 50000

    return {
        "estimated_price": estimated_price,
        "currency": "USD",
        "logic_used": "Linear Formula v1"
    }


# 4. Run the Server
if __name__ == "__main__":
    # Runs on localhost:8000
    uvicorn.run(app, host="127.0.0.1", port=8000)