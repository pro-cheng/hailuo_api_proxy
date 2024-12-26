from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from .models import VideoTask, VideoTaskStatus, UserProfile
from .database import SessionLocal
from .hailuo_api import gen_video
import traceback

def add_new_task():
    db: Session = SessionLocal()
    # 获取所有用户信息
    user_profiles = db.query(UserProfile).all()
    for user_profile in user_profiles:
        user_profile: UserProfile = user_profile
        
        # 查询VideoTask 的任务，超过3个小时的就设置失败
        tasks = db.query(VideoTask).filter(
            VideoTask.user_id == user_profile.user_id,
            VideoTask.status.in_([VideoTaskStatus.CREATE, VideoTaskStatus.HL_QUEUE, VideoTaskStatus.PROGRESS]),
            VideoTask.created_at < datetime.now() - timedelta(hours=3)
        ).all()
        for task in tasks:
            task.status = VideoTaskStatus.FAILED
            task.failed_msg = "任务超时"
            db.commit()
        
        # 更新用户的工作计数
        work_count = db.query(VideoTask).filter(
            VideoTask.user_id == user_profile.user_id,
            VideoTask.status.in_([
                VideoTaskStatus.CREATE,
                VideoTaskStatus.HL_QUEUE,
                VideoTaskStatus.PROGRESS
            ])
        ).count()
        user_profile.work_count = work_count
        db.commit()
        db.refresh(user_profile)
        
        if user_profile.work_count >= user_profile.concurrency_limit:
            # 如果用户的工作数量达到了并发限制，则跳过该用户
            continue
        
        # 获取该用户的任务队列
        limit = user_profile.concurrency_limit - user_profile.work_count
        if limit < 1:
            limit = 1
        task_queue = db.query(VideoTask).filter(VideoTask.user_id == user_profile.user_id, VideoTask.status == VideoTaskStatus.QUEUE).limit(limit).all()
        
        for task in task_queue:
            task: VideoTask = task
            try:
                if user_profile.is_online == 0:
                    print("User is offline, skipping task.")
                    task.status = VideoTaskStatus.FAILED
                    task.failed_msg = "用户不在线"
                    db.commit()
                    continue
                
                print(f"Selected User ID: {user_profile.id}, Token: {user_profile.token}, Work Count: {user_profile.work_count}")
                res = gen_video(user_profile.token, task.prompt, task.image_url, task.model_id)
                task.video_id = res["data"]["id"]
                task.status = VideoTaskStatus.CREATE
                user_profile.work_count += 1
                db.commit()
                db.refresh(task)
                db.refresh(user_profile)
            except Exception as e:
                task.add_failed_count += 1
                if task.add_failed_count > 3:
                    task.status = VideoTaskStatus.FAILED
                task.failed_msg = str(e)
                db.commit()
                print("gen video error", task.id, e)
                print(traceback.format_exc())
                continue
    db.close()