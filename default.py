#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Source: https://github.com/RyanMelenaNoesis/XbmcSecurityCamOverlayAddOn"
# and kodi forum discussion: https://forum.kodi.tv/showthread.php?tid=182540
#
# JSONRPC Call to trigger this script:
#
# curl -s -u <user>:<password> -H "Content-Type: application/json" -X POST -d '{"jsonrpc":"2.0","method":"Addons.ExecuteAddon","params":{"addonid":"script.securitycam"},"id":1}' http://<ip>:<port>/jsonrpc
#

# Import the modules
import os, time, random, string, sys, platform
import xbmc, xbmcaddon, xbmcgui, xbmcvfs
import urllib2, requests, subprocess
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
from threading import Thread

# Constants
ACTION_PREVIOUS_MENU = 10
ACTION_BACKSPACE = 110
ACTION_NAV_BACK = 92

MAXCAMS = 4

# Set plugin variables
__addon__        = xbmcaddon.Addon()
__addon_id__     = __addon__.getAddonInfo('id')
__addon_path__   = __addon__.getAddonInfo('path')
__profile__      = __addon__.getAddonInfo('profile')
__icon__         = os.path.join(__addon_path__, 'icon.png')
__loading__      = os.path.join(__addon_path__, 'loading.gif')

# Get settings
active     = [False] * MAXCAMS

name       = [None] * MAXCAMS
urls       = [None] * MAXCAMS
usernames  = [None] * MAXCAMS
passwords  = [None] * MAXCAMS

streamid   = 0
requestType = "display" # display, motion
cameraUrl = None
cameraName = None
cameraUsername = None
cameraPassword = None
camera1 = None
camera2 = None
camera3 = None
camera4 = None

ffmpeg_exec = 'ffmpeg.exe' if platform.system() == 'Windows' else 'ffmpeg'

if len(sys.argv) > 1:
    for i in range (1, len(sys.argv)):
        try:
            if sys.argv[i].split('=')[0] == 'streamid':
                streamid = int(sys.argv[i].split('=')[1])
            if sys.argv[i].split('=')[0] == 'requestType':
                requestType = str(sys.argv[i].split('=')[1])
            if sys.argv[i].split('=')[0] == 'cameraURL':
                cameraUrl = str(sys.argv[i].split('=')[1])
            if sys.argv[i].split('=')[0] == 'cameraName':
                cameraName = str(sys.argv[i].split('=')[1])
            if sys.argv[i].split('=')[0] == 'cameraUsername':
                cameraUsername = str(sys.argv[i].split('=')[1])
            if sys.argv[i].split('=')[0] == 'cameraPassword':
                cameraPassword = str(sys.argv[i].split('=')[1])
            if sys.argv[i].split('=')[0] == 'camera1':
                camera1 = str(sys.argv[i].split('=')[1])                
            if sys.argv[i].split('=')[0] == 'camera2':
                camera2 = str(sys.argv[i].split('=')[1])
            if sys.argv[i].split('=')[0] == 'camera3':
                camera3 = str(sys.argv[i].split('=')[1])
            if sys.argv[i].split('=')[0] == 'camera4':
                camera4 = str(sys.argv[i].split('=')[1])                 
                # break here, or keep on searching for other arguments
        except:
            continue

if streamid in range(1, MAXCAMS + 1) and __addon__.getSetting('url{:d}'.format(streamid)):
    name[0] = __addon__.getSetting('name{:d}'.format(streamid))
    urls[0] = __addon__.getSetting('url{:d}'.format(streamid))
    usernames[0] = __addon__.getSetting('username{:d}'.format(streamid))
    passwords[0] = __addon__.getSetting('password{:d}'.format(streamid))
elif cameraUrl != None and cameraName != None:
    name[0] = cameraName
    urls[0] = cameraUrl
    usernames[0] = cameraUsername
    passwords[0] = cameraPassword
