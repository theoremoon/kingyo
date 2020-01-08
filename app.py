import cv2
from flask import Flask, Response, request
import json
import requests
import threading
import os
import time

if __name__ != '__main__':
    print("[!] this should be used as main")
    exit()

# motor server
MOTOR_SERVER='http://motor.example.com/'

# initialize camera at launch
video = cv2.VideoCapture(0)
video.set(cv2.CAP_PROP_FPS, 10)
frame = None

# for face detection TODO: Replate face detection to kingyo detection
face_img = None
cascade_path = "haarcascade_frontalface_alt.xml"
cascade = cv2.CascadeClassifier(cascade_path)

def get_frame():
    global frame
    while True:
        ok, img = video.read()
        if not ok:
            return
        ok, jpg = cv2.imencode(".jpg", img)
        if not ok:
            return
        frame = jpg.tobytes()

        threading.Thread(target=face_detect, args=[img]).start()

def face_detect(img):
    global face_img
    grayscale_img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    front_face_list = cascade.detectMultiScale(grayscale_img, minSize = (100, 100))

    for (x,y,w,h) in front_face_list:
        cv2.rectangle(img, (x,y), (x+w, y+h), (0, 0, 255), thickness=10)
    ok, jpg = cv2.imencode(".jpg", img)
    face_img = jpg.tobytes()

app = Flask(__name__)

def generateFrames():
    while True:
        time.sleep(0.5)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/streaming.mjpeg')
def video_feed():
    return Response(generateFrames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def generateFaceFrames():
    while True:
        time.sleep(0.5)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + face_img + b'\r\n\r\n')

@app.route('/face.mjpeg')
def face_feed():
    return Response(generateFaceFrames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/camera-move', methods=['POST'])
def camera_move():
    req = request.json()
    requests.post(MOTOR_SERVER + "/camera_move", data=json.dumps(req))

@app.route('/')
def index():
    return '<img src="/streaming.mjpeg" />'

@app.route('/face')
def face():
    return '<img src="/face.mjpeg" />'


threading.Thread(target=get_frame).start()
app.run(port=os.environ.get("PORT", 5000))
