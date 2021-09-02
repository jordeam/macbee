from flask import Flask, render_template, Response, request, redirect, url_for
from ..url_for2 import url_for2

from flask_login import login_required, current_user
import cv2
import datetime, time
import os, sys
import numpy as np
from threading import Thread
from . import cam
from itertools import count

capture = False
grey = False
neg = False
camera_on = False
rec = False

camera_device = 0

#make shots directory to save pics
try:
    os.mkdir('./shots')
except OSError as error:
    pass

#make videos directory to save videos
try:
    os.mkdir('./videos')
except OSError as error:
    pass

def cam_record():
    global rec, rec_frame, rec_status, camera, camera_on
    rec = True

    print('Openning VideoCapture inside the thread')
    if not camera_on:
        camera = cv2.VideoCapture(camera_device)

    # Check if camera opened successfully
    while not camera.isOpened():
        print(f'Unable to read camera feed camera={camera}')
        if not rec:
            # cv2.destroyAllWindows()
            return

    # get a valid frame to determine properties
    for i in count(1):
        print(f'Trying to read (i={i})...')
        ret, _ = camera.read()
        if ret:
            break
        if not rec:
            return

    # Default resolutions of the frame are obtained.The default resolutions are system dependent.
    # We convert the resolutions from float to integer.
    frame_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_rate = int(camera.get(cv2.CAP_PROP_FPS))
    print(f'frame_rate={frame_rate}, frame_width={frame_width}, frame_height={frame_height}')
    # Define the codec and create VideoWriter object. The output is stored in 'outpy.avi' file.
    now = datetime.datetime.now()
    out = cv2.VideoWriter('videos/vid_{}.avi'.format(str(now).replace(":",'')), cv2.VideoWriter_fourcc('M','J','P','G'), 16, (frame_width, frame_height))

    while True:
      rec_status, rec_frame = camera.read()
      if rec_status:
        # Write the frame into the file 'output.avi'
        out.write(rec_frame)
        if not rec:
          break
    # When everything is done, release the video capture and video write objects
    if not camera_on:
        camera.release()
    out.release()

def gen_frames():  # generate frame by frame from camera
    global out, capture, rec_frame
    while rec or camera_on:
        if not rec:
            success, frame = camera.read()
            if success:
                if grey:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if neg:
                    frame = cv2.bitwise_not(frame)
                if capture:
                    capture = False
                    now = datetime.datetime.now()
                    p = os.path.sep.join(['shots', "shot_{}.png".format(str(now).replace(":",''))])
                    cv2.imwrite(p, frame)
                try:
                    _, buffer = cv2.imencode('.jpg', cv2.flip(frame,1))
                    frame = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                except Exception as e:
                    pass
        else:
            try:
                _, buffer = cv2.imencode('.jpg', rec_frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            except Exception as e:
                pass

@cam.route('/macbee/camera')
@cam.route('/camera')
@login_required
def index():
    return render_template('camera/camera.html', camera_on = camera_on, neg = neg, grey = grey, rec=rec, url_for2=url_for2)

@cam.route('/video_feed')
@login_required
def video_feed():
    if camera_on or rec:
        return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return redirect(url_for2('.index'))

@cam.route('/macbee/cam_requests',methods=['POST','GET'])
@cam.route('/cam_requests',methods=['POST','GET'])
@login_required
def tasks():
    global camera_on,camera, capture, grey, neg, rec
    print('Entering cam_requests')
    if request.method == 'POST':
        if request.form.get('click'):
            capture = True
        elif  request.form.get('color'):
            grey = False
        elif  request.form.get('grey'):
            grey = True
        elif  request.form.get('pos'):
            neg = False
        elif  request.form.get('neg'):
            neg = True
        elif  request.form.get('start'):
            if not camera_on and not rec:
                camera = cv2.VideoCapture(camera_device)
            camera_on = True
        elif  request.form.get('stop'):
            if camera_on and not rec:
                camera.release()
            camera_on = False
            # cv2.destroyAllWindows()
        elif request.form.get('rec_start'):
            # if camera_on:
            #     camera.release()
            #     camera_on = False
            if not rec:
                #Start new thread for recording the video
                th = Thread(target = cam_record)
                th.start()
                time.sleep(1)
        elif request.form.get('rec_stop'):
            if rec:
                rec = False
                time.sleep(1)
    print('Leaving cam_requests')
    return redirect('macbee/camera')
    # return redirect(url_for2('.index'))