elif camera1 != None:
    if camera1 != None:
        name[0] = None
        urls[0] = camera1
        usernames[0] = cameraUsername
        passwords[0] = cameraPassword
    if camera2 != None:
        name[1] = None
        urls[1] = camera2
        usernames[1] = cameraUsername
        passwords[1] = cameraPassword
    if camera3 != None:
        name[2] = None
        urls[2] = camera3
        usernames[2] = cameraUsername
        passwords[2] = cameraPassword
    if camera4 != None:
        name[3] = None
        urls[3] = camera4
        usernames[3] = cameraUsername
        passwords[3] = cameraPassword
else:
    count = 0
    for i in range(MAXCAMS):
        active[i] = bool(__addon__.getSetting('active{:d}'.format(i + 1)) == 'true')
        if active[i]:
            name[count] = __addon__.getSetting('name{:d}'.format(i + 1))
            urls[count] = __addon__.getSetting('url{:d}'.format(i + 1))
            usernames[count] = __addon__.getSetting('username{:d}'.format(i + 1))
            passwords[count] = __addon__.getSetting('password{:d}'.format(i + 1))
            count += 1

_width       = int(float(__addon__.getSetting('width')))
_height      = int(float(__addon__.getSetting('height')))
_interval    = int(float(__addon__.getSetting('interval')))
_autoClose   = bool(__addon__.getSetting('autoClose') == 'true')
_duration    = int(float(__addon__.getSetting('duration')) * 1000)
_alignment   = int(float(__addon__.getSetting('alignment')))
_padding     = int(float(__addon__.getSetting('padding')))
_animate     = bool(__addon__.getSetting('animate') == 'true')
_aspectRatio = int(float(__addon__.getSetting('aspectRatio')))

# Utils
def log(message,loglevel=xbmc.LOGNOTICE):
    xbmc.log(msg='[{}] {}'.format(__addon_id__, message), level=loglevel)

def which(pgm):
    for path in os.getenv('PATH').split(os.path.pathsep):
        p=os.path.join(path, pgm)
        if os.path.exists(p) and os.access(p, os.X_OK):
            return p

    return None

# Auth Scheme Mapping for Requets
AUTH_MAP = {
    'basic': HTTPBasicAuth,
    'digest': HTTPDigestAuth,
}

def auth_get(url, *args, **kwargs):
    r = requests.get(url, **kwargs)

    if r.status_code != 401:
        return r

    auth_scheme = r.headers['WWW-Authenticate'].split(' ')[0]
    auth = AUTH_MAP.get(auth_scheme.lower())

    if not auth:
        raise ValueError('Unknown authentication scheme')

    r = requests.get(url, auth=auth(*args), **kwargs)

    return r

