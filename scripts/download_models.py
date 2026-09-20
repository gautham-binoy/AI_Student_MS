"""
AI Attendance & Engagement Analyzer — Model Download Helper
Downloads required face detection and recognition weights to the local models/ directory.
"""

import os
import urllib.request

MODELS = {
    "models/yolov8n-face.pt": "https://huggingface.co/arnabdhar/YOLOv8-Face-Detection/resolve/main/model.pt"
}


def download_models():
    os.makedirs("models", exist_ok=True)
    for target_path, url in MODELS.items():
        if os.path.exists(target_path):
            print(f"Model already exists at: {target_path}")
            continue

        print(f"Downloading {target_path} from {url}...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as resp, open(target_path, "wb") as f:
                f.write(resp.read())
            print(f"Successfully downloaded {target_path} ({os.path.getsize(target_path)} bytes)")
        except Exception as e:
            print(f"Failed to download {target_path}: {e}")

    # Also trigger facenet-pytorch model caching
    try:
        print("Checking FaceNet InceptionResnetV1 weights...")
        from facenet_pytorch import InceptionResnetV1
        InceptionResnetV1(pretrained="vggface2").eval()
        print("FaceNet weights are cached and ready.")
    except Exception as e:
        print(f"FaceNet setup note: {e}")


if __name__ == "__main__":
    download_models()
