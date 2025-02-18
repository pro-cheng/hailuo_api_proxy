# scheduler_tasks.py
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from .add_task import add_new_task
from .asyn_task import sync_hailuo_tasks
from .database import SessionLocal
from .models import UserProfile,VideoTask,VideoTaskStatus
from .user_profile_api import process_user_info
from datetime import datetime, timedelta
import os
import shutil
from .kling.kling_task import add_kling_new_task,sync_kling_task_info
from .hailuo_api import get_video_status
# 定义第一个定时任务
def check_user_profiles():
    print("Checking user profiles...")
     # 获取数据库会话
    db = SessionLocal()
    try:
        # 获取所有用户
        user_profiles = db.query(UserProfile).all()
        
        for user_profile in user_profiles:
            # 调用 process_user_info 更新每个用户的信息
            process_user_info(user_profile.token, db, current_user=None)  # 假设 current_user 不需要在此上下文中使用
    finally:
        db.close()
    
    # 这里可以添加你需要的检查逻辑

def refresh_work_count():
    print("Refreshing work count...")
    # 获取数据库会话
    db = SessionLocal()
    try:
        # 获取所有用户
        user_profiles = db.query(UserProfile).all()
        
        for user_profile in user_profiles:
            try:
                res = get_video_status(user_profile.token, 0)
                if res and res['data'] and res['data']['videoList']:
                    # 计算在线工作数量
                    online_work_count = sum(
                        1 for video in res['data']['videoList']
                        if video['videoAsset']['status'] not in [2, 5, 14, 7]
                    )
                    user_profile.work_count = online_work_count
                    db.commit()
            except Exception as e:
                print(f"Refresh work count error: {e}")
    finally:
        db.close()

# 定义第二个定时任务
def clean_expired_tokens():
    print("Cleaning expired tokens...")
    sync_hailuo_tasks()

# 定义第三个定时任务
def perform_frequent_task():
    print("Performing frequent task...")
    add_new_task()
    add_kling_new_task()

# 创建并启动调度器
scheduler = BackgroundScheduler()

def perform_delete_images():
    print("Performing delete images...")
    # 获取images路径里面的除了今天和昨天的文件夹都删除
    images_path = os.path.join(os.getcwd(), 'images')
    today = datetime.now().strftime('%Y-%m-%d')
    three_days_ago = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
    for folder in os.listdir(images_path):
        if folder < three_days_ago:
            shutil.rmtree(os.path.join(images_path, folder))

scheduler.add_job(perform_delete_images, 'interval', hours=5)

# 添加第一个任务，每10分钟运行一次
scheduler.add_job(check_user_profiles, 'interval', minutes=60)

# 添加第二个任务，每20秒运行一次
scheduler.add_job(clean_expired_tokens, 'interval', seconds=20, max_instances=1)

scheduler.add_job(sync_kling_task_info, 'interval', seconds=30)

# 添加第三个任务，每6秒运行一次
scheduler.add_job(perform_frequent_task, 'interval', seconds=6, max_instances=1)

scheduler.add_job(refresh_work_count, 'interval', minutes=15, max_instances=1)

scheduler.start()

# 确保在应用关闭时关闭调度器
atexit.register(lambda: scheduler.shutdown())