# main.py

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Hello"}

from vico.database import get_db

@app.get("/db-test")
def db_test(db: Session = Depends(get_db)):
    return {
        "connected": db.is_active
    }