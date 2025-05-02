from sqlalchemy.orm import Session, scoped_session, sessionmaker
from .models import VideoTask, VideoTaskStatus, UserProfile
from .database import SessionLocal
from .hailuo_api import get_video_status, read_task
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading
import traceback

def process_single_task(task_id: int, db_factory):
    """处理单个视频任务"""
    thread_name = threading.current_thread().name
    print(f"Thread {thread_name} processing task {task_id}")
    
    db = db_factory()
    try:
        # 获取任务信息
        task = db.query(VideoTask).get(task_id)
        if not task:
            print(f"Thread {thread_name}: Task {task_id} not found")
            return
            
        print(f"Thread {thread_name}: Syncing Task: {task.id}, Status: {task.status}")
        
        # 验证基本信息
        if not task.video_id:
            task.status = VideoTaskStatus.FAILED
            task.failed_msg = "video_id is None"
            db.commit()
            return
            
        if not task.user_id:
            task.status = VideoTaskStatus.FAILED
            task.failed_msg = "user_id is None"
            db.commit()
            return

        # 获取用户信息
        user = db.query(UserProfile).filter(UserProfile.user_id == task.user_id).first()
        if not user:
            task.status = VideoTaskStatus.FAILED
            task.failed_msg = "user not found"
            db.commit()
            return
            
        # 获取视频状态
        token = user.token
        batch_id = task.video_id
        if task.batch_type == 1:
            batch_id = task.batch_id
        res = get_video_status(token, batch_id, task.batch_type)
        
        if res['statusInfo']['code'] == 0:
            # 查找匹配的assets
            target_asset = None
            for batch in res['data']['batchVideos']:
                for asset in batch['assets']:
                    if asset['id'] == task.video_id:
                        target_asset = asset
                        break
                if target_asset:
                    break

            if target_asset:
                task.status = VideoTaskStatus.HL_QUEUE
                
                # 处理不同的视频状态
                if target_asset['status'] == 1:
                    task.percent = target_asset['percent']
                elif target_asset['status'] in [5, 14, 7]:
                    task.status = VideoTaskStatus.FAILED
                    user.work_count -= 1
                    read_task(token, [task.video_id])
                elif target_asset['status'] == 2:
                    task.status = VideoTaskStatus.SUCCESS
                    task.percent = 100
                    task.videoURL = target_asset['downloadURL']
                    task.downloadURL = target_asset['downloadURL']
                    user.work_count -= 1
                    read_task(token, [task.video_id])
                # 设置失败信息
                if target_asset.get('message'):
                    task.failed_msg = target_asset['message']
                if "<wait>" in task.failed_msg:
                    task.failed_msg = "Queuing..."

                # 更新其他视频信息
                task.coverURL = target_asset['coverURL']
                task.width = target_asset['width']
                task.height = target_asset['height']
                task.updated_at = datetime.now()

                db.commit()
                print(f"Thread {thread_name}: Successfully processed task {task_id}")
            else:
                task.status = VideoTaskStatus.FAILED
                task.failed_msg = f"Failed to generate video. Please retry."
                db.commit()
                print(f"Thread {thread_name}: Video {task.video_id} not found in response")

            # 计算在线工作数量
            user.work_count = res['data']['processInfo']['onProcessingVideoNum']
            user.img_work_count = res['data']['processInfo']['onProcessingImageNum']             
            db.commit()
    except Exception as e:
        print(f"Thread {thread_name}: Error processing task {task_id}: {str(e)}")
        print(traceback.format_exc())
    finally:
        db.close()

def sync_hailuo_tasks():
    db = SessionLocal()
    try:
        # 获取需要同步的任务
        tasks_to_sync = db.query(VideoTask).filter(
            VideoTask.status.in_([
                VideoTaskStatus.CREATE,
                VideoTaskStatus.HL_QUEUE,
                VideoTaskStatus.PROGRESS
            ])
        ).all()
        
        task_ids = [task.id for task in tasks_to_sync]
        
        # 创建线程安全的数据库会话工厂
        db_factory = scoped_session(sessionmaker(
            bind=db.get_bind(),
            expire_on_commit=False
        ))
        
        # 使用线程池处理任务
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(process_single_task, task_id, db_factory)
                for task_id in task_ids
            ]
            
            # 等待所有任务完成
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f"Get Task Thread error: {e}")
                    print(traceback.format_exc())
        
        return tasks_to_sync
        
    finally:
        db.close()