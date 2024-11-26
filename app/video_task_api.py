from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import VideoTask, VideoTaskStatus
from pydantic import BaseModel
from typing import List
from . import models
from .user_profile_api import UserProfile
from fastapi import Query
from sqlalchemy import select
import uuid
import re
import base64
import os
import requests
from datetime import datetime
from typing import Optional
from .dependencies import get_current_user
import random
router = APIRouter()


# 创建数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class VideoTaskCreate(BaseModel):
    user_id: Optional[str] = None
    prompt: str = ''
    image_url: str = ''

def save_image_to_local(image_url: str):
    # 如果image_url为空，返回空路径
    if not image_url:
        return ""
    # 判断image_url是否为base64格式
    if image_url.startswith('data:image'):
        # 是base64格式的图片
        image_data = re.sub('^data:image/.+;base64,', '', image_url)
        image_bytes = base64.b64decode(image_data)
    else:
        # 是网络链接，下载图片
        response = requests.get(image_url)
        if response.status_code == 200:
            image_bytes = response.content
        else:
            raise HTTPException(status_code=400, detail="Failed to download image from URL")

    # 生成唯一文件名
    filename = f"{uuid.uuid4()}.png"
    # 获取当前日期
    date_str = datetime.now().strftime('%Y-%m-%d')
    # 确保存储目录存在，增加日期层级
    os.makedirs(f'images/{date_str}', exist_ok=True)
    # 保存图片到本地
    image_path = os.path.join('images', date_str, filename)
    with open(image_path, 'wb') as f:
        f.write(image_bytes)

    return image_path


@router.post("/video_tasks_create" )
def create_video_task(video_task: VideoTaskCreate, db: Session = Depends(get_db), current_user: models.SystemUser = Depends(get_current_user)):
    
    image_path = save_image_to_local(video_task.image_url)
    user_id = video_task.user_id
    pix_user_profile = None
    user_profiles = db.query(UserProfile).filter(UserProfile.u_id == current_user.id).all()
    if len(user_profiles) == 0:
        raise HTTPException(status_code=400, detail="用户不存在")
    if user_id:
        for user_profile in user_profiles:
            if user_profile.user_id == user_id:
                pix_user_profile = user_profile
                break
    if not pix_user_profile:
        # 随机选择一个用户
        pix_user_profile = random.choice(user_profiles)

    db_video_task = VideoTask(
        user_id=pix_user_profile.user_id,
        u_id=current_user.id,
        prompt=video_task.prompt,
        image_url=image_path,
        video_id="",  # 默认值
        coverURL="",  # 默认值
        videoURL="",  # 默认值
        status=VideoTaskStatus.QUEUE,
        canRetry=0,  # 默认值
        width=1920,  # 默认值
        height=1080,  # 默认值
        originFiles="[]",  # 默认值
        canAppeal=0,  # 默认值
        downloadURL=""  # 默认值
    )
    db_video_task.created_at = datetime.now()
    db.add(db_video_task)
    db.commit()
    db.refresh(db_video_task)
    return db_video_task


@router.get("/video_tasks_list")
def get_video_tasks(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1), db: Session = Depends(get_db), current_user: models.SystemUser = Depends(get_current_user)):
    """
    分页查询 video_tasks
    :param skip: 跳过的记录数
    :param limit: 返回的记录数
    :param db: 数据库会话
    :return: video_tasks 列表和总记录数
    """
    u_id = current_user.id
    # 计算总记录数
    total_count = db.query(VideoTask).filter(VideoTask.u_id == u_id).count()
    # 创建时间倒序
    video_tasks = db.execute(select(VideoTask).filter(VideoTask.u_id == u_id).order_by(VideoTask.created_at.desc()).offset(skip).limit(limit)).scalars().all()
    return {"total_count": total_count, "video_tasks": video_tasks}



@router.get("/recommend_video_tasks")
def get_recommend_video_tasks(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1), db: Session = Depends(get_db) ):
    # 创建时间倒序
    video_tasks = db.execute(select(VideoTask).filter(VideoTask.u_id == 1 , VideoTask.status == VideoTaskStatus.SUCCESS).order_by(VideoTask.created_at.desc()).offset(skip).limit(limit)).scalars().all()
    return video_tasks


@router.get("/video_task/{task_id}")
def get_video_task_by_task_id(task_id: str, db: Session = Depends(get_db), current_user: models.SystemUser = Depends(get_current_user)):
    """
    根据视频ID查询单个视频任务的详细信息
    :param task_id: 视频的唯一标识符
    :param db: 数据库会话
    :return: 单个视频任务的详细信息
    """
    try:
        # 将字符串转换为UUID对象
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID format")

    video_task = db.query(VideoTask).filter(VideoTask.id == task_uuid).first()
    if video_task is None:
        raise HTTPException(status_code=404, detail="Video task not found")
    return video_task