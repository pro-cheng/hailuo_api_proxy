from sqlalchemy.orm import Session
from .models import VideoTask, VideoTaskStatus,UserProfile
from .database import SessionLocal
from .hailuo_api import get_video_status
from datetime import datetime

def sync_hailuo_tasks():
    # 创建数据库会话
    db: Session = SessionLocal()
    try:
        tasks_to_sync = db.query(VideoTask).filter(
            VideoTask.status.in_([
                VideoTaskStatus.CREATE,
                VideoTaskStatus.HL_QUEUE,
                VideoTaskStatus.PROGRESS
            ])
        ).all()

        for task in tasks_to_sync:
            print(f"Syncing Task: {task.id}, Status: {task.status}")
            if not task.video_id:
                task.status = VideoTaskStatus.FAILED
                task.failed_msg = "video_id is None"
                db.commit()
                continue
            if not task.user_id:
                task.status = VideoTaskStatus.FAILED
                task.failed_msg = "user_id is None"
                db.commit()
                continue

            if task.user_id:
                user = db.query(UserProfile).filter(UserProfile.user_id == task.user_id).first()
                if not user:
                    task.status = VideoTaskStatus.FAILED
                    task.failed_msg = "user not found"
                    db.commit()
                    continue
                token = user.token
                res = get_video_status(token,task.video_id)
                if res and res['data'] and res['data']['videos']:
                    task.status = VideoTaskStatus.HL_QUEUE
                    if res['data']['videos'][0]['status'] == 5 or res['data']['videos'][0]['status'] == 14:
                        task.status = VideoTaskStatus.FAILED
                        user.work_count -= 1 
                    elif res['data']['videos'][0]['status'] == 2:
                        task.status = VideoTaskStatus.SUCCESS
                        user.work_count -= 1 
                    if res['data']['videos'][0].get('message'):
                        task.failed_msg = res['data']['videos'][0]['message']
                    
                    online_work_count = 0
                    for tmp_video in res['data']['videos']:
                        if tmp_video['status'] != 2 and tmp_video['status'] != 5:
                            online_work_count += 1 
                    user.work_count = online_work_count
                    
                    task.videoURL = res['data']['videos'][0]['videoURL']
                    task.coverURL = res['data']['videos'][0]['coverURL']
                    task.width = res['data']['videos'][0]['width']
                    task.height = res['data']['videos'][0]['height']
                    task.updated_at = datetime.now()    
                    
                    
                    
                db.commit()
        # 提交更改
        db.commit()
        
        return tasks_to_sync
    finally:
        db.close()