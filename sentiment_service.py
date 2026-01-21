from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn


# 1. Define the Data Model (Input)
class Review(BaseModel):
    text: str


# 2. Initialize the App
app = FastAPI()


# 3. Define the Logic Endpoint
@app.post("/analyze")
def analyze_sentiment(review: Review):
    print(f"Received review: {review.text}")

    # Simple "AI" Logic (Keyword matching)
    text = review.text.lower()

    if any(word in text for word in ["love", "happy", "great", "excellent", "good"]):
        sentiment = "Positive 😃"
        score = 0.9
    elif any(word in text for word in ["hate", "sad", "bad", "terrible", "worst"]):
        sentiment = "Negative 😠"
        score = 0.1
    else:
        sentiment = "Neutral 😐"
        score = 0.5

    # Return JSON response
    return {
        "sentiment": sentiment,
        "confidence": score,
        "original_text": review.text
    }


# 4. Run the Server
if __name__ == "__main__":
    # Runs on localhost:8000
    uvicorn.run(app, host="127.0.0.1", port=8000)