import os
import pandas as pd
from ultralytics import YOLO

# Load the lightweight YOLOv8 nano model
model = YOLO('yolov8n.pt')

def detect_and_classify(image_path):
    results = model(image_path)
    detections = results[0].boxes.data.tolist() # [x1, y1, x2, y2, conf, class_id]
    
    # YOLOv8 default classes: 0 = person, 39 = bottle, 41 = cup (common for containers)
    has_person = any(int(d[5]) == 0 for d in detections)
    has_product = any(int(d[5]) in [39, 41] for d in detections)
    
    # Classification Logic
    if has_person and has_product:
        return "promotional", detections
    elif has_product:
        return "product_display", detections
    elif has_person:
        return "lifestyle", detections
    else:
        return "other", detections

# Process images and save to CSV
data = []
image_root = 'data/raw/images/'

for channel in os.listdir(image_root):
    channel_path = os.path.join(image_root, channel)
    for img_name in os.listdir(channel_path):
        msg_id = img_name.split('.')[0]
        img_path = os.path.join(channel_path, img_name)
        
        category, raw_hits = detect_and_classify(img_path)
        
        for hit in raw_hits:
            data.append({
                "message_id": msg_id,
                "channel_name": channel,
                "detected_class": model.names[int(hit[5])],
                "confidence_score": hit[4],
                "image_category": category
            })

pd.DataFrame(data).to_csv('medical_warehouse/seeds/yolo_detections.csv', index=False)