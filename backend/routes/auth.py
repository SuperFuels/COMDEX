from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from models import User  # Assuming your User model is imported here
from database import get_db  # Assuming you have a function to get a DB session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer  # Added import
from typing import Optional

# Settings for JWT
SECRET_KEY = "your_secret_key"  # Make sure to replace this with a secure secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # You can adjust the expiration time

# Create a password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Initialize the FastAPI router
router = APIRouter()

# Define oauth2_scheme to extract token from the Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Helper function to verify password
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Helper function to hash passwords
def get_password_hash(password):
    return pwd_context.hash(password)

# Helper function to create a JWT token
def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Register user route
@router.post("/register")
def register_user(name: str, email: str, password: str, db: Session = Depends(get_db)):
    # Check if the user already exists
    db_user = db.query(User).filter(User.email == email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create a new user
    hashed_password = get_password_hash(password)
    new_user = User(name=name, email=email, password_hash=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"msg": "User created successfully", "user": new_user}

# Login route
@router.post("/login")
def login_user(email: str, password: str, db: Session = Depends(get_db)):
    # Find user by email
    db_user = db.query(User).filter(User.email == email).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # Verify password
    if not verify_password(password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    # Create a JWT token
    access_token = create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# Dependency for getting the current user from the token
def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return email
    except JWTError:
        raise credentials_exception

