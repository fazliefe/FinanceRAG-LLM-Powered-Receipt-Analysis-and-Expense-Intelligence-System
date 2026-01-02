"""
Model Manager - Çoklu model desteği ve otomatik seçim
"""
import os
from pathlib import Path
from typing import Optional, Literal
from llama_cpp import Llama

ModelType = Literal["fast", "accurate", "vision"]

class ModelManager:
    """Farklı görevler için farklı modeller yönetir"""
    
    def __init__(self):
        self.models = {}
        self.model_paths = {
            "fast": os.getenv("FAST_MODEL_PATH", "models/phi-3-mini-4k-instruct-q4.gguf"),
            "accurate": os.getenv("ACCURATE_MODEL_PATH", "models/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf"),
            "vision": os.getenv("VISION_MODEL_PATH", "models/llava-v1.5-7b-Q4_K.gguf"),
        }
        
    def get_model(self, model_type: ModelType = "accurate") -> Optional[Llama]:
        """Model yükle veya cache'den getir"""
        if model_type in self.models:
            return self.models[model_type]
            
        model_path = self.model_paths.get(model_type)
        if not model_path or not Path(model_path).exists():
            print(f"⚠️ {model_type} model bulunamadı: {model_path}")
            # Fallback to accurate model
            if model_type != "accurate":
                return self.get_model("accurate")
            return None
            
        try:
            print(f"📥 {model_type} model yükleniyor...")
            
            # GPU desteği kontrol
            n_gpu_layers = -1 if self._has_gpu() else 0
            
            model = Llama(
                model_path=model_path,
                n_ctx=2048,
                n_threads=8,
                n_gpu_layers=n_gpu_layers,
                verbose=False
            )
            
            self.models[model_type] = model
            print(f"✅ {model_type} model yüklendi (GPU: {n_gpu_layers > 0})")
            return model
            
        except Exception as e:
            print(f"❌ Model yükleme hatası: {e}")
            return None
    
    def _has_gpu(self) -> bool:
        """CUDA/GPU desteği var mı kontrol et"""
        try:
            import torch
            return torch.cuda.is_available()
        except:
            return False
    
    def select_model_for_task(self, task: str) -> ModelType:
        """Görev tipine göre en uygun modeli seç"""
        task_lower = task.lower()
        
        # Basit sorular için hızlı model
        simple_keywords = ["kaç", "toplam", "ne kadar", "var mı", "liste"]
        if any(kw in task_lower for kw in simple_keywords):
            return "fast" if Path(self.model_paths["fast"]).exists() else "accurate"
        
        # Görsel işleme
        if "resim" in task_lower or "fotoğraf" in task_lower or "görsel" in task_lower:
            return "vision"
        
        # Varsayılan: doğru model
        return "accurate"
    
    def clear_cache(self):
        """Tüm modelleri bellekten temizle"""
        self.models.clear()

# Global instance
_model_manager = None

def get_model_manager() -> ModelManager:
    """Singleton model manager"""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
