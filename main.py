from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from uuid import uuid4
from bson import json_util
from passlib.hash import bcrypt
from fastapi.middleware.cors import CORSMiddleware
import json
import requests
from bson import ObjectId

app = FastAPI()

# Applying CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Load database secrets and initialize database client
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

# Define Pydantic models for request validation
class WorkerData(BaseModel):
    name: str
    phoneNo: str
    location: str
    password: str

class UserResponseModel(BaseModel):
    name: str
    phoneNo: str
    userType: str
    location: str

@app.get("/")
def read_root():
    return {"Hello": "World"}

# Register Worker Endpoint
@app.post("/register/worker/")
async def register_worker(worker: WorkerData):
    collection = db.availableFarmworker
    worker_data = worker.dict()
    worker_data.update({
        'UID': str(uuid4()),
        'logIntime': datetime.utcnow().isoformat(),
        'userType': "worker",
        'status': "available",
        'password': bcrypt.hash(worker.password),
        'paymentHistory': [0, 0],
        'currentPayment': 0
    })
    await collection.insert_one(worker_data)
    return {"message": "Worker added successfully!", "UID": worker_data['UID']}
@app.post("/register/farmer/")
async def register_worker(worker: WorkerData):
    collection = db.availableFarmer
    worker_data = worker.dict()
    worker_data['UID'] = str(uuid4())
    worker_data['logIntime'] = datetime.utcnow().isoformat()
    worker_data['userType'] = "farmer"
    worker_data['status'] = "available"
    worker_data['password'] = bcrypt.hash(worker.password)

    await collection.insert_one(worker_data)
    return {"message": f"farmer added successfully!", "UID": worker_data['UID']}


# Login Endpoint
@app.post("/login/")
async def login_user(phoneNo: str, password: str):
    user = await db.availableFarmworker.find_one({"phoneNo": phoneNo}) or await db.availableFarmer.find_one({"phoneNo": phoneNo})
    if user and bcrypt.verify(password, user['password']):
        user_data = {
            "name": user["name"],
            "phoneNo": user["phoneNo"],
            "userType": user["userType"],
            "Location": user["location"]
        }
        return {"message": "Login successful", "user": user_data}
    else:
        raise HTTPException(status_code=404, detail="Invalid credentials or user not found")

# Remaining endpoints would be similarly updated and refactored
class PriceCalculatorInput(BaseModel):
    Working_Hours: int            # Number of working hours
    Crop_Type: str                # Type of crop, e.g., "Wheat"
    NoOfpeople : int


