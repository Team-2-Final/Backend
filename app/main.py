from fastapi import FastAPI
from sqlalchemy import text

from app.api.router import router
from app.api.auth import router as auth_router
from app.db.mongo import mongo_db
from app.db.oracle import engine

app = FastAPI(title="SeedFarm-TEST-123")

app.include_router(router, prefix="/api")
app.include_router(auth_router)


@app.get("/")
def root():
    return {"message": "THIS IS APP.MAIN 9999"}


@app.get("/mongo-test")
async def mongo_test():
    collections = await mongo_db.list_collection_names()
    return {"collections": collections}


@app.get("/oracle-test")
def oracle_test():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1 FROM dual"))
        row = result.fetchone()
    return {"oracle_result": row[0]}


@app.get("/mongo-insert-test")
async def mongo_insert_test():
    result = await mongo_db.sensor_raw.insert_one({
        "test": True,
        "message": "mongo save success"
    })
    return {"inserted_id": str(result.inserted_id)}