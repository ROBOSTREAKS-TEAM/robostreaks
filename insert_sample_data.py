from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client.robostreaks

# Insert About Section
db.content.update_one(
    {"section": "about"},
    {"$set": {
        "content": "<p>It all began with a group of enthusiastic engineers who dreamt of creating and innovating something completely new.</p>"
    }},
    upsert=True
)

# Insert Wings (Left)
db.wings.insert_many([
    {
        "title": "Core Wing",
        "description": "Lorem ipsum dolor sit amet...",
        "icon": "fa-user-secret",
        "position": "left"
    },
    {
        "title": "Design & Animation Wing",
        "description": "Creates visually appealing and functional designs...",
        "icon": "fa-paint-brush",
        "position": "left"
    },
    {
        "title": "Mechanical Design Wing",
        "description": "Tasked with designing, building, and maintaining the physical structure...",
        "icon": "fa-wrench",
        "position": "left"
    }
])

# Insert Wings (Right)
db.wings.insert_many([
    {
        "title": "Programming Wing",
        "description": "Crafts precise software to direct robots...",
        "icon": "fa-code",
        "position": "right"
    },
    {
        "title": "Research & Innovation Wing",
        "description": "Pioneers advanced technologies...",
        "icon": "fa-lightbulb",
        "position": "right"
    },
    {
        "title": "Electronics Wing",
        "description": "Oversees the design, implementation...",
        "icon": "fa-bolt",
        "position": "right"
    }
])

# Insert Team Members
db.team.insert_many([
    {
        "name": "Dr. Chitta Ranjan Mohanty",
        "role": "Principal",
        "image": "/static/images/team/prof.-cr-mohanty.jpg",
        "order": 1
    },
    {
        "name": "Mr. Aditya Patra",
        "role": "Professor In Charge(PIC)",
        "image": "/static/images/team/aditya_patra.jpg",
        "order": 2
    },
    {
        "name": "Dr. Niranjan Panigrahi",
        "role": "Faculty Adviser",
        "image": "/static/images/team/niranjan_panigrahi.jpg",
        "order": 3
    }
])

# Insert Testimonials
db.testimonials.insert_many([
    {
        "quote": "Regardless of your intellect, true engineering lies in curiosity...",
        "author": "Aman Patro"
    },
    {
        "quote": "In the thrilling realms of engineering and robotics...",
        "author": "Ankit Pattnaik"
    },
    {
        "quote": "NOT JUST TECHNICAL KNOWLEDGE BUT TAUGHT US TEAM-BUILDING...",
        "author": "Prachi Pragnya Padhi"
    }
])

print("✅ Sample data inserted successfully.")