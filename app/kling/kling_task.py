from sqlalchemy.orm import Session
from ..models import KlingVideoTask, KlingUserProfile,KlingImageTaskType,VideoTaskStatus
from ..database import SessionLocal
from .kling_api import BaseGen,ImageGen,VideoGen,TaskStatus
from datetime import datetime
import json
import time

def add_kling_new_task():
    db: Session = SessionLocal()
    #获取所有在线的kling用户
    kling_user_profiles = db.query(KlingUserProfile).all()
    for kling_user_profile in kling_user_profiles:
        kling_user_profile : KlingUserProfile = kling_user_profile
        
        work_count = db.query(KlingVideoTask).filter(
            KlingVideoTask.user_id == kling_user_profile.user_id,
            KlingVideoTask.status.in_([
                VideoTaskStatus.CREATE,
                VideoTaskStatus.HL_QUEUE,
                VideoTaskStatus.PROGRESS
            ])
        ).count()
        kling_user_profile.work_count = work_count
        db.commit()
        db.refresh(kling_user_profile)
        
        if kling_user_profile.work_count >= kling_user_profile.concurrency_limit:
            # 如果用户的工作数量达到了并发限制，则跳过该用户
            continue
        # 获取这个账号任务队列
        limit = kling_user_profile.concurrency_limit - kling_user_profile.work_count
        if limit < 1:
            limit = 1
        task_queue = db.query(KlingVideoTask).filter(KlingVideoTask.u_id == kling_user_profile.u_id, KlingVideoTask.status == VideoTaskStatus.QUEUE).limit(limit).all()
        if len(task_queue) > 0:
            for task in task_queue:
                task:KlingVideoTask = task
                try:
                    if task.task_type == KlingImageTaskType.text2image:
                        bg:ImageGen = ImageGen(kling_user_profile.cookie)
                        data = json.loads(task.inputs)                    
                        request_id = bg.submit_image_task(prompt=data['prompt'],aspect_ratio=data['aspect_ratio'],image_count=data['count'])
                        task.job_id = request_id
                        task.status = VideoTaskStatus.CREATE
                        task.updated_at = datetime.now()
                        kling_user_profile.work_count += 1
                        db.commit()
                        db.refresh(task)
                        db.refresh(kling_user_profile)
                        
                    elif task.task_type == KlingImageTaskType.image2image:
                        bg:ImageGen = ImageGen(kling_user_profile.cookie)
                        data = json.loads(task.inputs)                    
                        request_id = bg.submit_image_task(prompt=data['prompt'],aspect_ratio=data['aspect_ratio'],image_count=data['count'],image_path=data['image'])
                        task.job_id = request_id
                        task.status = VideoTaskStatus.CREATE
                        task.updated_at = datetime.now()
                        kling_user_profile.work_count += 1
                        db.commit()
                        db.refresh(task)
                        db.refresh(kling_user_profile)
                        
                        pass
                    elif task.task_type == KlingImageTaskType.text2video:
                        tv:VideoGen = VideoGen(kling_user_profile.cookie)
                        data = json.loads(task.inputs)                    
                        request_id = tv.submit_video_task(prompt=data['prompt'],aspect_ratio=data['aspect_ratio'],is_high_quality=data['is_high_quality'],model_name=data['model_name'])
                        task.job_id = request_id
                        task.status = VideoTaskStatus.CREATE
                        task.updated_at = datetime.now()
                        kling_user_profile.work_count += 1
                        db.commit()
                        db.refresh(task)
                        db.refresh(kling_user_profile)
                        
                        pass
                    elif task.task_type == KlingImageTaskType.image2video or task.task_type == KlingImageTaskType.image2image_tail:
                        tv:VideoGen = VideoGen(kling_user_profile.cookie)
                        data = json.loads(task.inputs)        
                        if task.task_type == KlingImageTaskType.image2video:
                            data['tail_image'] = None
                        request_id = tv.submit_video_task(prompt=data['prompt'],aspect_ratio=data['aspect_ratio'],is_high_quality=data['is_high_quality'],model_name=data['model_name'],image_path=data['image'],tail_image_path=data['tail_image'])
                        task.job_id = request_id
                        task.status = VideoTaskStatus.CREATE
                        task.updated_at = datetime.now()
                        kling_user_profile.work_count += 1
                        db.commit()
                        db.refresh(task)
                        db.refresh(kling_user_profile)
                except Exception as e:
                    print(e)
                    task.add_failed_count += 1
                    task.failed_msg = str(e)
                    if task.add_failed_count >= 3:
                        task.status = VideoTaskStatus.FAILED
                    db.commit()
                    db.refresh(task)
        

def sync_kling_task_info():
    print("sync_kling_task_info")
    db: Session = SessionLocal()
    tasks = db.query(KlingVideoTask).filter(
            KlingVideoTask.status.in_([
                VideoTaskStatus.CREATE,
                VideoTaskStatus.HL_QUEUE,
                VideoTaskStatus.PROGRESS
            ])
        ).all()
    for task in tasks:
        task:KlingVideoTask = task
        user_profile:KlingUserProfile = db.query(KlingUserProfile).filter(KlingUserProfile.user_id == task.user_id).first()
        if user_profile:
            user_profile:KlingUserProfile = user_profile
            if user_profile.cookie:
                
                    bg:ImageGen = ImageGen(user_profile.cookie)
                    res,status = bg.get_image_task_info(task.job_id)
                    print(res)
                    if status == TaskStatus.COMPLETED:
                        task.status = VideoTaskStatus.SUCCESS
                        result = []
                        works = res.get("works", [])
                        if not works:
                            print("No images found.")
                            task.status = VideoTaskStatus.HL_QUEUE
                            task.failed_msg = "No images found."
                        else:
                            for work in works:
                                resource = work.get("resource", {}).get("resource")
                                result.append(resource)
                            task.status = VideoTaskStatus.SUCCESS
                            user_profile.work_count -= 1
                            task.outputs = json.dumps(result)
                    elif status == TaskStatus.FAILED:
                        task.status = VideoTaskStatus.FAILED
                        user_profile.work_count -= 1
                        task.failed_msg = res.get('data',{}).get("message", "Failed to get task info")
                    else:
                        task.status = VideoTaskStatus.HL_QUEUE
                        task.failed_msg = res['message']
                    task.updated_at = datetime.now()
                    db.commit()
                    db.refresh(task)
                    db.refresh(user_profile)
                    
                    
        
        