"""Download public assets for CPU wake-word training."""
from pathlib import Path
import requests
ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets'
ASSETS.mkdir(exist_ok=True)
FILES = {
 'voice.onnx': 'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx',
 'voice.onnx.json': 'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx.json',
 'melspectrogram.onnx': 'https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/melspectrogram.onnx',
 'embedding_model.onnx': 'https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/embedding_model.onnx',
 'negative_features.npy': 'https://huggingface.co/datasets/davidscripka/openwakeword_features/resolve/main/validation_set_features.npy',
}
for name, url in FILES.items():
 target = ASSETS / name
 if target.exists():
  print('Cached', name, flush=True)
  continue
 print('Downloading', name, flush=True)
 with requests.get(url, stream=True, timeout=(30,120)) as response:
  response.raise_for_status()
  with target.with_suffix(target.suffix + '.part').open('wb') as out:
   for chunk in response.iter_content(1024*1024):
    out.write(chunk)
 target.with_suffix(target.suffix + '.part').replace(target)
 print('Saved', name, target.stat().st_size, flush=True)
