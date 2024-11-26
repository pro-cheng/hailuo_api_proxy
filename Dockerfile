# 使用官方的Python基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制项目的依赖文件
COPY requirements.txt .

# 安装项目的依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件到容器中
COPY . .

# 暴露FastAPI默认的端口
EXPOSE 8000

# 启动FastAPI应用
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]