from fastapi import FastAPI

app = FastAPI(title="CV Recommender API")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
