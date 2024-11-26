from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from ..database import SessionLocal
from .. import models
from ..models import KlingImageTaskType,KlingVideoTask,VideoTaskStatus
from pydantic import BaseModel
from typing import List, Optional
from ..auth import get_current_user
from sqlalchemy import func
from .kling_api import BaseGen,ImageGen,VideoGen
from ..video_task_api import save_image_to_local
import random
import json
import uuid
router = APIRouter()

# 创建数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class KlingUserProfileCreate(BaseModel):
    cookie: Optional[str] = None

class KlingUserProfileUpdate(BaseModel):
    cookie: Optional[str] = None
    concurrency_limit: Optional[int] = 3
    work_count: Optional[int] = 0

@router.post("/kling_user_profiles/add")
def add_kling_user_profile(kling_user_profile_data: KlingUserProfileCreate, db: Session = Depends(get_db), current_user: models.SystemUser = Depends(get_current_user)):

    # 获取当前用户的token数量
    existing_tokens_count = db.query(models.KlingUserProfile).filter(models.KlingUserProfile.u_id == current_user.id).count()
    # 检查用户是否为VIP
    if current_user.is_vip != 1 and existing_tokens_count >= 1:
        raise HTTPException(status_code=403, detail="非VIP用户只能添加一个token")
    
   
    try:
        bg = BaseGen(kling_user_profile_data.cookie)
        
        info = bg.get_account_info()
        if info['data'] is not None:
            user_id = info['data']['userId']
            user_name = info['data']['userName']
            avatar = info['data']['userAvatar'][0]
            
            #先查找是否存在
            existing_kling_user_profile = db.query(models.KlingUserProfile).filter(models.KlingUserProfile.u_id == current_user.id, models.KlingUserProfile.user_id == user_id).first()
            if existing_kling_user_profile is None:
                existing_kling_user_profile = models.KlingUserProfile(
                    u_id=current_user.id,
                    cookie=kling_user_profile_data.cookie,
                    concurrency_limit=3,
                    work_count=0,
                    created_at=func.now(),
                    updated_at=func.now()
                )
                
            
            existing_kling_user_profile.user_id = user_id
            existing_kling_user_profile.user_name = user_name
            existing_kling_user_profile.avatar = avatar
            
        else:
            raise HTTPException(status_code=400, detail="Failed to get account info")
        
        point = bg.get_account_point()
        existing_kling_user_profile.point = point
        db.add(existing_kling_user_profile)
        db.commit()
        db.refresh(existing_kling_user_profile)    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error during account info retrieval: {str(e)}")
    
    return {"message": "KlingUserProfile added successfully", "kling_user_profile": existing_kling_user_profile}

@router.put("/kling_user_profiles/update/{id}")
def update_kling_user_profile(id: int, kling_user_profile_data: KlingUserProfileUpdate, db: Session = Depends(get_db), current_user: models.SystemUser = Depends(get_current_user)):
    kling_user_profile = db.query(models.KlingUserProfile).filter(models.KlingUserProfile.u_id == current_user.id, models.KlingUserProfile.id == id).first()
    if not kling_user_profile:
        raise HTTPException(status_code=404, detail="KlingUserProfile not found")
    
    if kling_user_profile_data.cookie :
        kling_user_profile.cookie = kling_user_profile_data.cookie
    else:
        raise HTTPException(status_code=400, detail="Cookie is required")
    
    if kling_user_profile_data.concurrency_limit is not None:
        kling_user_profile.concurrency_limit = kling_user_profile_data.concurrency_limit
    if kling_user_profile_data.work_count is not None:
        kling_user_profile.work_count = kling_user_profile_data.work_count

    try:
        bg = BaseGen(kling_user_profile.cookie)
        info = bg.get_account_info()
        if info['data'] is not None:
            kling_user_profile.user_id = info['data']['userId']
            kling_user_profile.user_name = info['data']['userName']
            kling_user_profile.avatar = info['data']['userAvatar'][0]
        
        point = bg.get_account_point()
        kling_user_profile.point = point
        
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error during account info retrieval: {str(e)}")
    
    db.commit()
    db.refresh(kling_user_profile)
    return {"message": "KlingUserProfile updated successfully", "kling_user_profile": kling_user_profile}

@router.delete("/kling_user_profiles/delete/{id}")
def delete_kling_user_profile(id: int, db: Session = Depends(get_db), current_user: models.SystemUser = Depends(get_current_user)):
    kling_user_profile = db.query(models.KlingUserProfile).filter(models.KlingUserProfile.u_id == current_user.id, models.KlingUserProfile.id == id).first()
    if not kling_user_profile:
        raise HTTPException(status_code=404, detail="KlingUserProfile not found")
    db.delete(kling_user_profile)
    db.commit()
    return {"message": "KlingUserProfile deleted successfully"}

@router.get("/kling_user_profiles/my")
def get_my_kling_user_profiles(
    db: Session = Depends(get_db), 
    current_user: models.SystemUser = Depends(get_current_user),
    limit: int = 10, 
    offset: int = 0
):
    total_count = db.query(models.KlingUserProfile).filter(models.KlingUserProfile.u_id == current_user.id).count()
    kling_user_profiles = db.query(models.KlingUserProfile).filter(models.KlingUserProfile.u_id == current_user.id).offset(offset).limit(limit).all()
    
    return {
        "total_count": total_count,
        "data": kling_user_profiles
    }

