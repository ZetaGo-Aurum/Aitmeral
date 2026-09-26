"""AI Engine abstraction for video/image enhancement (mmagic, Real-ESRGAN, etc.)"""

from __future__ import annotations

import os
import subprocess
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

import cv2
import numpy as np
from PIL import Image


@dataclass
class AIEngineConfig:
    """Configuration for AI engine"""
    name: str
    model: str
    scale: int = 4
    tile_size: int = 0
    tile_pad: int = 10
    pre_pad: int = 0
    fp32: bool = False
    gpu_id: int = 0
    out_ext: str = "png"
    extra_args: Dict[str, Any] = None


@dataclass
class ProcessResult:
    """Result of AI processing"""
    output_path: str
    success: bool
    error: str = ""
    metadata: Dict[str, Any] = None


class AIEngineBase(ABC):
    """Base class for AI enhancement engines"""
    
    def __init__(self, config: AIEngineConfig):
        self.config = config
        self._model = None
        self._device = None
    
    @abstractmethod
    def load_model(self) -> bool:
        """Load the AI model. Returns True if successful."""
        pass
    
    @abstractmethod
    def enhance_image(self, input_path: str, output_path: str) -> ProcessResult:
        """Enhance a single image. Returns ProcessResult."""
        pass
    
    @abstractmethod
    def enhance_video(self, input_path: str, output_path: str, 
                      progress_callback=None) -> ProcessResult:
        """Enhance video frame by frame. Returns ProcessResult."""
        pass
    
    @abstractmethod
    def get_supported_models(self) -> List[str]:
        """Return list of supported model names."""
        pass
    
    @abstractmethod
    def get_engine_info(self) -> Dict[str, Any]:
        """Return engine information (name, version, capabilities)."""
        pass
    
    def _get_device(self):
        """Get torch device (cuda/mps/cpu)"""
        try:
            import torch
            if torch.cuda.is_available():
                return torch.device(f"cuda:{self.config.gpu_id}")
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return torch.device("mps")
        except Exception:
            pass
        return torch.device("cpu") if 'torch' in globals() else "cpu"
    
    def _read_image(self, path: str) -> np.ndarray:
        """Read image as RGB numpy array"""
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is None:
            raise ValueError(f"Cannot read image: {path}")
        if img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return img
    
    def _write_image(self, img: np.ndarray, path: str):
        """Write RGB/RGBA numpy array to file"""
        if img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        cv2.imwrite(path, img)
    
    def _video_to_frames(self, video_path: str, output_dir: str) -> Tuple[List[str], float, int, int]:
        """Extract frames from video. Returns (frame_paths, fps, width, height)"""
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        frame_paths = []
        frame_idx = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_path = os.path.join(output_dir, f"frame_{frame_idx:06d}.png")
            cv2.imwrite(frame_path, frame)
            frame_paths.append(frame_path)
            frame_idx += 1
            
            if progress_callback:
                progress_callback(frame_idx / total_frames, f"Extracting frame {frame_idx}/{total_frames}")
        
        cap.release()
        return frame_paths, fps, width, height
    
    def _frames_to_video(self, frame_paths: List[str], output_path: str, fps: float, 
                         width: int, height: int, codec: str = "mp4v"):
        """Combine frames into video"""
        fourcc = cv2.VideoWriter_fourcc(*codec)
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        for i, frame_path in enumerate(frame_paths):
            frame = cv2.imread(frame_path)
            if frame is not None:
                out.write(frame)
            if progress_callback:
                progress_callback(i / len(frame_paths), f"Writing frame {i+1}/{len(frame_paths)}")
        
        out.release()


