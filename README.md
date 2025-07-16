# CogAgent: An open-sourced VLM-based GUI Agent
## run in demo
```shell
conda create -n cog_env python=3.10 -y

conda activate cog_env

pip install -r requirements.txt

python inference/cli_demo.py --model_dir THUDM/cogagent-9b-20241220 --platform "Mac" --max_length 4096 --top_k 1 --output_image_path ./results --format_key status_action_op_sensitive

```
## run in server
```shell
make build
make run
```
