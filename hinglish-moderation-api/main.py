from fastapi import FastAPI, HTTPException

from schemas import ModerateRequest, ModerateResponse
from services.pipeline import moderate_text
from services.rate_limiter import rate_limiter

app = FastAPI(title="Hinglish Moderation API")


@app.post("/api/v1/moderate", response_model=ModerateResponse)
def moderate(payload: ModerateRequest):
    if not rate_limiter.is_allowed(payload.user_id):
        raise HTTPException(
            status_code=429,
            detail="Your free daily limit has been reached. Please try again tomorrow.",
        )

    result = moderate_text(payload.text)
    return result


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
