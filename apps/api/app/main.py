from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .routers import wallet, agents, chain_data, bridge, starknet, routing, system

# Create DB Tables
Base.metadata.create_all(bind=engine)

# Fix path to allow importing from applications
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from applications.capp.capp.core.redis import init_redis
from applications.capp.capp.core.aptos import init_aptos_client
from applications.capp.capp.core.polygon import init_polygon_client

app = FastAPI(
    title="CAPP Wallet API",
    description="Backend API for the CAPP Smart Treasury Wallet",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    # Initialize Redis (mock or real)
    try:
        await init_redis()
    except Exception as e:
        print(f"Warning: Redis unavailable ({e}). Agents might fail if they rely on cache.")
    
    # Initialize Clients
    await init_aptos_client()
    await init_polygon_client()

    # Start Chain Listener (Background)
    from applications.capp.capp.services.chain_listener import ChainListenerService
    import asyncio
    listener = ChainListenerService()
    asyncio.create_task(listener.start_listening())
    print("Chain Listener Background Task Started")

# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(wallet.router)
app.include_router(agents.router)
app.include_router(chain_data.router)
app.include_router(bridge.router)
app.include_router(starknet.router)
app.include_router(routing.router)
app.include_router(system.router)
from .routers import admin_dlq
app.include_router(admin_dlq.router)

@app.get("/")
async def root():
    return {"message": "Welcome to CAPP Wallet API. System Online."}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