class KlingImageTaskCreate(BaseModel):
    prompt: str
    image_url: str = ""
    aspect_ratio: str = "1:1"
    count: int = 1
    
@router.post("/kling_image_tasks/add")    
def add_kling_image_task(kling_image_task_data: KlingImageTaskCreate, db: Session = Depends(get_db), current_user: models.SystemUser = Depends(get_current_user)):
    kling_user_profiles = db.query(models.KlingUserProfile).filter(models.KlingUserProfile.u_id == current_user.id).all()
    if not kling_user_profiles:
        raise HTTPException(status_code=404, detail="KlingUserProfile not found")
    
    kling_user_profile = random.choice(kling_user_profiles)
    
    image_path = save_image_to_local(kling_image_task_data.image_url)
    
    kling_image_task = KlingVideoTask(
        u_id=current_user.id,
        user_id=kling_user_profile.user_id,
        created_at=func.now(),
        updated_at=func.now(),
        status=VideoTaskStatus.QUEUE,
    )
    if image_path:
        kling_image_task.task_type = KlingImageTaskType.image2image
        data = {
            "image": image_path,
            "prompt": kling_image_task_data.prompt,
            "aspect_ratio": kling_image_task_data.aspect_ratio,
            "count": kling_image_task_data.count
        }
        kling_image_task.inputs = json.dumps(data)
    else:
        kling_image_task.task_type = KlingImageTaskType.text2image
        data = {
            "prompt": kling_image_task_data.prompt,
            "count": kling_image_task_data.count,
            "aspect_ratio": kling_image_task_data.aspect_ratio
        }
        kling_image_task.inputs = json.dumps(data)
    
    db.add(kling_image_task)
    db.commit()
    db.refresh(kling_image_task)
    return {"message": "KlingImageTask added successfully", "kling_image_task": kling_image_task}



class KlingVideoTaskCreate(KlingImageTaskCreate):
    tail_image_url: str = ""
    model_name: str = "1.0"
    is_high_quality: bool = False

@router.post("/kling_video_tasks/add")
def add_kling_video_task(kling_video_task_data: KlingVideoTaskCreate, db: Session = Depends(get_db), current_user: models.SystemUser = Depends(get_current_user)):
    kling_user_profiles = db.query(models.KlingUserProfile).filter(models.KlingUserProfile.u_id == current_user.id).all()
    if not kling_user_profiles:
        raise HTTPException(status_code=404, detail="KlingUserProfile not found")
    
    kling_user_profile = random.choice(kling_user_profiles)
    kling_video_task = KlingVideoTask(
        u_id=current_user.id,
        user_id=kling_user_profile.user_id,
        created_at=func.now(),
        updated_at=func.now(),
        status=VideoTaskStatus.QUEUE,
    )
    image_path = save_image_to_local(kling_video_task_data.image_url)
    if image_path:
        kling_video_task.task_type = KlingImageTaskType.image2video
        data = {
            "image": image_path,
            "prompt": kling_video_task_data.prompt,
            "aspect_ratio": kling_video_task_data.aspect_ratio,
            "count": kling_video_task_data.count,
            "model_name": kling_video_task_data.model_name,
            "is_high_quality": kling_video_task_data.is_high_quality
        }
        if kling_video_task_data.tail_image_url:
            kling_video_task.task_type = KlingImageTaskType.image2image_tail
            tail_image_path = save_image_to_local(kling_video_task_data.tail_image_url)
            data["tail_image"] = tail_image_path
        kling_video_task.inputs = json.dumps(data)
    else:
        kling_video_task.task_type = KlingImageTaskType.text2video
        data = {
            "prompt": kling_video_task_data.prompt,
            "count": kling_video_task_data.count,
            "aspect_ratio": kling_video_task_data.aspect_ratio,
            "model_name": kling_video_task_data.model_name,
            "is_high_quality": kling_video_task_data.is_high_quality
        }
        kling_video_task.inputs = json.dumps(data)
    
    db.add(kling_video_task)
    db.commit()
    db.refresh(kling_video_task)
    return {"message": "KlingVideoTask added successfully", "kling_video_task": kling_video_task}
    

@router.get("/kling_tasks/list")
def get_kling_task_list(skip: int = 0, limit: int = 10, db: Session = Depends(get_db), current_user: models.SystemUser = Depends(get_current_user)):
    kling_user_profiles = db.query(models.KlingUserProfile).filter(models.KlingUserProfile.u_id == current_user.id).all()
    if not kling_user_profiles:
        raise HTTPException(status_code=404, detail="KlingUserProfile not found")
    
    tasks = db.query(models.KlingVideoTask).filter(models.KlingVideoTask.u_id == current_user.id).order_by(models.KlingVideoTask.created_at.desc()).offset(skip).limit(limit).all()
    return tasks

@router.get("/kling_tasks/detail/{id}")
def get_kling_task_detail(id: str, db: Session = Depends(get_db), current_user: models.SystemUser = Depends(get_current_user)):
    try:
        task_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID format")
    task = db.query(models.KlingVideoTask).filter(models.KlingVideoTask.u_id == current_user.id, models.KlingVideoTask.id == task_uuid).first()
    if not task:
        raise HTTPException(status_code=404, detail="KlingVideoTask not found")
    return task