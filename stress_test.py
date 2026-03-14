import requests
import random
import time

API_URL = "http://127.0.0.1:8000/order/limit"
BASE_PRICE = 100

def place_random_order():
    side = random.choice(["buy" , "sell"])
    price = round(BASE_PRICE + random.uniform(2,-1) , 2)

    quantity = random.randint(1,10)

    payload = {
        "side": side,
        "price": price,
        "quantity": quantity
    }
    try:
        response = requests.post(API_URL , json = payload)
        if response.status_code ==200:
            data = response.json()
            if data.get("status") == "REJECTED":
                print(f" MARKET HALTED: {data.get('reason')}")
                return False
            else:
                print(f"{side.upper()} {quantity} @ {price}")
        else:
            print(f" Error: {response.status_code}")

    except Exception as e:
        print(f" Connection Failed: {e}") 


    return True

print(" Starting Market Simulator...")
while True:
    active = place_random_order()
    if not active:
        break
    time.sleep(0.1)                   