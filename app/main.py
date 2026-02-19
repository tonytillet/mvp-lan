from fastapi import FastAPI
from app.routes import games, players, votes, lan
from app.firestore import db

app = FastAPI(
    title="LAN-LOL Backend",
    description="Backend API for LAN-LOL gaming platform",
    version="1.0.0"
)

app.include_router(games.router, prefix="/games", tags=["Games"])
app.include_router(players.router, prefix="/players", tags=["Players"])
app.include_router(votes.router, prefix="/votes", tags=["Votes"])
app.include_router(lan.router, prefix="/lan", tags=["LAN"])

@app.get("/")
async def root():
    return {"message": "LAN-LOL Backend API", "status": "running"}

@app.get("/health")
async def health_check():
    """Health check endpoint that also verifies Firebase connection"""
    try:
        # Test Firebase connection
        test_doc = db.collection('health').document('test').get()
        return {
            "status": "healthy",
            "firebase": "connected",
            "database": "firestore"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "firebase": "disconnected",
            "error": str(e)
        }
