from fastapi import FastAPI, File, UploadFile, Form
from PIL import Image, ImageDraw
import io
import os
import re
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import List
import uvicorn
import logging
from datetime import datetime

# Configure logging
os.makedirs("./logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(f"./logs/app_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Global variables for model and tokenizer
model = None
tokenizer = None
# 从环境变量获取模型路径，如果未设置，则使用默认值
MODEL_DIR = os.getenv("MODEL_STORAGE_PATH", "THUDM/cogagent-9b-20241220")
PLATFORM = "Mac"
MAX_LENGTH = 4096
TOP_K = 1
OUTPUT_DIR = "./results"

def draw_boxes_on_image(image: Image.Image, boxes: List[List[float]], save_path: str):
    logger.info(f"Drawing boxes on image and saving to {save_path}")
    draw = ImageDraw.Draw(image)
    for box in boxes:
        x_min = int(box[0] * image.width)
        y_min = int(box[1] * image.height)
        x_max = int(box[2] * image.width)
        y_max = int(box[3] * image.height)
        draw.rectangle([x_min, y_min, x_max, y_max], outline="red", width=3)
    image.save(save_path)

@app.on_event("startup")
async def load_model():
    global model, tokenizer
    logger.info("Starting model loading")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_DIR,
            torch_dtype=torch.bfloat16,
            trust_remote_code=True,
            device_map="auto"
        ).eval()
        logger.info("Model and tokenizer loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        raise

@app.post("/api/v1/agent/recognize")
async def recognize(question: str = Form(...), image: UploadFile = File(...)):
    logger.info(f"Received request with question: {question}, image: {image.filename}")
    try:
        # Store the original UploadFile object for filename access
        uploaded_file = image
        # Read and process the image
        image_data = await uploaded_file.read()
        image = Image.open(io.BytesIO(image_data)).convert("RGB")

        # Prepare query
        format_str = "(Answer in Status-Action-Operation-Sensitive format.)"
        platform_str = f"(Platform: {PLATFORM})\n"
        query = f"Task: {question}\nHistory steps: \n{platform_str}{format_str}"

        # Tokenize inputs
        inputs = tokenizer.apply_chat_template(
            [{"role": "user", "image": image, "content": query}],
            add_generation_prompt=True,
            tokenize=True,
            return_tensors="pt",
            return_dict=True,
        ).to(model.device)

        # Generate response
        logger.info("Generating model response")
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_length=MAX_LENGTH,
                do_sample=True,
                top_k=TOP_K
            )
            outputs = outputs[:, inputs["input_ids"].shape[1]:]
            response = tokenizer.decode(outputs[0], skip_special_tokens=True)
            logger.info("Model response generated successfully")

        # Extract bounding boxes
        box_pattern = r"box=\[\[?(\d+),(\d+),(\d+),(\d+)\]?\]"
        matches = re.findall(box_pattern, response)
        output_path = None
        if matches:
            boxes = [[int(x) / 1000 for x in match] for match in matches]
            base_name = os.path.splitext(uploaded_file.filename)[0]
            output_file_name = f"{base_name}_processed.png"
            output_path = os.path.join(OUTPUT_DIR, output_file_name)
            draw_boxes_on_image(image, boxes, output_path)
            logger.info(f"Annotated image saved at: {output_path}")
        else:
            logger.warning("No bounding boxes found in the response")

        return {
            "response": response,
            "annotated_image_path": output_path if output_path else "No bounding boxes found"
        }
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
