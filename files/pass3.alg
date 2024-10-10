
from fastapi import FastAPI, HTTPException, Depends
from passlib.context import CryptContext
from pydantic import BaseModel

app = FastAPI()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory store for this example
users_db = {}

class User(BaseModel):
    username: str
    password: str

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

@app.post("/register")
def register(user: User):
    hashed_password = hash_password(user.password)
    users_db[user.username] = hashed_password
    return {"message": "User registered successfully"}

@app.post("/login")
def login(user: User):
    stored_password_hash = users_db.get(user.username)
    if not stored_password_hash or not verify_password(user.password, stored_password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"message": "Login successful"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
