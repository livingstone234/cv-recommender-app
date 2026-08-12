from fastapi import FastAPI

from app.routers import analysis, cv, jobs

app = FastAPI(title="CV Recommender API")
app.include_router(cv.router)
app.include_router(analysis.router)
app.include_router(jobs.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
