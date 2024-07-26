from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.models import load_model
from imutils.video import VideoStream
import numpy as np
import imutils
import time
import cv2
import requests
from threading import Thread, Event
from playsound import playsound

def detect_and_predict_mask(frame, faceNet, maskNet):
    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1.0, (224, 224),
                                 (104.0, 177.0, 123.0))

    faceNet.setInput(blob)
    detections = faceNet.forward()

    faces = []
    locs = []
    preds = []

    for i in range(0, detections.shape[2]):
        confidence = detections[0, 0, i, 2]

        if confidence > 0.5:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")

            (startX, startY) = (max(0, startX), max(0, startY))
            (endX, endY) = (min(w - 1, endX), min(h - 1, endY))

            face = frame[startY:endY, startX:endX]
            face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
            face = cv2.resize(face, (224, 224))
            face = img_to_array(face)
            face = preprocess_input(face)

            faces.append(face)
            locs.append((startX, startY, endX, endY))

    if len(faces) > 0:
        faces = np.array(faces, dtype="float32")
        preds = maskNet.predict(faces, batch_size=32)

    return (locs, preds)

def play_warning_sound(sound_event):
    while True:
        sound_event.wait()  # Menunggu hingga ada sinyal untuk memainkan suara
        playsound('alarm.mp3')

prototxtPath = r"face_detector/deploy.prototxt"
weightsPath = r"face_detector/res10_300x300_ssd_iter_140000.caffemodel"
faceNet = cv2.dnn.readNet(prototxtPath, weightsPath)

maskNet = load_model("mask_detector.model")

print("[INFO] starting video stream...")
vs = VideoStream(src=0).start()
time.sleep(2.0)

server_url = "http://127.0.0.1:5000/"

# Menggunakan Event untuk mengontrol sound thread
sound_event = Event()
sound_thread = Thread(target=play_warning_sound, args=(sound_event,))
sound_thread.daemon = True
sound_thread.start()

alarm_playing = False

while True:
    frame = vs.read()
    frame = imutils.resize(frame, width=800)

    (locs, preds) = detect_and_predict_mask(frame, faceNet, maskNet)

    try:
        sensor_data = requests.get(server_url).json()
    except requests.exceptions.RequestException as e:
        sensor_data = {}
        print(f"[ERROR] {e}")

    temperature = sensor_data.get('temperature', 'N/A')
    humidity = sensor_data.get('humidity', 'N/A')
    air_quality = sensor_data.get('air_quality', 'N/A')

    sensor_text = f"Temp: {temperature} C, Humidity: {humidity} %, Air Quality: {air_quality}"
    warning_texts = []

    if temperature != 'N/A':
        if temperature < 23.0:
            warning_texts.append("Suhu rendah")
        elif temperature > 35.0:
            warning_texts.append("Suhu tinggi")

    if humidity != 'N/A':
        if humidity < 50.0:
            warning_texts.append("Kelembapan udara rendah")
        elif humidity > 88.0:
            warning_texts.append("Kelembapan udara tinggi")

    if air_quality != 'N/A' and air_quality >= 100:
        warning_texts.append("Kualitas udara buruk")

    show_mask_warning = False
    show_specific_warning = False

    for (box, pred) in zip(locs, preds):
        (startX, startY, endX, endY) = box
        (mask, withoutMask) = pred

        label = "Mask" if mask > withoutMask else "No Mask"
        color = (0, 255, 0) if label == "Mask" else (0, 0, 255)
        label = "{}: {:.2f}%".format(label, max(mask, withoutMask) * 100)

        cv2.putText(frame, label, (startX, startY - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
        cv2.rectangle(frame, (startX, startY), (endX, endY), color, 2)

        if label.startswith("No Mask"):
            show_mask_warning = True

    cv2.putText(frame, sensor_text, (10, frame.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

    y_offset = 30
    for warning_text in warning_texts:
        cv2.putText(frame, warning_text, (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
        y_offset += 30

        if warning_text in ["Suhu rendah", "Suhu tinggi", "Kelembapan udara rendah", "Kelembapan udara tinggi", "Kualitas udara buruk"]:
            show_specific_warning = True

    # Mengatur event sound berdasarkan kondisi peringatan masker
    if show_specific_warning and show_mask_warning:
        cv2.putText(frame, "Harap menggunakan masker", (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
        if not alarm_playing:
            sound_event.set()  # Aktifkan suara
            alarm_playing = True
    else:
        sound_event.clear()  # Matikan suara
        alarm_playing = False

    cv2.namedWindow("Frame", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Frame", 800, 450)

    cv2.imshow("Frame", frame)
    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

sound_event.clear()  # Pastikan suara mati saat keluar dari loop
sound_thread.join(timeout=1)

cv2.destroyAllWindows()
vs.stop()
