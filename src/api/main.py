from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(
    title="AstroGeo AI",
    description="MLOps Platform with Agentic AI",
    version="1.0.0"
)
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
async def root():
    return {"message": "AstroGeo AI is running!"}
@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "astrogeo-api",
        "version": "1.0.0"
    }
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)