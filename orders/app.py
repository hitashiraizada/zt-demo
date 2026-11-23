import os

import httpx
from fastapi import FastAPI

PAYMENTS_URL = os.environ["PAYMENTS_URL"]

app = FastAPI()
client = httpx.Client()


@app.post("/order")
def order():
    r = client.post(f"{PAYMENTS_URL}/pay", json={"amount": 42})
    r.raise_for_status()
    return r.json()
