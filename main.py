
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
import json
from bson import json_util
import pickle
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import uvicorn
from uuid import uuid4
from passlib.hash import bcrypt
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
import uvicorn
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


class WorkerData(BaseModel):
    name: str
    phoneNo: str
    Location: str
    password: str

class UserResponseModel(BaseModel):
    name: str
    phoneNo: str
    userType: str
    Location: str

def custom_user_response(user):
    return {
        "name": user.get("name"),
        "phoneNo": user.get("phoneNo"),
        "userType": user.get("userType"),
        "Location": user.get("Location")
    }



class BookingData(BaseModel):
    UID: str

def load_secrets():
    try:
        with open("secrets.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="secrets.json not found.")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error decoding secrets.json. Please check the file format.")

secrets = load_secrets()
client = AsyncIOMotorClient(secrets["mongodbKey"])
db = client.user

@app.post("/register/worker/")
async def register_worker(user_type: str, worker: WorkerData):
    collection = db.availableFarmworker 
    worker_data = worker.dict()
    worker_data['UID'] = str(uuid4())
    worker_data['logIntime'] = datetime.utcnow().isoformat()
    worker_data['userType'] = user_type
    worker_data['status'] = "available"
    worker_data['password'] = bcrypt.hash(worker.password)

    await collection.insert_one(worker_data)
    return {"message": f"{user_type.capitalize()} added successfully!", "UID": worker_data['UID']}

@app.post("/register/farmer/")
async def register_worker(user_type: str, worker: WorkerData):
    collection = db.availableFarmer
    worker_data = worker.dict()
    worker_data['UID'] = str(uuid4())
    worker_data['logIntime'] = datetime.utcnow().isoformat()
    worker_data['userType'] = user_type
    worker_data['status'] = "available"
    worker_data['password'] = bcrypt.hash(worker.password)

    await collection.insert_one(worker_data)
    return {"message": f"{user_type.capitalize()} added successfully!", "UID": worker_data['UID']}


@app.post("/login/")
async def login_user(phoneNo: str, password: str):
    user = await db.availableFarmworker.find_one({"phoneNo": phoneNo}) or await db.availableFarmer.find_one({"phoneNo": phoneNo})
    if user:
        # Check the password
        if bcrypt.verify(password, user['password']):
            # Convert MongoDB user document to JSON serializable format
            user_data = custom_user_response(user)
            return {"message": "Login successful", "user": user_data}
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    else:
        raise HTTPException(status_code=404, detail="User not found")


class PriceCalculatorInput(BaseModel):
    Working_Hours: int            # Number of working hours
    Crop_Type: str                # Type of crop, e.g., "Wheat"
    NoOfpeople : int

def get_dynamic_values():
    now = datetime.now()
    
    return {
        "Day_of_Week": now.weekday(),  
        "Month": now.month,
        "Base_Hourly_Wage": 12.00,  
        "Supply_Demand_Ratio": 1.2,  
        "Dynamic_Pricing_Multiplier": 1.44  
    }

@app.post("/price-calculator")
def price_calculator(input_data: PriceCalculatorInput):
    dynamic_values = get_dynamic_values()
    total_price = (dynamic_values["Base_Hourly_Wage"] * input_data.Working_Hours *
                   dynamic_values["Supply_Demand_Ratio"] * dynamic_values["Dynamic_Pricing_Multiplier"])

    return {
        "Crop_Type": input_data.Crop_Type,
        "Calculated_Price": total_price,
        "Day_of_Week": dynamic_values["Day_of_Week"],
        "Month": dynamic_values["Month"]
    }







class Worker(BaseModel):
   
    UID: str
    name: str
    phoneNo: str
    Location: str
    logIntime: str
    userType: str
    status: str

# Helper function to parse MongoDB results into Pydantic models
def worker_model_from_db(worker):
    worker_data = worker.copy()
    worker_data['_id'] = str(worker['_id'])
    return Worker(**worker_data)

@app.post("/allocate-workers/", response_model=list[Worker])
async def allocate_workers(num_workers: int):
    workers_collection = db.availableFarmworker
    # Find available workers and limit to the number requested
    available_workers_cursor = workers_collection.find({'status': 'available'}).limit(num_workers)
    allocated_workers = []

    async for worker in available_workers_cursor:
        # Attempt to update the worker status to 'allocated'
        result = await workers_collection.update_one(
            {'_id': worker['_id'], 'status': 'available'},  # Check status again to avoid race conditions
            {'$set': {'status': 'bussy'}}
        )
        if result.modified_count:
            worker['status'] = 'allocated'
            allocated_workers.append(worker_model_from_db(worker))

    # Check if any workers were allocated
    if not allocated_workers:
        raise HTTPException(status_code=404, detail="No available workers to allocate.")

    return allocated_workers



# change status
@app.post("/reset-workers-status/")
async def reset_workers_status():
    workers_collection = db.availableFarmworker
    # Update the status of all workers in the collection to 'available'
    result = await workers_collection.update_many(
        {},  # This empty query matches all documents
        {'$set': {'status': 'available'}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="No workers status were updated, possibly they were already 'available'.")

    return {"message": f"Successfully updated the status of {result.modified_count} workers to available."}









@app.post("/work/")
async def add_work(work: dict): 
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
async def add_booking(booking: dict): 
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
    try:
        collection = db.availableFarmworker
        farmworkers = await collection.find().to_list(length=None)
        # Remove '_id' field from each farmworker record
        for farmworker in farmworkers:
            farmworker.pop('_id', None)  # Remove '_id' if it exists
        return farmworkers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/news/")
async def get_news():
    collection = db.user.news
    news_items = await collection.find().sort('_id', -1).limit(8).to_list(length=None)
    return news_items

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)