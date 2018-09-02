#!/usr/bin/python
# -*- coding: utf-8 -*-

# Source: https://github.com/RyanMelenaNoesis/XbmcSecurityCamOverlayAddOn"
# and kodi forum discussion: https://forum.kodi.tv/showthread.php?tid=182540
#
# JSONRPC Call to trigger this script:
# e.g. http://192.168.178.12:8080/jsonrpc?request={"jsonrpc":"2.0","method":"Addons.ExecuteAddon","params":{"addonid":"script.securitycam"},"id":"1"}

# Import the modules
import os, time, urllib2, xbmc, xbmcaddon, xbmcgui, xbmcvfs, random, string
from threading import Thread

# Constants
ACTION_PREVIOUS_MENU = 10
ACTION_BACKSPACE = 110
ACTION_NAV_BACK = 92

# Set plugin variables
__addon__        = xbmcaddon.Addon()
__addon_id__     = __addon__.getAddonInfo('id')
__addon_path__   = __addon__.getAddonInfo('path')
__profile__      = __addon__.getAddonInfo('profile')
__icon__         = os.path.join(__addon_path__, 'icon.png')
__spinner__      = os.path.join(__addon_path__, 'loading.gif')

# Get settings
url       = __addon__.getSetting('url')
username  = __addon__.getSetting('username')
password  = __addon__.getSetting('password')

_width     = int(float(__addon__.getSetting('width')))
_height    = int(float(__addon__.getSetting('height')))
_interval  = int(float(__addon__.getSetting('interval')))
_autoClose = bool(__addon__.getSetting('autoClose') == 'true')
_duration  = int(float(__addon__.getSetting('duration')) * 1000)

# Utils
def log(message,loglevel=xbmc.LOGNOTICE):
    xbmc.log(msg='[{}] {}'.format(__addon_id__, message), level=loglevel)

# Classes
class CamPreviewDialog(xbmcgui.WindowDialog):
    def __init__(self, index, url, username, password):
        COORD_GRID_WIDTH = 1280
        COORD_GRID_HEIGHT = 720

        scaledWidth = int(float(COORD_GRID_WIDTH) / self.getWidth() * _width)
        scaledHeight = int(float(COORD_GRID_HEIGHT) / self.getHeight() * _height)

        if index < 1 or index > 4:
            log('Window index of {} is outside of allowed range (1..4)'.format(index))
            return

        scaledX = COORD_GRID_WIDTH - scaledWidth - 25
        scaledY = (index - 1) * scaledHeight + index * 25

        self.url = url
        self.username = username
        self.password = password

        randomname = ''.join([random.choice(string.ascii_letters + string.digits) for n in xrange(32)])
        self.snapshotdir = os.path.join(__profile__, randomname)
        if not xbmcvfs.exists(self.snapshotdir):
            xbmcvfs.mkdir(self.snapshotdir)

        self.image = xbmcgui.ControlImage(scaledX, scaledY, scaledWidth, scaledHeight, __spinner__, aspectRatio = 1)
        self.addControl(self.image)

    def start(self):
        Thread(target=self.update, args=()).start()
        return self

    def update(self):
        self.show()
        self.isRunning = True

        startTime = time.time()

        request = urllib2.Request(self.url)

        if self.username and self.password:
            base64str = base64.b64encode('{}:{}'.format(self.username, self.password))
            request.add_header('Authorization', 'Basic {}'.format(base64str))

        i=0
        while(not _autoClose or (time.time() - startTime) * 1000 <= _duration):
            #snapshot = os.path.join(self.snapshotdir, 'snapshot' + str(time.time()) + '.jpg' )
            snapshot = os.path.join(self.snapshotdir, 'snapshot' + str(i) + '.jpg' )
            i = i+1

            try:
                imgData = urllib2.urlopen(request).read()
                file = xbmcvfs.File(snapshot, 'wb')
                file.write(imgData)
                file.close()

            except Exception, e:
                log(str(e))

            if xbmcvfs.exists(snapshot):
                self.image.setImage(snapshot, False)

            xbmc.sleep(_interval)

            if not self.isRunning:
                break

        self.close()
        self.cleanup()

    def cleanup(self):
        files = xbmcvfs.listdir(self.snapshotdir)[1]
        for file in files:
            xbmcvfs.delete(os.path.join(self.snapshotdir, file))
        xbmcvfs.rmdir(self.snapshotdir)

    def onAction(self, action):
        log('onAction')
        if action in (ACTION_PREVIOUS_MENU, ACTION_BACKSPACE, ACTION_NAV_BACK):
            self.stop()

    def stop(self):
            self.isRunning = False


if __name__ == '__main__':
    camPreview1 = CamPreviewDialog(1, url, username, password)
    #camPreview1.update()
    camPreview1.start()


    #camPreview1 = CamPreviewDialog(1, url, username, password).start()

    url2='http://192.168.178.13/cgi-bin/get_stream6'
    camPreview2 = CamPreviewDialog(2, url2, username, password).start()

    del camPreview1
    del camPreview2
