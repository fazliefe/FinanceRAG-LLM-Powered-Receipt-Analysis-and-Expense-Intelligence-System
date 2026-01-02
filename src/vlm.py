import os
from pathlib import Path

# Placeholder for LLaVA / Multimodal support
# Requires: pip install llama-cpp-python[server] or similar
try:
    from llama_cpp import Llama
    from llama_cpp.llama_chat_format import Llava15ChatHandler
except ImportError:
    Llama = None
    Llava15ChatHandler = None

VLM_MODEL_PATH = os.getenv("VLM_MODEL_PATH", "")  # e.g. "models/llava-v1.5-7b-Q4_K.gguf"
CLIP_MODEL_PATH = os.getenv("CLIP_MODEL_PATH", "") # e.g. "models/mmproj-model-f16.gguf"

def get_vlm_handler():
    if not VLM_MODEL_PATH or not Path(VLM_MODEL_PATH).exists():
        return None
    if not CLIP_MODEL_PATH or not Path(CLIP_MODEL_PATH).exists():
        return None
        
    try:
        chat_handler = Llava15ChatHandler(clip_model_path=CLIP_MODEL_PATH)
        llm = Llama(
            model_path=VLM_MODEL_PATH,
            chat_handler=chat_handler,
            n_ctx=2048,
            n_gpu_layers=-1, # Auto
            verbose=False
        )
        return llm
    except Exception as e:
        print(f"VLM Init Error: {e}")
        return None

def analyze_receipt_image(image_path: str) -> str:
    """
    Analyzes an image using a local VLM to extract receipt data.
    Input: image_path (absolute path to image file)
    Output: JSON string with receipt data or empty string if failed.
    """
    llm = get_vlm_handler()
    if not llm:
        return "" 
        
    # Prepare image URI for the handler
    # Local file URI format: file:///absolute/path/to/image.jpg
    uri = Path(image_path).absolute().as_uri()
    
    prompt = """
    You are an expense assistant. Look at this receipt image.
    Extract the following fields in strict JSON format:
    {
      "merchant": "Store Name",
      "date": "YYYY-MM-DD",
      "total_amount": 123.45,
      "currency": "TRY",
      "items": [
        {"name": "Item 1", "qty": 1, "price": 10.0, "category": "Gida"},
        {"name": "Item 2", "qty": 2, "price": 5.0, "category": "Temizlik"}
      ]
    }
    If a field is not visible, use null.
    """
    
    try:
        response = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": "You are a helpful assistant that outputs JSON."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": uri}}
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=1024
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"VLM Analysis Failed: {e}")
        return ""
