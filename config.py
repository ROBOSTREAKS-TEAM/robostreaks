import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://<username>:<password>@cluster0.abcd.mongodb.net/robostreaks?retryWrites=true&w=majority")
SECRET_KEY = os.getenv("SECRET_KEY", 24)