class MMagicEngine(AIEngineBase):
    """MMEditing/mmagic engine for video/image restoration"""
    
    def __init__(self, config: AIEngineConfig):
        super().__init__(config)
        self._init_args = None
    
    def load_model(self) -> bool:
        try:
            from mmengine.config import Config
            from mmagic.apis import init_model
            
            # mmagic uses config files for models
            model_name = self.config.model
            
            # Map common model names to mmagic configs
            model_configs = {
                "realesrgan-x4": "configs/realesrgan/realesrgan_x4c64b23g32_1xb16-400k_div2k.py",
                "realesrgan-x2": "configs/realesrgan/realesrgan_x2c64b23g32_1xb16-400k_div2k.py",
                "esrgan-x4": "configs/esrgan/esrgan_x4c64b23g32_1xb16-400k_div2k.py",
                "swinir-x4": "configs/swinir/swinir_x4_gan_1xb16-400k_div2k.py",
                "basicvsr-x4": "configs/basicvsr/basicvsr_reds4.py",
                "iconvsr-x4": "configs/iconvsr/iconvsr_reds4.py",
                "realbasicvsr-x4": "configs/realbasicvsr/realbasicvsr_x4.py",
            }
            
            config_path = model_configs.get(model_name, model_name)
            
            # Try to find config in mmagic
            import mmagic
            mmagic_root = os.path.dirname(mmagic.__file__)
            full_config = os.path.join(mmagic_root, config_path)
            
            if not os.path.exists(full_config):
                # Try as relative path
                full_config = config_path
            
            self._model = init_model(full_config, checkpoint=None, device=self._get_device())
            return True
            
        except Exception as e:
            print(f"MMagic load failed: {e}")
            return False
    
    def enhance_image(self, input_path: str, output_path: str) -> ProcessResult:
        try:
            from mmagic.apis import restoration_inference
            
            result = restoration_inference(self._model, input_path)
            result.save(output_path)
            
            return ProcessResult(
                output_path=output_path,
                success=True,
                metadata={"model": self.config.model, "scale": self.config.scale}
            )
        except Exception as e:
            return ProcessResult(output_path="", success=False, error=str(e))
    
    def enhance_video(self, input_path: str, output_path: str, 
                      progress_callback=None) -> ProcessResult:
        try:
            from mmagic.apis import restoration_video_inference
            
            restoration_video_inference(
                self._model, input_path, output_path,
                max_seq_len=100,  # Process in chunks
                progress_callback=progress_callback
            )
            
            return ProcessResult(
                output_path=output_path,
                success=True,
                metadata={"model": self.config.model, "scale": self.config.scale}
            )
        except Exception as e:
            return ProcessResult(output_path="", success=False, error=str(e))
    
    def get_supported_models(self) -> List[str]:
        return [
            "realesrgan-x4", "realesrgan-x2", "esrgan-x4", 
            "swinir-x4", "basicvsr-x4", "iconvsr-x4", "realbasicvsr-x4"
        ]
    
    def get_engine_info(self) -> Dict[str, Any]:
        return {
            "name": "MMagic (OpenMMLab)",
            "version": "1.0",
            "type": "video/image restoration",
            "supports_video": True,
            "supports_image": True,
            "models": self.get_supported_models(),
        }