# Classes
class CamPreviewDialog(xbmcgui.WindowDialog):
    def __init__(self, name, urls, usernames, passwords):
        self.cams = [{'name':None, 'url':None, 'username':None, 'password':None, 'tmpdir':None, 'control':None} for i in range(MAXCAMS)]

        passwd_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        self.opener = urllib2.build_opener()

        for i in range(MAXCAMS):
            if urls[i]:
                self.cams[i]['name'] = name[i]
                self.cams[i]['url'] = urls[i]

                if usernames[i] and passwords[i]:
                    self.cams[i]['username'] = usernames[i]
                    self.cams[i]['password'] = passwords[i]

                    passwd_mgr.add_password(None, self.cams[i]['url'], self.cams[i]['username'], self.cams[i]['password'])
                    self.opener.add_handler(urllib2.HTTPBasicAuthHandler(passwd_mgr))
                    self.opener.add_handler(urllib2.HTTPDigestAuthHandler(passwd_mgr))

                randomname = ''.join([random.choice(string.ascii_letters + string.digits) for n in xrange(32)])
                self.cams[i]['tmpdir'] = os.path.join(__profile__, randomname)
                if not xbmcvfs.exists(self.cams[i]['tmpdir']):
                    xbmcvfs.mkdir(self.cams[i]['tmpdir'])

                x, y, w, h = self.coordinates(i)
                self.cams[i]['control'] = xbmcgui.ControlImage(x, y, w, h, __loading__, aspectRatio = _aspectRatio)
                self.addControl(self.cams[i]['control'])
                
                if _animate:
                    if _alignment in [0, 4, 6, 8, 9, 10]:
                        direction = 1
                    else:
                        direction = -1
                    self.cams[i]['control'].setAnimations([('WindowOpen', 'effect=slide start=%d time=1000 tween=cubic easing=in'%(w*direction),), ('WindowClose', 'effect=slide end=%d time=1000 tween=cubic easing=in'%(w*direction),)])

    def coordinates(self, position):
        COORD_GRID_WIDTH = 1280
        COORD_GRID_HEIGHT = 720

        scaledWidth = int(float(COORD_GRID_WIDTH) / self.getWidth() * _width)
        scaledHeight = int(float(COORD_GRID_HEIGHT) / self.getHeight() * _height)

        scaledPaddingX = int(float(COORD_GRID_WIDTH) / self.getWidth() * _padding)
        scaledPaddingY = int(float(COORD_GRID_HEIGHT) / self.getHeight() * _padding)

        if _alignment == 0: # vertical right, top to bottom
            scaledX = COORD_GRID_WIDTH - scaledWidth - scaledPaddingX
            scaledY = position * scaledHeight + (position + 1) * scaledPaddingY
        if _alignment == 1: # vertical left, top to bottom
            scaledX = scaledPaddingX
            scaledY = position * scaledHeight + (position + 1) * scaledPaddingY
        if _alignment == 2: # horizontal top, left to right
            scaledX = position * scaledWidth + (position + 1) * scaledPaddingX
            scaledY = scaledPaddingY
        if _alignment == 3: # horizontal bottom, left to right
            scaledX = position * scaledWidth + (position + 1) * scaledPaddingX
            scaledY = COORD_GRID_HEIGHT - scaledHeight - scaledPaddingY
        if _alignment == 4: # square right
            scaledX = COORD_GRID_WIDTH - (2 - position%2) * scaledWidth - (2 - position%2) * scaledPaddingX
            scaledY = position/2 * scaledHeight + (position/2 + 1) * scaledPaddingY
        if _alignment == 5: # square left
            scaledX = position%2 * scaledWidth + (position%2 + 1) * scaledPaddingX
            scaledY = position/2 * scaledHeight + (position/2 + 1) * scaledPaddingY
        if _alignment == 6: # vertical right, bottom to top
            scaledX = COORD_GRID_WIDTH - scaledWidth - scaledPaddingX
            scaledY = COORD_GRID_HEIGHT - (position + 1) * scaledHeight + (position + 1) * scaledPaddingY
        if _alignment == 7: # vertical left, bottom to top
            scaledX = scaledPaddingX
            scaledY = COORD_GRID_HEIGHT - (position + 1) * scaledHeight + (position + 1) * scaledPaddingY
        if _alignment == 8: # horizontal top, right to left
            scaledX = COORD_GRID_WIDTH - (position + 1) * scaledWidth - (position + 1) * scaledPaddingX
            scaledY = scaledPaddingY
        if _alignment == 9: # horizontal bottom, right to left
            scaledX = COORD_GRID_WIDTH - (position + 1) * scaledWidth - (position + 1) * scaledPaddingX
            scaledY = COORD_GRID_HEIGHT - scaledHeight - scaledPaddingY
        if _alignment == 10: # square right botton
            scaledX = COORD_GRID_WIDTH - (2 - position%2) * scaledWidth - (2 - position%2) * scaledPaddingX
            scaledY = COORD_GRID_HEIGHT/2 - position/2 * scaledHeight - (position/2 - 1) * scaledPaddingY
        if _alignment == 11: # square left bottom
            scaledX = position%2 * scaledWidth + (position%2 + 1) * scaledPaddingX
            scaledY = COORD_GRID_HEIGHT/2 - position/2 * scaledHeight - (position/2 - 1) * scaledPaddingY            

        return scaledX, scaledY, scaledWidth, scaledHeight

    def start(self):
        self.show()
        self.isRunning = True
        # send notification
        if requestType == 'motion':
            xbmc.executebuiltin('Notification(Motion,' + str(self.cams[0]['name']) +','+ str(_duration) + ')')
        elif requestType == 'display':
            xbmc.executebuiltin('Notification(View Cameras,,'+ str(_duration) + ')')

        for i in range(MAXCAMS):
            if self.cams[i]['url']:
                Thread(target=self.update, args=(self.cams[i],)).start()

        startTime = time.time()
        while(not _autoClose or (time.time() - startTime) * 1000 <= _duration):
            if not self.isRunning:
                 break

            xbmc.sleep(1000)

        self.isRunning = False

        self.close()
        self.cleanup()

    def update(self, cam):
        request = urllib2.Request(cam['url'])
        index = 1

        if cam['url'][:4] == 'rtsp' and not which(ffmpeg_exec):
            log('Error: {} not installed. Can\'t process rtsp input format.'.format(ffmpeg_exec))
            #self.isRunning = False
            self.stop()
            return

        if cam['url'][:4] == 'rtsp':
            if cam['username'] and cam['password']:
                input = 'rtsp://{}:{}@{}'.format(cam['username'], cam['password'], cam['url'][7:])
            else:
                input = cam['url']

            output = os.path.join(cam['tmpdir'], 'snapshot_%06d.jpg')
            command = [ffmpeg_exec,
                      '-nostdin',
                      '-rtsp_transport', 'tcp',
                      '-i', input,
                      '-an',
                      '-f', 'image2',
                      '-vf', 'fps=fps='+str(int(1000.0/_interval)),
                      '-q:v', '10',
                      '-s', str(_width)+'x'+str(_height),
                      '-vcodec', 'mjpeg',
                      xbmc.translatePath(output)]
            p = subprocess.Popen(command)

        while(self.isRunning):
            snapshot = os.path.join(cam['tmpdir'], 'snapshot_{:06d}.jpg'.format(index))
            index += 1

            try:
                if cam['url'][:4] == 'http':
                    imgData = self.opener.open(request).read()

                    #r = auth_get(cam['url'], cam['username'], cam['password'], verify=False, stream=True)
                    #if r.status_code == 200: # success!
                    #    imgData = r.content

                    if imgData:
                        file = xbmcvfs.File(snapshot, 'wb')
                        file.write(imgData)
                        file.close()

                elif cam['url'][:4] == 'rtsp':
                    while(self.isRunning):
                       if xbmcvfs.exists(snapshot):
                           break

                elif xbmcvfs.exists(cam['url']):
                    xbmcvfs.copy(cam['url'], snapshot)

            except Exception, e:
                log(str(e))
                #snapshot = __loading__
                snapshot = None

            #if snapshot and xbmcvfs.exists(snapshot):
            if snapshot:
                cam['control'].setImage(snapshot, False)
                xbmc.sleep(_interval)
            
            if cam['url'][:4] != 'rtsp' and which(ffmpeg_exec):
                xbmc.sleep(_interval)

        if cam['url'][:4] == 'rtsp' and p.pid:
            p.terminate()

    def cleanup(self):
        for i in range(MAXCAMS):
            if self.cams[i]['tmpdir']:
                files = xbmcvfs.listdir(self.cams[i]['tmpdir'])[1]
                for file in files:
                    xbmcvfs.delete(os.path.join(self.cams[i]['tmpdir'], file))
                xbmcvfs.rmdir(self.cams[i]['tmpdir'])

    def onAction(self, action):
        if action in (ACTION_PREVIOUS_MENU, ACTION_BACKSPACE, ACTION_NAV_BACK):
            self.stop()

    def stop(self):
        self.isRunning = False


if __name__ == '__main__':
    if streamid > 0:
        log('Addon called with streamid={}'.format(streamid))

    camPreview = CamPreviewDialog(name, urls, usernames, passwords)
    camPreview.start()

    del camPreview
