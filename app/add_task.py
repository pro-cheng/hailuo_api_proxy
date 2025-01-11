from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from .models import VideoTask, VideoTaskStatus, UserProfile
from .database import SessionLocal
from .hailuo_api import gen_video
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import List
from sqlalchemy.orm import scoped_session, sessionmaker
import threading

def process_single_user(user_profile: UserProfile, db_factory):
    """处理单个用户的任务"""
    thread_name = threading.current_thread().name
    print(f"Thread {thread_name} processing user {user_profile.user_id}")
    db = db_factory()
    try:
        # 重新获取用户信息
        user_profile = db.merge(user_profile)
        
        # 处理超时任务
        tasks = db.query(VideoTask).filter(
            VideoTask.user_id == user_profile.user_id,
            VideoTask.status.in_([VideoTaskStatus.CREATE, VideoTaskStatus.HL_QUEUE, VideoTaskStatus.PROGRESS]),
            VideoTask.created_at < datetime.now() - timedelta(hours=1)
        ).all()
        for task in tasks:
            task.status = VideoTaskStatus.FAILED
            task.failed_msg = "System busy. Please try again tomorrow."
            db.commit()
        
        # 更新工作计数
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
            return
        
        # 获取任务队列
        limit = max(1, user_profile.concurrency_limit - user_profile.work_count)
        task_queue = db.query(VideoTask).filter(
            VideoTask.user_id == user_profile.user_id, 
            VideoTask.status == VideoTaskStatus.QUEUE
        ).limit(limit).all()
        
        for task in task_queue:
            try:
                if user_profile.is_online == 0:
                    task.status = VideoTaskStatus.FAILED
                    task.failed_msg = "用户不在线"
                    db.commit()
                    continue
                
                print(f"Thread {thread_name} Selected User ID: {user_profile.id}, Token: {user_profile.token}, Work Count: {user_profile.work_count}")
                res = gen_video(user_profile.token, task.prompt, task.image_url, task.model_id, task.type)
                
                if res['statusInfo']['code'] != 0:
                    task.status = VideoTaskStatus.FAILED
                    task.failed_msg = res['statusInfo']['message']
                    db.commit()
                    continue
                    
                task.video_id = res["data"]["id"]
                task.status = VideoTaskStatus.CREATE
                user_profile.work_count += 1
                db.commit()
                db.refresh(task)
                db.refresh(user_profile)
                print(f"Thread {thread_name}: Successfully processed user {user_profile.user_id}")
                
            except Exception as e:
                task.add_failed_count += 1
                if task.add_failed_count > 3:
                    task.status = VideoTaskStatus.FAILED
                task.failed_msg = str(e)
                db.commit()
                print("gen video error", task.id, e)
                print(traceback.format_exc())
                continue
                
    finally:
        db.close()

def add_new_task():
    db = SessionLocal()
    try:
        # 获取所有用户信息
        user_profiles = db.query(UserProfile).all()
        
        # 创建线程安全的数据库会话工厂
        db_factory = scoped_session(sessionmaker(
            bind=db.get_bind(),
            expire_on_commit=False
        ))
        
        # 使用线程池执行任务
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(process_single_user, user_profile, db_factory)
                for user_profile in user_profiles
            ]
            
            # 等待所有任务完成
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f"Submit Task Thread error: {e}")
                    print(traceback.format_exc())
                    
    finally:
        db.close()