class RealESRGANEngine(AIEngineBase):
    """Real-ESRGAN engine for image/video super-resolution"""
    
    def __init__(self, config: AIEngineConfig):
        super().__init__(config)
        self._upsampler = None
    
    def load_model(self) -> bool:
        try:
            from realesrgan import RealESRGANer
            from basicsr.archs.rrdbnet_arch import RRDBNet
            
            model_name = self.config.model
            
            # Model configurations
            model_configs = {
                "realesrgan-x4plus": {
                    "model": RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4),
                    "scale": 4,
                    "model_path": "weights/realesrgan-x4plus.pth",
                },
                "realesrgan-x2plus": {
                    "model": RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=2),
                    "scale": 2,
                    "model_path": "weights/realesrgan-x2plus.pth",
                },
                "realesrgan-anime-x4": {
                    "model": RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4),
                    "scale": 4,
                    "model_path": "weights/realesrgan-anime-x4.pth",
                },
                "realesrgan-video-x4": {
                    "model": RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4),
                    "scale": 4,
                    "model_path": "weights/realesrgan-video-x4.pth",
                },
            }
            
            config = model_configs.get(model_name, model_configs["realesrgan-x4plus"])
            
            # Download weights if not exist
            self._ensure_weights(config["model_path"])
            
            self._upsampler = RealESRGANer(
                scale=config["scale"],
                model_path=config["model_path"],
                model=config["model"],
                tile=self.config.tile_size,
                tile_pad=self.config.tile_pad,
                pre_pad=self.config.pre_pad,
                half=not self.config.fp32,
                device=self._get_device(),
            )
            return True
            
        except Exception as e:
            print(f"Real-ESRGAN load failed: {e}")
            return False
    
    def _ensure_weights(self, model_path: str):
        """Download model weights if not present"""
        import os
        import urllib.request
        
        weights_dir = os.path.dirname(model_path)
        os.makedirs(weights_dir, exist_ok=True)
        
        if not os.path.exists(model_path):
            # Download from Real-ESRGAN releases
            base_url = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/"
            filename = os.path.basename(model_path)
            url = base_url + filename
            print(f"Downloading {filename}...")
            urllib.request.urlretrieve(url, model_path)
    
    def enhance_image(self, input_path: str, output_path: str) -> ProcessResult:
        try:
            img = self._read_image(input_path)
            output, _ = self._upsampler.enhance(img, outscale=self.config.scale)
            self._write_image(output, output_path)
            
            return ProcessResult(
                output_path=output_path,
                success=True,
                metadata={"model": self.config.model, "scale": self.config.scale}
            )
        except Exception as e:
            return ProcessResult(output_path="", success=False, error=str(e))
    
    def enhance_video(self, input_path: str, output_path: str, 
                      progress_callback=None) -> ProcessResult:
        try:
            import tempfile
            import shutil
            
            with tempfile.TemporaryDirectory() as tmpdir:
                # Extract frames
                frame_paths, fps, width, height = self._video_to_frames(input_path, tmpdir)
                
                # Process frames
                out_width = width * self.config.scale
                out_height = height * self.config.scale
                out_frames = []
                
                for i, frame_path in enumerate(frame_paths):
                    img = self._read_image(frame_path)
                    output, _ = self._upsampler.enhance(img, outscale=self.config.scale)
                    out_frame_path = os.path.join(tmpdir, f"out_{i:06d}.png")
                    self._write_image(output, out_frame_path)
                    out_frames.append(out_frame_path)
                    
                    if progress_callback:
                        progress_callback(i / len(frame_paths), f"Processing frame {i+1}/{len(frame_paths)}")
                
                # Write video
                self._frames_to_video(out_frames, output_path, fps, out_width, out_height)
            
            return ProcessResult(
                output_path=output_path,
                success=True,
                metadata={"model": self.config.model, "scale": self.config.scale}
            )
        except Exception as e:
            return ProcessResult(output_path="", success=False, error=str(e))
    
    def get_supported_models(self) -> List[str]:
        return [
            "realesrgan-x4plus", "realesrgan-x2plus",
            "realesrgan-anime-x4", "realesrgan-video-x4"
        ]
    
    def get_engine_info(self) -> Dict[str, Any]:
        return {
            "name": "Real-ESRGAN",
            "version": "1.0",
            "type": "super-resolution",
            "supports_video": True,
            "supports_image": True,
            "models": self.get_supported_models(),
        }


class AIEngineFactory:
    """Factory for creating AI engines"""
    
    _engines = {
        "mmagic": MMagicEngine,
        "realesrgan": RealESRGANEngine,
    }
    
    @classmethod
    def create(cls, engine_name: str, config: AIEngineConfig) -> AIEngineBase:
        engine_name = engine_name.lower()
        if engine_name not in cls._engines:
            raise ValueError(f"Unknown AI engine: {engine_name}. Available: {list(cls._engines.keys())}")
        return cls._engines[engine_name](config)
    
    @classmethod
    def get_available_engines(cls) -> List[str]:
        return list(cls._engines.keys())
    
    @classmethod
    def register(cls, name: str, engine_class: type):
        cls._engines[name.lower()] = engine_class


def get_ai_engine(engine: str, model: str = "realesrgan-x4plus", 
                  scale: int = 4, **kwargs) -> AIEngineBase:
    """Convenience function to create AI engine"""
    config = AIEngineConfig(
        name=engine,
        model=model,
        scale=scale,
        **kwargs
    )
    return AIEngineFactory.create(engine, config)