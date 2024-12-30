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
                if res and res['data'] and res['data']['videoList']:
                    # Find the video that matches task.video_id
                    target_video = None
                    for video in res['data']['videoList']:
                        if video['id'] == task.video_id:
                            target_video = video['videoAsset']
                            break    
                    if target_video:
                        task.status = VideoTaskStatus.HL_QUEUE
                        if target_video['status'] == 1:
                            task.percent = target_video['percent']
                        elif target_video['status'] == 5 or target_video['status'] == 14:
                            task.status = VideoTaskStatus.FAILED
                            user.work_count -= 1 
                        elif target_video['status'] == 2:
                            task.status = VideoTaskStatus.SUCCESS
                            task.percent = target_video['percent']
                            task.videoURL = target_video['downloadURL']
                            task.downloadURL = target_video['downloadURL']
                            user.work_count -= 1 
                        if target_video.get('message'):
                            task.failed_msg = target_video['message']

                        online_work_count = 0
                        for tmp_video in res['data']['videoList']:
                            if tmp_video['videoAsset']['status'] != 2 and tmp_video['videoAsset']['status'] != 5:
                                online_work_count += 1 
                        user.work_count = online_work_count        

                        
                        task.coverURL = target_video['coverURL']
                        task.width = target_video['width']
                        task.height = target_video['height']
                        task.updated_at = datetime.now()    

                db.commit()
        # 提交更改
        db.commit()
        
        return tasks_to_sync
    finally:
        db.close()