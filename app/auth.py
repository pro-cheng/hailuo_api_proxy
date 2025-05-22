import jwt
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from passlib.context import CryptContext
from .database import SessionLocal
from . import models
from .dependencies import get_current_user
from typing import Optional
from fastapi.security import OAuth2PasswordRequestForm


# 创建数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 创建一个新的路由器
auth_router = APIRouter()

# JWT 配置
SECRET_KEY = "fyshark"  # 请使用更安全的密钥
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30*2*24*30*12

# Pydantic 模型用于请求体
class UserCreate(BaseModel):
    username: str
    password: str
    email: str
    

class UserLogin(BaseModel):
    username: str
    password: str

# 新的 Pydantic 模型用于用户信息
class UserInfo(BaseModel):
    id: int
    username: str
    email: str
    phone: Optional[str] = None  # 将 phone 字段设为可选
    is_active: int
    is_superuser: int
    is_vip: int
    created_at: datetime
    updated_at: datetime
    

# 生成 JWT token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 注册户
@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.SystemUser).filter(models.SystemUser.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    
    hashed_password = pwd_context.hash(user.password)
    db_user = models.SystemUser(
        username=user.username,
        hashed_password=hashed_password,
        email=user.email,
        phone='',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_vip=0
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User registered successfully"}

# 用户登录
@auth_router.post("/login")
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.SystemUser).filter(models.SystemUser.username == user.username).first()
    if not db_user or not pwd_context.verify(user.password, db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@auth_router.post("/token")
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = db.query(models.SystemUser).filter(models.SystemUser.username == form_data.username).first()
    if not db_user or not pwd_context.verify(form_data.password, db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@auth_router.get("/user/me", response_model=UserInfo)
def read_users_me(current_user: models.SystemUser = Depends(get_current_user)):
    return UserInfo(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        phone=current_user.phone,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        is_vip=current_user.is_vip,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at or datetime.utcnow()
    )

