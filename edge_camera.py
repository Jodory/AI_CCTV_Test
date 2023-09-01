#import onnx
import numpy as np
import time
from cv2 import *  
import cv2
import matplotlib.pyplot as plt
from datetime import datetime
import requests
import threading
import subprocess
#from ultralytics import YOLO

def send_frame(url, frame, timeData):
    _, img_encoded = cv2.imencode(".jpg", frame)
    requests.post(url, data={'time': timeData, 'cameraID': cameraID}, files={'frame': ('image.jpg', img_encoded, 'image/jpeg')})

def send_original(frame, timeData):
    OriginFrame = frame.copy()
    OriginURL = "http://bangwol08.iptime.org:20002/camera/original"
    _, img_encoded = cv2.imencode(".jpg", OriginFrame)
    requests.post(OriginURL, data={'time': timeData, 'cameraID': cameraID},
                  files={'frame': ('image.jpg', img_encoded, 'image/jpeg')})
    # cv2.imwrite(f'camera/esqure_01/original/{timeData}.jpg', frame)

def send_process(frame, timeData, face_detector, count, tick, constancy, instability):
            global person, process_thread_is_running
            channels = 1 if len(frame.shape) == 2 else frame.shape[2]
            if channels == 1:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            if channels == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            height, width, _ = frame.shape
            face_detector.setInputSize((width, height))
            i = 0
            _, results = face_detector.detect(frame)
            for det in (results if results is not None else []):
                i = i + 1
            if person == i:
                instability += 1
                if instability > 9:
                    i = 0
            if person != i:
                count = 6
                if person > i:
                    tick = 1
                    constancy = person
                    face_detector.setScoreThreshold(0.3)
                    _, results = face_detector.detect(frame)
            person = i
            if count == 6:
                count = count - 1
            elif count > 0:
                count = count - 1
            else:
                constancy = 0
            if i >= constancy and tick == 1:
                tick = 0
                face_detector.setScoreThreshold(0.7)
            output = frame.copy()
            for det in (results if results is not None else []):
                bbox = list(map(int, det[:4]))
                for i in range(len(bbox)):
                    if bbox[i] < 0: 
                        bbox[i] = 0
                start_x, start_y, end_x, end_y = bbox
                region = output[start_y:start_y + end_y, start_x:start_x + end_x]
                height, width = region.shape[:2]
                w = int(width * 0.05)
                h = int(height * 0.05)
                if w <= 0: w = 1
                if h <= 0: h = 1
                small = cv2.resize(region, (w, h), interpolation=cv2.INTER_AREA)
                mosaic = cv2.resize(small, (width, height), interpolation=cv2.INTER_NEAREST)
            
                img_mosaic = output.copy()
                img_mosaic[start_y:start_y + end_y, start_x:start_x + end_x] = mosaic
                output = img_mosaic
            frame = output

            ProURL = "http://bangwol08.iptime.org:20002/camera/process"

            _, img_encoded = cv2.imencode(".jpg", frame)
            requests.post(ProURL, data={'time': timeData, 'cameraID': cameraID},
                          files={'frame': ('image.jpg', img_encoded, 'image/jpeg')})
            # cv2.imwrite(f'camera/esqure_01/process/{timeData}.jpg', output)
            process_thread_is_running = False

if __name__ == '__main__':
    # load model
    face_detector = cv2.FaceDetectorYN.create("face_detection_yunet_2023mar.onnx", "", (320, 320))    
    # face_detector = cv2.FaceDetectorYN.create(model="face_detection_yunet_2023mar.onnx", config="", input_size=(320, 320), backend_id=3, target_id=0)
    # Camera
    cap = cv2.VideoCapture(0) 
    if not cap.isOpened():
        print('Error: Camera is not open.')
        exit()
    
    # if Camera is open --> Start to send original / process frame
    while cap.isOpened():
        # camera Id
        cameraID = 'esqure_01'
        deviceId = 0
        person = 0
        count = 0
        tick = 0
        constancy = 0
        instability = 0
        
        process_thread_is_running = False
        while cv2.waitKey(1) < 0:
            hasFrame, frame = cap.read()
            if not hasFrame:
                break
            timeData = time.time()
            send_original_thread = threading.Thread(target=send_original, args=(frame, timeData))
            send_process_thread = threading.Thread(target=send_process, args=(frame, timeData, face_detector, count, tick, constancy, instability))

            send_original_thread.start()
            # if send_process_thread is running --> pass
            if not process_thread_is_running:
                process_thread_is_running = True
                send_process_thread.start()
        cap.release()
        