@app.post("/price-calculator")
def price_calculator(input_data: PriceCalculatorInput):
    # dynamic_values = get_dynamic_values()
    # total_price = (dynamic_values["Base_Hourly_Wage"] * input_data.Working_Hours *
    #                dynamic_values["Supply_Demand_Ratio"] * dynamic_values["Dynamic_Pricing_Multiplier"])
    url = "https://supreme-happiness-jprvq94x65x3jqj6-8000.app.github.dev/price-calculator/"
    payload = json.dumps({
    "Working_Hours": input_data.Working_Hours,
    "Crop_Type": input_data.Crop_Type,
    "Count": input_data.NoOfpeople
    })

    headers = {
    'accept': 'application/json',
    'Content-Type': 'application/json',
    'Cookie': '.Tunnels.Relay.WebForwarding.Cookies=CfDJ8E0FHi1JCVNKrny-ARCYWxOcQXqDwS8Zf7ybXpfEabuVYz6b59lRegfoQoIMkOdzqK1V1lwRrHmOYwuYJ0mA0Y_4sFofgXuZV27BX3KYO6el-IuSEL5OEEXqYtuxHcST5jgyD4t97FDOhkXWsrPYoKfJ7KeT5FFbx_bl8Bo0cdemyfvBRzrf7QW08t-DXEi49k1o__qaFXCG0rrxrQytvBnYEnMMfY1aNAjPQgd0UJ0yeDCtyWh3BHtQ_r0bqJsJKHaDjjgFLIbnDRJhLLH7sbnaRYMFYkBzFgE7DxN2OTTuo8j9k5TqjNImg3d1-QvkO_F9Fco7iNw3y2Rld8vGO43g1aokNUaT8E8njHNl-rl_wWse83jIsQGsHDV39H_B2sxkCMxJMGxTOWrukFpGGuMz1EWTYR64GHgPCUOvXLEH-nT4mrdOY-9oKK_k1dXBpm5KC081mwrZZT7n5CHYT8OmtDWkzsb_hd7psHbHYZRXGWACc7f0UQAy0na_koEWX4E59GXj1VNS5bs0aolog_0fd-37f3xXiCxdOhcG4diXvPq51y_yR8F6ars_3cJVGUBRJf-KG19bz0tshfo7ep-JOBWE9KR4EYTxdIKiTImuczsSlAVdWf22rK_wDg34jnI3kdLLeqWbsMPMLGrjKVzTEF-iFTQB0VoFpRoPHQuJ35h_HMw6mWoZenbePXFxsdlbIf6oEpFCiSLsIAM4OQbbDNArNp4faEB3ckDBb_bBN13k0puF4R8HAt5WohEMtOyVv-zZq1ywDX_CXBWUrA_1EkOoN1ytUCi27vQwcnMVRI7lpYWvDgT4peLf8q0OIL6kl6OCAMlIeHIM2ScoJ91LGECfeADRwW--Td9XBYzoaTzowKSnIeApdtC4Yp5RHZqQnXxx4Se9QebsvWQi1gmgoZbzK2_8qKbZtgd8AOGqP2IGKRwmtwjXx76ClYhLIYvBmDQKqD6xjlEHfqFPouLXPmwnkjEr3RJsolN__zucc4dr22dbQJe4gEa1PYm1_A'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    price=response.json()['Total_Calculated_Price']
    print(input_data.NoOfpeople)
    print(price)
    return {
        "Crop_Type": input_data.Crop_Type,
        "Calculated_Price": int(price)
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
async def allocate_workers(num_workers: int,fixed_price: int):
    pricePP=fixed_price/num_workers
    print(int(pricePP))
    workers_collection = db.availableFarmworker
    # Find available workers and limit to the number requested
    available_workers_cursor = workers_collection.find({'status': 'available'}).limit(num_workers)
    allocated_workers = []

    async for worker in available_workers_cursor:
        # Attempt to update the worker status to 'allocated'
        result = await workers_collection.update_one(
            {'_id': worker['_id'], 'status': 'available'},  # Check status again to avoid race conditions
            {'$set': {'status': 'busy', 'currentPayment': int(pricePP)}},

        )
        if result.modified_count:
            worker['status'] = 'allocated'
            allocated_workers.append(worker_model_from_db(worker))

    # Check if any workers were allocated
    if not allocated_workers:
        raise HTTPException(status_code=404, detail="No available workers to allocate.")

    return allocated_workers


@app.post("/reset-workers-status/")
async def reset_workers_status():
    workers_collection = db.availableFarmworker
    try:
        # Attempt to update the status of all workers
        result = await workers_collection.update_many(
            {},  # This empty query matches all documents
            {
                '$set': {
                    'status': 'available',
                    'currentPayment': 0,
                    'paymentHistory': [0, 0]
                }
            }
        )
        
        # Check if any documents were actually updated
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="No workers' statuses were updated, possibly they were already 'available'.")

        # Successful update response
        return {"message": f"Successfully updated the status of {result.modified_count} workers to available."}

    except Exception as e:
        # Catch and log unexpected exceptions
        print(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while updating workers' statuses.")

@app.get("/worker-payment/")
async def get_worker_payment(UID: str, name: str):
    workers_collection = db.availableFarmworker
    """
    Fetches the current payment of a worker based on UID and name if the worker's status is 'busy'.
    """
    worker = await workers_collection.find_one({"UID": UID, "name": name})
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found.")

    if worker['status'] != 'busy':
        raise HTTPException(status_code=400, detail="Worker is not currently busy.")

    return {
        "UID": UID,
        "Name": name,
        "CurrentPayment": worker['currentPayment']
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


