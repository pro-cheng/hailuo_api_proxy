# Conch Video Generation API Proxy

## Project Overview

This project is a conch video generation API proxy, designed to provide the following features:

- **Automatic Queueing**: Intelligently manage task queues to ensure tasks are executed in order.
- **Multi-account Management**: Support unified management of multiple accounts, making it easy for users to switch and operate.
- **Task Management**: Provide functions for task creation, monitoring, and management.
- **Automatic Task Submission**: Automate the task submission process to reduce manual intervention.
- **Kling Account Hosting**: Support for managing Kling accounts, including task creation and management.

Additionally, this project supports interface integration, making it easy to integrate with other systems.

## Usage Instructions

Currently, this service is open for free use. You can experience it directly through the following URL:

[http://hailuo.st-ai.top/public](http://hailuo.st-ai.top/public)

No registration or login is required, and you can use all features directly.

### API Documentation

For detailed API documentation, please visit:

- [API Documentation (English)](http://hailuo.st-ai.top/docs)

## Contact Information

If you have any questions or suggestions, please contact us through the following ways:


Thank you for your use and support!

### Build Multi-platform Push

To build a multi-platform Docker image, use the following command:

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t hexiaochun/hailuo_api_proxy:latest --push .
```

### Build Docker Image

To build a Docker image, run the following command in the root directory of the project:

```bash
docker build -t hailuo_api_proxy .
```

To run the Docker container, use:

```bash
docker run -d -p 8130:8000 hailuo_api_proxy
```

API address: [http://127.0.0.1:8130/docs](http://127.0.0.1:8130/docs)

Web address: [http://127.0.0.1:8130/public](http://127.0.0.1:8130/public)

admin address: [http://127.0.0.1:8130/admin](http://127.0.0.1:8130/admin)

Account: admin

Password: hailuo888!!!

### Online Docker One-click Deployment

```bash
docker run -d -p 8130:8000 hexiaochun/hailuo_api_proxy:latest
```



# hailuo 视频生成 API 代理

## 项目概述

该项目是一个 hailuo 视频生成 API 代理，旨在提供以下功能：

- **自动排队**：智能管理任务队列，确保任务按顺序执行。
- **多账户管理**：支持多个账户的统一管理，方便用户切换和操作。
- **任务管理**：提供任务创建、监控和管理功能。
- **自动任务提交**：自动化任务提交过程，减少人工干预。
- **Kling 账户托管**：支持管理 Kling 账户，包括任务创建和管理。

此外，该项目支持接口集成，便于与其他系统集成。

## 使用说明

目前，该服务免费开放使用。您可以通过以下 URL 直接体验：

[http://hailuo.st-ai.top/public](http://hailuo.st-ai.top/public)

无需注册或登录，您可以直接使用所有功能。

### API 文档

有关详细的 API 文档，请访问：

- [API 文档 (英文)](http://hailuo.st-ai.top/docs)

## 联系信息

如果您有任何问题或建议，请通过以下方式联系我们：

感谢您的使用和支持！

### 构建多平台推送

要构建多平台 Docker 镜像，请使用以下命令：

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t hexiaochun/hailuo_api_proxy:latest --push .
```

### 构建 Docker 镜像

要构建 Docker 镜像，请在项目根目录运行以下命令：

```bash
docker build -t hailuo_api_proxy .
```

要运行 Docker 容器，请使用：

```bash
docker run -d -p 8130:8000 hailuo_api_proxy
```

API 地址: [http://127.0.0.1:8130/docs](http://127.0.0.1:8130/docs)

Web 地址: [http://127.0.0.1:8130/public](http://127.0.0.1:8130/public)

管理地址: [http://127.0.0.1:8130/admin](http://127.0.0.1:8130/admin)

账号: admin

密码: hailuo888!!!

### 在线 Docker 一键部署

```bash
docker run -d -p 8130:8000 hexiaochun/hailuo_api_proxy:latest
```

![添加任务示例](images/add_task.png)
![任务列表](images/task_list.png)
![账号列表](images/account_list.png)
![接口文档](images/api.png)


