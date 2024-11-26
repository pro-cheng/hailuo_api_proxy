from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from .database import SessionLocal
from . import models
from .models import UserProfile
from .hailuo_api import get_user_info
from pydantic import BaseModel
from typing import List, Optional
from .dependencies import get_current_user
from sqlalchemy import func

router = APIRouter()

# 创建数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class UserProfileCreate(BaseModel):
    token: str

def process_user_info(token: str, db: Session, current_user: models.SystemUser):
    try:
        res = get_user_info(token)
        print(res,"res")
    except Exception as e:        
        # 查找用户
        user_profile = db.query(UserProfile).filter(UserProfile.token == token).first()
        if user_profile:
            user_profile.is_online = 0
            db.commit()
            db.refresh(user_profile)
        raise HTTPException(status_code=400, detail="Token异常，获取用户信息失败")
            

    user_info = res.get('data', {}).get('userInfo', {})
    if not user_info:
        raise HTTPException(status_code=400, detail="Invalid user info in response")

    user_id = user_info.get('userID')
    name = user_info.get('name')
    avatar = user_info.get('avatarInfo').get('small')
    code = user_info.get('code')
    real_user_id = user_info.get('realUserID')
    is_new_user = user_info.get('isNewUser')

    # 查找用户
    user_profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    if not user_profile:
        # 如果用户不存在，创建一个新用户
        user_profile = UserProfile(
            u_id=current_user.id,
            user_id=user_id,
            token=token,
            name=name,
            avatar=avatar,
            code=code,
            is_online=1,
            real_user_id=real_user_id,
            is_new_user=is_new_user,
            updated_at=func.now()
        )
        db.add(user_profile)
    else:
        # 如果用户存在，更新信息
        user_profile.token = token
        user_profile.name = name
        user_profile.avatar = avatar
        user_profile.code = code
        user_profile.real_user_id = real_user_id
        user_profile.is_new_user = is_new_user
        user_profile.is_online = 1
        user_profile.updated_at = func.now()

    db.commit()
    db.refresh(user_profile)
    return user_profile

@router.post("/user_profiles/add_token")
def add_token(user_profile_data: UserProfileCreate, db: Session = Depends(get_db), current_user: models.SystemUser = Depends(get_current_user)):
    # 获取当前用户的token数量
    existing_tokens_count = db.query(models.UserProfile).filter(models.UserProfile.u_id == current_user.id).count()
    
    # 检查用户是否为VIP
    if current_user.is_vip != 1 and existing_tokens_count >= 1:
        raise HTTPException(status_code=403, detail="非VIP用户只能添加一个token")
    
    token = user_profile_data.token
    user_profile = process_user_info(token, db, current_user)
    return {"message": "Token added successfully", "user_profile": user_profile}

class UserProfileUpdate(BaseModel):
    user_id: str
    token: str
    concurrency_limit: Optional[int] = 3
    work_count: Optional[int] = 0
    


class UserProfileResponse(BaseModel):
    id: int
    user_id: str
    token: str
    class Config:
        orm_mode = True

@router.put("/user_profiles/update_token")
def update_token(user_profile_data: UserProfileUpdate, db: Session = Depends(get_db), current_user: models.SystemUser = Depends(get_current_user)):
    token = user_profile_data.token
    user_profile = process_user_info(token, db, current_user)
    
    # 仅在传入时更新 concurrency_limit
    if user_profile_data.concurrency_limit is not None:
        user_profile.concurrency_limit = user_profile_data.concurrency_limit
    
    # 仅在传入时更新 work_limit
    if user_profile_data.work_count is not None:
        user_profile.work_count = user_profile_data.work_count

    db.commit()
    db.refresh(user_profile)
    return {"message": "Token updated successfully", "user_profile": user_profile}

# 获取我的用户user_profiles列表list
@router.get("/user_profiles/my")
def get_my_user_profiles(
    db: Session = Depends(get_db), 
    current_user: models.SystemUser = Depends(get_current_user),
    limit: int = 10, 
    offset: int = 0
):
    # 获取总数
    total_count = db.query(UserProfile).filter(UserProfile.u_id == current_user.id).count()
    
    # 获取分页数据
    user_profiles = db.query(UserProfile).filter(UserProfile.u_id == current_user.id).offset(offset).limit(limit).all()
    
    return {
        "total_count": total_count,
        "data": user_profiles
    }

# 删除用户user_profiles列表里面的条目
@router.delete("/user_profiles/my/{id}")
def delete_my_user_profile(id: int, db: Session = Depends(get_db), current_user: models.SystemUser = Depends(get_current_user)):
    user_profile = db.query(UserProfile).filter(UserProfile.u_id == current_user.id, UserProfile.id == id).first()
    if not user_profile:
        raise HTTPException(status_code=404, detail="UserProfile not found")
    db.delete(user_profile)
    db.commit()
    return {"message": "UserProfile deleted successfully"}


