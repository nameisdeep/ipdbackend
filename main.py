from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
import json
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


# Define data models using Pydantic for input validation
class WorkerData(BaseModel):
    name: str
    userType: str
    phoneNo: str
    Location: str
    logIntime: str
    UID: str

class BookingData(BaseModel):
    UID: str

# Placeholder for secrets loading
def load_secrets():
    try:
        with open("secrets.json", "r") as file:
            secrets = json.load(file)
            return secrets
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="secrets.json not found.")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error decoding secrets.json. Please check the file format.")

secrets = load_secrets()

# Database Client Setup
client = AsyncIOMotorClient(secrets["mongodbKey"])
db = client.user  # Adjust database access according to your MongoDB setup



@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.post("/workers/")
async def add_worker(worker: WorkerData):
    collection = db.availableFarmworker
    await collection.insert_one(worker.dict())
    return {"message": "Worker added successfully! thanks"}

@app.post("/work/")
async def add_work(work: dict):  # Define the data model appropriately
    collection = db.work.available
    await collection.insert_one(work)
    return {"message": "Work added successfully!"}

@app.post("/allocate_work/")
async def allocate_work(work: BookingData):
    available_col = db.work.available
    allocated_col = db.work.allocated
    doc_to_move = await available_col.find_one({"UID": work.UID})
    if doc_to_move:
        await allocated_col.insert_one(doc_to_move)
        await available_col.delete_one({"UID": work.UID})
        return {"message": "Work allocated successfully!"}
    else:
        raise HTTPException(status_code=404, detail="Work not found or already allocated.")

@app.post("/bookings/")
async def add_booking(booking: dict):  # Define the data model appropriately
    collection = db.bookings[booking['UID']]
    await collection.insert_one(booking)
    return {"message": "Booking added successfully!"}

@app.get("/bookings/{UID}")
async def get_all_bookings(UID: str):
    collection = db.bookings[UID]
    bookings = await collection.find().to_list(length=None)
    return bookings

@app.get("/farmworkers/")
async def get_all_farmworkers():
    collection = db.user.availableFarmworker
    farmworkers = await collection.find().to_list(length=None)
    return farmworkers

@app.get("/news/")
async def get_news():
    collection = db.user.news
    news_items = await collection.find().sort('_id', -1).limit(8).to_list(length=None)
    return news_items

