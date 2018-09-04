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
import os, time, urllib2, xbmc, xbmcaddon, xbmcgui, xbmcvfs, random, string
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
urls       = [None] * MAXCAMS
usernames  = [None] * MAXCAMS
passwords  = [None] * MAXCAMS

for i in range(MAXCAMS):
    urls[i] =__addon__.getSetting('url{:d}'.format(i + 1))
    usernames[i] =__addon__.getSetting('username{:d}'.format(i + 1))
    passwords[i] =__addon__.getSetting('password{:d}'.format(i + 1))

_width     = int(float(__addon__.getSetting('width')))
_height    = int(float(__addon__.getSetting('height')))
_interval  = int(float(__addon__.getSetting('interval')))
_autoClose = bool(__addon__.getSetting('autoClose') == 'true')
_duration  = int(float(__addon__.getSetting('duration')) * 1000)
_alignment = int(float(__addon__.getSetting('alignment')))
_padding   = int(float(__addon__.getSetting('padding')))
_animate   = bool(__addon__.getSetting('animate') == 'true')

# Utils
def log(message,loglevel=xbmc.LOGNOTICE):
    xbmc.log(msg='[{}] {}'.format(__addon_id__, message), level=loglevel)

# Classes
class CamPreviewDialog(xbmcgui.WindowDialog):
    def __init__(self, urls, usernames, passwords):
        self.cams = [{'url':None, 'username':None, 'password':None, 'tmpdir':None, 'control':None} for i in range(MAXCAMS)]

        for i in range(MAXCAMS):
            if urls[i]:
                self.cams[i]['url'] = urls[i]

                if usernames[i] and passwords[i]:
                    self.cams[i]['username'] = usernames[i]
                    self.cams[i]['password'] = passwords[i]

                randomname = ''.join([random.choice(string.ascii_letters + string.digits) for n in xrange(32)])
                self.cams[i]['tmpdir'] = os.path.join(__profile__, randomname)
                if not xbmcvfs.exists(self.cams[i]['tmpdir']):
                    xbmcvfs.mkdir(self.cams[i]['tmpdir'])

                x, y, w, h = self.coordinates(i)
                self.cams[i]['control'] = xbmcgui.ControlImage(x, y, w, h, __loading__, aspectRatio = 1)
                self.addControl(self.cams[i]['control'])

                if _animate:
                    if _alignment in [0, 4, 6, 8, 9]:
                        direction = 1
                    else:
                        direction = -1
                    self.cams[i]['control'].setAnimations([('WindowOpen', 'effect=slide start=%d time=1000 tween=cubic easing=in'%(w*direction),), ('WindowClose', 'effect=slide end=%d time=1000 tween=cubic easing=in'%(w*direction),)])

    def coordinates(self, position):
        COORD_GRID_WIDTH = 1280
        COORD_GRID_HEIGHT = 720

        scaledWidth = int(float(COORD_GRID_WIDTH) / self.getWidth() * _width)
        scaledHeight = int(float(COORD_GRID_HEIGHT) / self.getHeight() * _height)

        if _alignment == 0: # vertical right, top to bottom
            scaledX = COORD_GRID_WIDTH - scaledWidth - _padding
            scaledY = position * scaledHeight + (position + 1) * _padding
        if _alignment == 1: # vertical left, top to bottom
            scaledX = _padding
            scaledY = position * scaledHeight + (position + 1) * _padding
        if _alignment == 2: # horizontal top, left to right
            scaledX = position * scaledWidth + (position + 1) * _padding
            scaledY = _padding
        if _alignment == 3: # horizontal bottom, left to right
            scaledX = position * scaledWidth + (position + 1) * _padding
            scaledY = COORD_GRID_HEIGHT - scaledHeight - _padding
        if _alignment == 4: # square right
            scaledX = COORD_GRID_WIDTH - (2 - position%2) * scaledWidth - (2 - position%2) * _padding
            scaledY = position%2 * scaledHeight + (position%2 + 1) * _padding
        if _alignment == 5: # square left
            scaledX = position%2 * scaledWidth + (position%2 + 1) * _padding
            scaledY = position%2 * scaledHeight + (position%2 + 1) * _padding
        if _alignment == 6: # vertical right, bottom to top
            scaledX = COORD_GRID_WIDTH - scaledWidth - _padding
            scaledY = COORD_GRID_HEIGHT - (position + 1) * scaledHeight + (position + 1) * _padding
        if _alignment == 7: # vertical left, bottom to top
            scaledX = _padding
            scaledY = COORD_GRID_HEIGHT - (position + 1) * scaledHeight + (position + 1) * _padding
        if _alignment == 8: # horizontal top, right to left
            scaledX = COORD_GRID_WIDTH - (position + 1) * scaledWidth - (position + 1) * _padding
            scaledY = _padding
        if _alignment == 9: # horizontal bottom, right to left
            scaledX = COORD_GRID_WIDTH - (position + 1) * scaledWidth - (position + 1) * _padding
            scaledY = COORD_GRID_HEIGHT - scaledHeight - _padding

        return scaledX, scaledY, scaledWidth, scaledHeight

    def start(self):
        self.show()
        self.isRunning = True

        for i in range(MAXCAMS):
            if self.cams[i]['url']:
                Thread(target=self.update, args=(self.cams[i],)).start()

        startTime = time.time()
        while(not _autoClose or (time.time() - startTime) * 1000 <= _duration):
            if not self.isRunning:
                 break

            xbmc.sleep(500)

        self.isRunning = False

        self.close()
        self.cleanup()

    def update(self, cam):
        if cam['url'][:4] == 'http':
            request = urllib2.Request(cam['url'])

            if cam['username'] and cam['password']:
                base64str = base64.b64encode('{}:{}'.format(cam['username'], cam['password']))
                request.add_header('Authorization', 'Basic {}'.format(base64str))

        index=0
        while(self.isRunning):
            snapshot = os.path.join(cam['tmpdir'], 'snapshot' + str(index) + '.jpg' )
            index = (index + 1)%10

            try:
                if cam['url'][:4] == 'http':
                    imgData = urllib2.urlopen(request).read()
                    file = xbmcvfs.File(snapshot, 'wb')
                    file.write(imgData)
                    file.close()
                elif xbmcvfs.exists(cam['url']):
                    xbmcvfs.copy(cam['url'], snapshot)

            except Exception, e:
                log(str(e))
                snapshot = __loading__

            if xbmcvfs.exists(snapshot):
                cam['control'].setImage(snapshot, False)

            xbmc.sleep(_interval)

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
    camPreview = CamPreviewDialog(urls, usernames, passwords)
    camPreview.start()

    del camPreview
