from flask import Flask, render_template, Response, request, redirect, url_for, send_file
# from ..url_for2 import url_for2

from flask_login import login_required, current_user
import cv2
import datetime, time
import os, sys
import numpy as np
from threading import Thread
from . import cam
from itertools import count
import glob, re

gpio_ok = True

try:
    import RPi.GPIO as GPIO
except:
    gpio_ok = False

if gpio_ok:
    print('GPIO support OK!')
else:
    print('WARNING: GPIO in failsafe mode')

capture = False
grey = False
neg = False
camera_on = False
rec = False

verbose = True

# LEDs state
leds_status = [False, False, False, False]
led_labels = { 'led1' : 0, 'led2' : 1, 'led3' : 2, 'led4' : 3}

gpio_led1 = 18
gpio_led2 = 23
gpio_led3 = 24
gpio_led4 = 25
gpio_pins = [gpio_led1, gpio_led2, gpio_led3, gpio_led4]

camera_device = 0

if gpio_ok:
    # Set up GPIO pins
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in gpio_pins:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin,0)

def led_set(led, on):
    if verbose:
        print(f'led_set: LED{led + 1} ' + ('ON' if on else 'OFF'))
    leds_status[led] = True if on else False
    if gpio_ok:
        GPIO.output(gpio_pins[led], on)

# not used anywhere
def turn_leds_off():
    for led in range(4):
        led_set(led, 0)

# not used anywhere
def turn_leds_on():
    for led in range(4):
        led_set(led, leds_status[led])


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
    out = cv2.VideoWriter('videos/vid_{}.avi'.format(str(now).replace(":",'')), cv2.VideoWriter_fourcc('M','J','P','G'), 20, (frame_width, frame_height))

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

@cam.route('/camera')
@login_required
def index():
    global camera_on, neg, grey, rec, leds_status
    return render_template('camera/camera.html', camera_on = camera_on, neg = neg, grey = grey, rec = rec, led1 = leds_status[0], led2 = leds_status[1], led3 = leds_status[2], led4 = leds_status[3])

@cam.route('/video_feed')
@login_required
def video_feed():
    if camera_on or rec:
        return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return redirect(url_for('.index'))

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
        elif request.form.get('rec_start'):
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
    return redirect(url_for('.index'))

@cam.route('/tabela',methods=['POST','GET'])
def tabela():
    return render_template('camera/tabela.html')

@cam.route('/files',methods=['POST','GET'])
@login_required
def files():
    fns = glob.glob('videos/*.avi')
    if fns != []:
        fns = list(map(lambda x: x.lstrip('videos').lstrip('/'), fns))
        dates = list(map(lambda x: re.search(r'[0-9]+-[0-9]+-[0-9]+', x).group(0), fns))
        times = list(map(lambda x: re.search(r' [0-9]+\.[0-9]+.avi$', x).group(0).lstrip().rstrip('.avi'), fns))
        d = list(map(lambda x, y, z: list([x, y, z]), fns, dates, times))
    else:
        d = []
    return render_template('camera/files.html', data = d)

@cam.route('/file_action',methods=['POST'])
@login_required
def file_action():
    if request.form.get('download'):
        print('download')
        fn = 'vid_{} {}.avi'.format(request.form.get('date'), request.form.get('time'))
        print(f'fn={fn} getenv("PWD")={os.getenv("PWD")}')
        try:
            return send_file('../videos/' + fn)
        except Exception as e:
            print(str(e))
    if request.form.get('erase'):
        fn = 'videos/vid_{} {}.avi'.format(request.form.get('date'), request.form.get('time'))
        print('erase')
        print(f'fn={fn}')
        os.unlink(fn)
    return redirect(url_for('cam.files'))

@cam.route('/set_led/<string:led>/<int:on>', methods=['GET'])
@login_required
def set_led(led, on):
    n = led_labels[led]
    led_set(n, on)
    return str(on)

@cam.route('/get_led/<string:led>', methods=['GET'])
@login_required
def get_led(led):
    n = led_labels[led]
    return str('1' if leds_status[led_labels[led]] else '0')

@cam.route('/set_leds', methods = ['POST'])
@login_required
def set_leds():
    for led in led_labels:
        if request.form.get(led):
            led_set(led_labels[led], 1)
        else:
            led_set(led_labels[led], 0)
    return redirect(url_for('cam.index'))

