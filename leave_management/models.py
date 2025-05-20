from django.db import models
from django.conf import settings
import datetime

# Create your models here.

class MongoDBManager:
    @property
    def db(self):
        return settings.mongo_db

class LeaveApplication(MongoDBManager):
    @property
    def collection(self):
        return self.db.leave_applications
    
    def create(self, data):
        data['created_at'] = datetime.datetime.now()
        result = self.collection.insert_one(data)
        return str(result.inserted_id)
    
    def get_all(self):
        return list(self.collection.find())
    
    def get_by_id(self, id):
        from bson.objectid import ObjectId
        return self.collection.find_one({"_id": ObjectId(id)})
    
    def update_status(self, id, status):
        from bson.objectid import ObjectId
        return self.collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"status": status}}
        )
