# script.securitycam

This a rework of the kodi 'Security Cam Overlay' addon originally developed by Ryan Melena Noesis.

The main change is that the addon is now capable of handling up to 4 camera feeds simultaneously. Each feed is updated in a seperate thread which should add to the addon's performance. 

Though the addon would technically support even more feeds, it is restricted by the arrangement of the feeds in the (single) window. The arrangement currently supports only a 4 item geometry: horizontal, vertical or square (2x2).

The addon feeds each require a source providing snapshots in jpeg format. This can either be a http URL or a file source (new). You should adjust the refresh interval in accordance with the source's capapility to update its output.

If you want the addon execution triggered by email (this is how I get notified exclusively of a motion detected by my cam), you may also want to look at my other project 'Kodi-Email-Alert'.

Alternatively, with a PIR motion detection device sending on 433 Mhz and 433 Mhz receiver module in a raspberry pi you can kick-off the addon almost instantly on any motion detected. Have look at my project 'Kodi-RF-Alert' if you're interested.
