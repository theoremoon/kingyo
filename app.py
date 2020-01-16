import cv2
import kingyo_learn.kingyo_v2 as K
from flask import Flask, Response, request, jsonify
from flask_cors import CORS
from datetime import datetime
import json
import requests
import threading
import os
import time
import sys
import bisect

if __name__ != '__main__':
    print("[!] this should be used as main")
    exit()

# motor server
MOTOR_SERVER='http://motor.example.com'

# initialize camera at launch
if len(sys.argv) > 1:
    MOTOR_SERVER = "http://" + sys.argv[1] + "/"
    video = cv2.VideoCapture("http://" + sys.argv[1] + ":8080/?action=stream")
else:
    video = cv2.VideoCapture(0)
# video.set(cv2.CAP_PROP_FPS, 30)
frame = None
frame_id = 0
MAX_FRAME_COUNT = 10000
recent_timestamp = []
recent_frameid = []
recent_frame = []

# kingyo_list
kingyos = []
kingyo_frame = None
kingyo_id = 0

def get_frame():
    global frame, frame_id, kingyo_frame, recent_frame, recent_timestamp, recent_frameid
    while True:
        ok, img = video.read()
        if not ok:
            return

        img = cv2.flip(img, 0)

        kingyo_img = K.learnFrame(img, frame_id)
        recent_timestamp.append(datetime.now().timestamp())
        recent_frame.append(img)
        recent_frameid.append(frame_id)
        if len(recent_timestamp) >= MAX_FRAME_COUNT:
            recent_timestamp = recent_timestamp[:MAX_FRAME_COUNT]
            recent_frameid = recent_frameid[:MAX_FRAME_COUNT]
            recent_frame = recent_frame[:MAX_FRAME_COUNT]

        frame_id += 1

        ok, jpg = cv2.imencode(".jpg", img)
        if not ok:
            return
        frame = jpg.tobytes()

        ok, kingyo_jpg = cv2.imencode(".jpg", kingyo_img)
        if not ok:
            return
        kingyo_frame = kingyo_jpg.tobytes()


app = Flask(__name__)
CORS(app)

def generateFrames():
    while True:
        time.sleep(0.5)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/camera.mjpeg')
def video_feed():
    return Response(generateFrames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def generateKingyoFrames():
    while True:
        time.sleep(0.5)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + kingyo_frame + b'\r\n\r\n')

@app.route('/streaming.mjpeg')
def kingyo_feed():
    return Response(generateKingyoFrames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/camera-move', methods=['POST'])
def camera_move():
    req = request.json
    r = requests.post(os.path.join(MOTOR_SERVER + "camera-move"), data=json.dumps(req), headers={'Content-Type': 'application/json'})
    return r.text

@app.route('/')
def index():
    return '<img src="/camera.mjpeg" />'

@app.route('/kingyo')
def kingyo():
    return '<img src="/streaming.mjpeg" />'


@app.route('/kingyo-register', methods=['POST'])
def kingyo_register():
    global kingyos, kingyo_id

    j = request.json
    t = j["timestamp"]

    kingyo = j["kingyo"]

    index = bisect.bisect_left(recent_timestamp, t)
    frame_id = recent_frameid[index]
    kingyos.append({
        "name": kingyo["name"],
        "id": kingyo_id,
    })
    kingyo_id += 1
    cv2.imwrite("kingyo.png", recent_frame[index])
    K.nameNewKingyo(kingyo["name"], frame_id, [kingyo["x"], kingyo["y"]])
    return ""

@app.route('/kingyo-rename', methods=['POST'])
def kingyo_rename():
    j = request.json
    t = j["timestamp"]

    kingyo = j["info"]

    index = bisect.bisect_left(recent_timestamp, t)
    frame_id = recent_frameid[index]
    K.renameKingyo(kingyo["name"], frame_id, [kingyo["x"], kingyo["y"]])
    return ""

@app.route('/all-kingyo-list')
def all_kingyo_list():
    return jsonify(sorted(kingyos, key=lambda x: x["id"]))


threading.Thread(target=get_frame).start()
app.run(port=os.environ.get("PORT", 5000))
