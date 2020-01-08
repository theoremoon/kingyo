import cv2
from flask import Flask, Response
import threading
import os
import time

if __name__ != '__main__':
    print("[!] this should be used as main")
    exit()


# initialize camera at launch
video = cv2.VideoCapture(0)
video.set(cv2.CAP_PROP_FPS, 10)
frame = None

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

@app.route('/')
def index():
    return '<img src="/streaming.mjpeg" />'


threading.Thread(target=get_frame).start()
app.run(port=os.environ.get("PORT", 5000))
