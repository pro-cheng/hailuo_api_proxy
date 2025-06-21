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
from .email_service import send_email

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
                # 重新获取work count
                res = get_video_status(user_profile.token, 0, 0)
                if res['statusInfo']['code'] == 0:
                    # 计算在线工作数量
                    user_profile.work_count = res['data']['processInfo']['onProcessingVideoNum']
                    user_profile.img_work_count = res['data']['processInfo']['onProcessingImageNum']
                    db.commit()
            except Exception as e:
                print(f"Refresh work count error: {e}")
    finally:
        db.close()

def monitor_failed_video_tasks():
    """监控过去半小时内的失败视频任务，超过60条发送告警邮件"""
    print("Monitoring failed video tasks...")
    
    # 获取数据库会话
    db = SessionLocal()
    try:
        # 计算半小时前的时间
        half_hour_ago = datetime.now() - timedelta(minutes=30)
        
        # 查询过去半小时内失败的视频任务数量
        failed_count = db.query(VideoTask).filter(
            VideoTask.status == VideoTaskStatus.FAILED,
            VideoTask.updated_at >= half_hour_ago,
            VideoTask.failed_msg != "System busy. Please try again tomorrow."
        ).count()
        
        print(f"Failed video tasks in last 30 minutes: {failed_count}")
        
        # 如果失败数量超过60条，发送告警邮件
        if failed_count > 60:
            # 构建邮件内容
            subject = f"🚨 视频任务失败告警 - {failed_count}条任务失败"
            
            html_content = f"""
            <html>
            <body>
                <h2 style="color: #d32f2f;">⚠️ 视频任务失败告警</h2>
                <p><strong>告警时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>时间范围:</strong> 过去30分钟</p>
                <p><strong>失败任务数量:</strong> <span style="color: #d32f2f; font-weight: bold; font-size: 18px;">{failed_count}</span> 条</p>
                <p><strong>告警阈值:</strong> 60条</p>
                
                <hr style="margin: 20px 0;">
                
                <h3>建议处理措施:</h3>
                <ul>
                    <li>检查海螺AI API服务状态</li>
                    <li>检查网络连接是否正常</li>
                    <li>查看系统日志排查具体错误原因</li>
                    <li>检查用户token是否有效</li>
                </ul>
                
                <p style="color: #666; font-size: 12px; margin-top: 30px;">
                    此邮件由视频任务监控系统自动发送，请及时处理相关问题。
                </p>
            </body>
            </html>
            """
            
            # 发送告警邮件 (可以配置多个收件人)
            alert_emails = [
                "promaverickzzz@gmail.com",  # 可以根据需要修改或添加更多邮箱
            ]
            
            for email in alert_emails:
                try:
                    email_id = send_email(
                        to=email,
                        subject=subject,
                        html_content=html_content
                    )
                    if email_id:
                        print(f"Alert email sent successfully to {email}, ID: {email_id}")
                    else:
                        print(f"Failed to send alert email to {email}")
                except Exception as e:
                    print(f"Error sending alert email to {email}: {str(e)}")
        
    except Exception as e:
        print(f"Error monitoring failed video tasks: {str(e)}")
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
scheduler.add_job(perform_frequent_task, 'interval', seconds=10, max_instances=1)

scheduler.add_job(refresh_work_count, 'interval', minutes=15, max_instances=1)

# 添加失败任务监控任务，每30分钟运行一次
scheduler.add_job(monitor_failed_video_tasks, 'interval', minutes=30, max_instances=1)

scheduler.start()

# 确保在应用关闭时关闭调度器
atexit.register(lambda: scheduler.shutdown())