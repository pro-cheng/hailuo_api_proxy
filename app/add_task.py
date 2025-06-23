from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from .models import VideoTask, VideoTaskStatus, UserProfile
from .database import SessionLocal
from .hailuo_api import gen_video, gen_image, cancel_video, get_video_status
from .email_service import send_email
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import List
from sqlalchemy.orm import scoped_session, sessionmaker
import threading
import time

# 全局变量，用于追踪上次发送邮件的时间
_last_ban_email_time = datetime.min

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
            try:
              if task.video_id:
                res = cancel_video(user_profile.token, task.video_id)
                if res['statusInfo']['code'] == 0:
                    if task.batch_type == 1:
                        user_profile.img_work_count -= 1
                    else:
                        user_profile.work_count -= 1
            except Exception as e:
              print(f"Thread {thread_name} TaskId {task.id}: Cancel Video Error: {e}")
              print(traceback.format_exc())
            task.status = VideoTaskStatus.FAILED
            task.failed_msg = "System busy. Please try again tomorrow."
            db.commit()
            
        tasks = db.query(VideoTask).filter(
            VideoTask.user_id == user_profile.user_id,
            VideoTask.status.in_([VideoTaskStatus.QUEUE]),
            VideoTask.created_at < datetime.now() - timedelta(hours=1.5)
        ).all()
        for task in tasks:
            task.status = VideoTaskStatus.FAILED
            task.failed_msg = "System busy. Please try again tomorrow."
            db.commit()

        db.refresh(user_profile)
        
        # 获取任务队列 - 分别处理视频和图片任务
        video_limit = max(1, user_profile.concurrency_limit - user_profile.work_count)
        image_limit = max(1, user_profile.img_concurrency_limit - user_profile.img_work_count)
        
        # 获取视频任务队列
        video_task_queue = db.query(VideoTask).filter(
            VideoTask.user_id == user_profile.user_id,
            VideoTask.status == VideoTaskStatus.QUEUE,
            VideoTask.batch_type == 0
        ).order_by(VideoTask.priority.desc(), VideoTask.created_at.asc()).limit(video_limit).all()
        
        # 获取图片任务队列
        image_task_queue = db.query(VideoTask).filter(
            VideoTask.user_id == user_profile.user_id,
            VideoTask.status == VideoTaskStatus.QUEUE,
            VideoTask.batch_type == 1
        ).order_by(VideoTask.priority.desc(), VideoTask.created_at.asc()).limit(image_limit).all()
        
        # 合并任务队列
        task_queue = video_task_queue + image_task_queue
        
        for task in task_queue:
            try:
                if user_profile.is_online == 0:
                    task.status = VideoTaskStatus.FAILED
                    task.failed_msg = "用户不在线"
                    db.commit()
                    continue
                
                print(f"Thread {thread_name} Selected User ID: {user_profile.id}, Token: {user_profile.token}, Work Count: {user_profile.work_count}")
                
                # 根据batch_type选择生成方法
                if task.batch_type == 1:
                    # 图片生成
                    if user_profile.img_work_count >= user_profile.img_concurrency_limit:
                        continue
                    res = gen_image(user_profile.token, task.prompt, task.model_id, task.aspect_ratio, task.quantity)
                else:
                    # 视频生成
                    if user_profile.work_count >= user_profile.concurrency_limit:
                        continue
                    res, origin_url = gen_video(user_profile.token, task.prompt, task.image_url, task.model_id, task.type, task.duration_type, task.resolution_type)
                    task.originURL = origin_url
                
                time.sleep(0.5)
                # 当前已有多个任务在队列中，只支持一次性生成0个
                if res['statusInfo']['code'] == 2400013:
                    # 重新获取work count
                    res = get_video_status(user_profile.token, 0, 0)
                    if res['statusInfo']['code'] == 0:
                        # 计算在线工作数量
                        user_profile.work_count = res['data']['processInfo']['onProcessingVideoNum']
                        user_profile.img_work_count = res['data']['processInfo']['onProcessingImageNum']
                        db.commit()
                    break
                # 封号
                if res['statusInfo']['code'] == 22 or res['statusInfo']['code'] == 2400008:
                    if task.batch_type == 1:
                        user_profile.img_work_count -= 1
                    else:
                        user_profile.work_count -= 1
                    task.status = VideoTaskStatus.FAILED
                    task.failed_msg = 'All credits have been exhausted. Please try again tomorrow!'
                    db.commit()
                    print(f"Thread {thread_name}: processed user {user_profile.user_id} banned, {res['statusInfo']['message']}")
                    
                    # 检查是否需要发送邮件通知
                    global _last_ban_email_time
                    current_time = datetime.now()
                    if current_time - _last_ban_email_time > timedelta(hours=1):
                        email_content = f"""
                        <h1>⚠️ User Account Banned Alert</h1>
                        <p>A user account has been banned or exhausted credits:</p>
                        <ul>
                            <li>User ID: {user_profile.user_id}</li>
                            <li>Error Code: {res['statusInfo']['code']}</li>
                            <li>Error Message: {res['statusInfo']['message']}</li>
                            <li>Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}</li>
                        </ul>
                        """
                        send_email(
                            to="promaverickzzz@gmail.com",
                            subject="⚠️ User Account Banned Alert",
                            html_content=email_content
                        )
                        _last_ban_email_time = current_time
                    
                    break                
                if res['statusInfo']['code'] != 0:
                    if task.batch_type == 1:
                        user_profile.img_work_count -= 1
                    else:
                        user_profile.work_count -= 1
                    task.status = VideoTaskStatus.FAILED
                    task.failed_msg = res['statusInfo']['message']
                    db.commit()
                    continue
                    
                task.video_id = res["data"]["id"]
                task.batch_id = res["data"]["task"]["batchID"]
                task.status = VideoTaskStatus.CREATE
                if task.batch_type == 1:
                    user_profile.img_work_count += 1
                else:
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
                time.sleep(1)
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