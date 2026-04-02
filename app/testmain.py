from fastapi import FastAPI
from app.api.data import router as data_router

app = FastAPI()

app.include_router(data_router)