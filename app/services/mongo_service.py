from app.db.mongo import mongo_db


class MongoService:

    async def save_ai_detail(self, data: dict):
        collection = mongo_db["ai_result_detail"]
        await collection.insert_one(data)