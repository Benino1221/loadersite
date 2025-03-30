from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from datetime import datetime, timedelta
import bcrypt
import jwt
import os
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

app = FastAPI(title="Loader Admin API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
try:
    # Use environment variable for MongoDB URL in production
    mongo_url = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
    # Test the connection
    client.server_info()
    db = client['loader_admin']
    print("Successfully connected to MongoDB!")
except (ConnectionFailure, ServerSelectionTimeoutError) as e:
    print("Error: Could not connect to MongoDB.")
    print("\nDetailed error:", str(e))
    raise

# JWT secret key from environment variable or generate one
SECRET_KEY = os.getenv('JWT_SECRET_KEY', os.urandom(24))

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Root endpoint to serve the admin panel
@app.get("/")
async def read_root(request: Request):
    return FileResponse("admin.html")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# API endpoints
@app.post("/api/login")
async def login(request: Request):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    
    admin = db.admin.find_one({"username": username})
    if not admin or not bcrypt.checkpw(password.encode(), admin["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = jwt.encode(
        {"username": username, "exp": datetime.utcnow() + timedelta(days=1)},
        SECRET_KEY,
        algorithm="HS256"
    )
    
    return {"token": token}

# ... rest of your existing API endpoints ...

# Error handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 