# app/models.py
from sqlalchemy import Column, Integer, String , DateTime, func , Enum, Float
from .database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
    
# 海螺的用户信息表    
class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True, index=True)
    u_id = Column(String, nullable=False, index=True)
    avatar = Column(String, nullable=True)  # 存储头像URL
    code = Column(String, nullable=True)    # 存储代码
    name = Column(String, nullable=True)    # 存储用户名
    real_user_id = Column(String, nullable=True)  # 存储真实用户ID
    is_online = Column(Integer, nullable=False, default=0)  # 是否在线
    user_id = Column(String, nullable=True)  # 存储用户ID
    is_new_user = Column(Integer, nullable=True)  # 存储是否为新用户的标志
    token = Column(String, nullable=False)  # 存储token
    concurrency_limit = Column(Integer, nullable=False, default=3)  # 并发个数限制，默认为1
    work_count = Column(Integer, nullable=False, default=0)  # 工作个数
    img_concurrency_limit = Column(Integer, nullable=False, default=6)  # 生成图片并发个数限制，默认为1
    img_work_count = Column(Integer, nullable=False, default=0)  # 生成图片工作个数
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 创建时间
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # 更新时间


# klingai 用户信息表
class KlingUserProfile(Base):
    __tablename__ = "kling_user_profiles"
    id = Column(Integer, primary_key=True, index=True)
    u_id = Column(String, nullable=False, index=True)
    avatar = Column(String, nullable=True)  # 存储头像URL
    user_id = Column(String, nullable=True, index=True)  # 存储用户ID
    user_name = Column(String, nullable=True)  # 存储用户名
    point = Column(Float, nullable=False, default=0)  # 存储总积分
    cookie = Column(String, nullable=True)  # 存储cookie
    work_count = Column(Integer, nullable=False, default=0)  # 工作个数
    concurrency_limit = Column(Integer, nullable=False, default=3)  # 并发个数限制，默认为1
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 创建时间
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # 更新时间



class VideoTaskStatus(enum.Enum):
    QUEUE = "queue"
    CREATE = "create"
    HL_QUEUE = "hl_queue"
    PROGRESS = "progress"
    SUCCESS = "success"
    FAILED = "failed"    


class KlingImageTaskType(enum.Enum):
    text2image = "text2image"  # 文字转图片
    image2image = "image2image"  # 图片转图片
    text2video = "text2video"  # 文字转视频
    image2video = "image2video"  # 图片转视频
    image2image_tail = "image2image_tail"  # 图片转图片（带尾巴）

# 视频任务
class KlingVideoTask(Base):
    __tablename__ = "kling_video_tasks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)  # 使用UUID作为主键
    u_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)  # 记录任务所属的用户ID
    job_id = Column(String, nullable=True)  # 记录任务的task_id
    inputs = Column(String, nullable=True)  # 记录任务的inputs
    add_failed_count = Column(Integer, nullable=True, default=0)  # 添加失败次数
    outputs = Column(String, nullable=True)  # 记录任务的outputs
    task_type = Column(Enum(KlingImageTaskType), nullable=False, server_default=KlingImageTaskType.text2image.value)  # 记录任务的类型
    status = Column(Enum(VideoTaskStatus), nullable=False, index=True, server_default=VideoTaskStatus.QUEUE.value)  # 使用枚举类型定义status，并设置默认值为queue
    failed_msg = Column(String, nullable=True) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 创建时间
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # 更新时间
    
    


class VideoTask(Base):
    __tablename__ = "video_tasks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)  # 使用UUID作为主键
    u_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)  # 记录任务所属的用户ID
    video_id = Column(String, nullable=False , index=True)  # 存储视频的唯一标识符
    batch_id = Column(String, nullable=True)
    batch_type = Column(Integer, nullable=False, default=0)
    aspect_ratio = Column(String, nullable=True) 
    request_ip = Column(String, nullable=True)  # 记录请求的IP地址
    visitor_id = Column(String, nullable=True)  # 记录请求的浏览器指纹id
    type = Column(Integer, nullable=False, default=0)  # 1:text to video 2:image to video 3:subject reference
    model_id = Column(String, nullable=True)  # 记录模型的ID
    desc = Column(String, nullable=True)
    prompt = Column(String, nullable=True)  # 添加prompt字段
    image_url = Column(String, nullable=True)  # 添加image_url字段
    add_failed_count = Column(Integer, nullable=False, default=0)  # 添加失败次数
    image_type = Column(Enum("url", "local",name="image_type_enum"), nullable=True)  # 限制image_type为"url"、"local"或为空
    coverURL = Column(String, nullable=False)
    videoURL = Column(String, nullable=False)
    originURL = Column(String, nullable=True)
    status = Column(Enum(VideoTaskStatus), nullable=False, index=True, server_default=VideoTaskStatus.QUEUE.value)  # 使用枚举类型定义status，并设置默认值为queue
    canRetry = Column(Integer, nullable=False)  # 使用Integer来表示布尔值
    failed_msg = Column(String, nullable=True) 
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    originFiles = Column(String, nullable=False)  # 存储originFiles的JSON字符串
    canAppeal = Column(Integer, nullable=False)  # 使用Integer来表示布尔值
    downloadURL = Column(String, nullable=False)
    percent = Column(Integer, nullable=False, default=0)  # 进度百分比
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 创建时间
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # 更新时间
    quantity = Column(Integer, nullable=False, default=1)
    assets = Column(String, nullable=True)

class SystemUser(Base):
    __tablename__ = "system_users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True, index=True)  # 用户名，必须唯一
    email = Column(String, nullable=False, unique=True)  # 邮箱，必须唯一
    phone = Column(String, nullable=True)  # 存储用户的电话号码
    hashed_password = Column(String, nullable=False)  # 存储加密后的密码
    is_active = Column(Integer, nullable=False, default=1)  # 表示用户是否活跃，使用Integer来表示布尔值
    is_superuser = Column(Integer, nullable=False, default=0)  # 表示用户是否为超级用户，使用Integer来表示布尔值
    is_vip = Column(Integer, nullable=False, default=0)  # 表示用户是否为VIP，使用Integer来表示布尔值
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 创建时间
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # 更新时间
