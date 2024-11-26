# app/main.py
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from . import models 
from .models import UserProfile, VideoTask, SystemUser, KlingUserProfile, KlingVideoTask
from .database import SessionLocal, engine
from .user_profile_api import router as user_profile_router
from .video_task_api import router as video_task_router
from .kling.kling_account import router as kling_account_router
from . import scheduler_tasks 
from sqladmin import Admin, ModelView
from .auth import auth_router 
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqladmin.authentication import AuthenticationBackend
import secrets

# 创建数据库表
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源。你可以根据需要指定特定的来源。
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有 HTTP 头
)
app.mount("/public", StaticFiles(directory="public" , html=True), name="static")

app.include_router(user_profile_router)
app.include_router(video_task_router)
app.include_router(auth_router)
app.include_router(kling_account_router)
class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        print("login")
        # 获取用户密码
        form_data = await request.form()
        username = form_data["username"]
        password = form_data["password"]
        print(username, password, "username, password")
        if username == "admin" and password == "hailuo888!!!":
            request.session.update({"token": "zeoqgmwdg0WyY"})
            return True
        else:
            return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False

        # Check the token in depth
        return True

# 添加自定义认证中间件
authentication_backend = AdminAuth(secret_key="hailuo888!!!")

admin = Admin(app, engine, authentication_backend=authentication_backend)

class UserAdmin(ModelView, model=UserProfile):
    column_list = [UserProfile.id, UserProfile.name ,  UserProfile.user_id, UserProfile.work_count,  UserProfile.concurrency_limit ,   UserProfile.created_at , UserProfile.updated_at]
    # 定义自定义按钮
    name = "用户管理"
    can_create = False
    column_default_sort = [(UserProfile.created_at, True)]  # True 表示降序

class VideoTaskAdmin(ModelView, model=VideoTask):
    column_list = [VideoTask.id, VideoTask.user_id ,  VideoTask.videoURL , VideoTask.video_id , VideoTask.status , VideoTask.created_at , VideoTask.updated_at]
    name = "视频任务管理"
    can_create = False
    column_default_sort = [(VideoTask.created_at, True)]  # True 表示降序

class SystemUserAdmin(ModelView, model=SystemUser):
    column_list = [SystemUser.id, SystemUser.username , SystemUser.email , SystemUser.phone , SystemUser.created_at , SystemUser.updated_at]
    name = "系统用户管理"
    can_create = False
    column_default_sort = [(SystemUser.created_at, True)]  # True 表示降序
class KlingUserProfileAdmin(ModelView, model=KlingUserProfile):
    column_list = [KlingUserProfile.id, KlingUserProfile.user_id , KlingUserProfile.user_name ,  KlingUserProfile.created_at , KlingUserProfile.updated_at]
    name = "Kling用户管理"
    can_create = False
    column_default_sort = [(KlingUserProfile.created_at, True)]  # True 表示降序
class KlingVideoTaskAdmin(ModelView, model=KlingVideoTask):
    column_list = [KlingVideoTask.id, KlingVideoTask.user_id , KlingVideoTask.status , KlingVideoTask.created_at , KlingVideoTask.updated_at]
    name = "Kling视频任务管理"
    can_create = False
    column_default_sort = [(KlingVideoTask.created_at, True)]  # True 表示降序
    
admin.add_view(UserAdmin)
admin.add_view(VideoTaskAdmin)
admin.add_view(SystemUserAdmin)
admin.add_view(KlingUserProfileAdmin)
admin.add_view(KlingVideoTaskAdmin)
# 将 FastAPI-Admin 挂载到 FastAPI 应用
# app.mount("/admin", admin_app)