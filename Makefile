# ==============================================================================
# Configuration
# ==============================================================================
# 'make' 命令中可以覆盖这些变量, e.g., 'make run PORT=8081'
IMAGE_NAME     = cogagent-service
CONTAINER_NAME = cogagent-container
TAG            = latest
PORT           = 8000
CURDIR         = /home/featurize/CogAgent

# --- Host paths (使用绝对路径以保证 Docker 挂载的稳定性)
# !!! 重要: 请根据你的系统路径修改下面这几行 !!!
MODEL_DIR      = /home/featurize/.cache/huggingface/hub/models--THUDM--cogagent-9b-20241220/snapshots/0de2cad8d51f2621a15f9d6ba3eb2944a41f0292
OUTPUT_DIR     = $(CURDIR)/results
LOG_DIR        = $(CURDIR)/logs

# --- Test variables
TEST_IMAGE_PATH = "$(CURDIR)/iShot_2025-07-15_18.29.16.png" # 你的测试图片路径
TEST_QUESTION   = "where is the input field"


# ==============================================================================
# Targets
# ==============================================================================
.PHONY: all help build run up down stop logs clean test

all: help ## ✨ 显示所有可用的命令 (默认)

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

up: build run ## 🚀 构建镜像并启动容器

down: stop ## 🛑 停止并移除容器

build: ## 🛠️  构建 Docker 镜像
	@echo "--> Building Docker image: $(IMAGE_NAME):$(TAG)"
	@docker build -t $(IMAGE_NAME):$(TAG) .

run: ## ▶️  在后台运行 Docker 容器
	@echo "--> Creating host directories for logs and results..."
	@mkdir -p $(LOG_DIR) $(OUTPUT_DIR)
	@echo "--> Running container [$(CONTAINER_NAME)] on port $(PORT)"
	@docker run --rm -d \
		--name $(CONTAINER_NAME) \
		-p $(PORT):8000 \
		--gpus all \
		-v $(MODEL_DIR):/model:ro \
		-v $(OUTPUT_DIR):/app/results \
		-v $(LOG_DIR):/app/logs \
		-e MODEL_STORAGE_PATH=/model \
		$(IMAGE_NAME):$(TAG)
	@echo "--> Container started. Use 'make logs' to see the output."

stop: ## ⏹️  停止并移除正在运行的容器
	@echo "--> Stopping and removing container [$(CONTAINER_NAME)]..."
	@docker stop $(CONTAINER_NAME) > /dev/null 2>&1 || true
	@docker rm $(CONTAINER_NAME) > /dev/null 2>&1 || true

logs: ## 📝 查看容器的实时日志
	@echo "--> Tailing logs for [$(CONTAINER_NAME)]..."
	@docker logs -f $(CONTAINER_NAME)

clean: down ## 🧹 清理容器和镜像 (先停止容器再删除镜像)
	@echo "--> Removing Docker image: $(IMAGE_NAME):$(TAG)..."
	@docker rmi $(IMAGE_NAME):$(TAG) || true

test: ## 🧪 向服务发送一个测试请求
	@echo "--> Sending test request to http://127.0.0.1:$(PORT)"
	@curl -s --location --request POST 'http://127.0.0.1:$(PORT)/api/v1/agent/recognize' \
	--form "question=$(TEST_QUESTION)" \
	--form 'image=@$(TEST_IMAGE_PATH)' | jq .
