from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Payment(BaseModel):
    amount: float


@app.post("/pay")
def pay(p: Payment):
    return {"status": "paid", "amount": p.amount}
