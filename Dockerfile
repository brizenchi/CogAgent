FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
# 复制项目文件
COPY . .

RUN pip install --upgrade pip setuptools \
    && pip install --no-cache-dir -r requirements-final-locked.txt

# 设置环境变量
ENV PYTHONPATH=/app
ENV TZ=UTC

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["python", "main.py"]
