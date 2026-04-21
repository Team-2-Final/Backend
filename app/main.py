from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.api.router import router
from app.db.mongo import mongo_db
from app.db.oracle import engine
from app.db.oracle import get_oracle_db
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="SeedFarm-TEST-123")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite
        "http://localhost:3000",  # React 기본
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return {"message": "THIS IS APP.MAIN 9999"}


@app.get("/mongo-test")
async def mongo_test():
    collections = await mongo_db.list_collection_names()
    return {"collections": collections}


# @app.get("/oracle-test")
# def oracle_test():
#     with engine.connect() as connection:
#         result = connection.execute(text("SELECT 1 FROM dual"))
#         row = result.fetchone()
#     return {"oracle_result": row[0]}


# @app.get("/mongo-insert-test")
# async def mongo_insert_test():
#     result = await mongo_db.sensor_raw.insert_one({
#         "test": True,
#         "message": "mongo save success"
#     })
#     return {"inserted_id": str(result.inserted_id)}


@app.get("/debug/schema")
def schema_check(db: Session = Depends(get_oracle_db)):
    result = db.execute(text("""
    SELECT 
        sys_context('userenv','session_user') AS session_user,
        sys_context('userenv','current_schema') AS current_schema,
        sys_context('userenv','db_name') AS db_name
    FROM dual
    """)).mappings().first()

    return result

