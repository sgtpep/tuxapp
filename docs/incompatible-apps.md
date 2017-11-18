# Incompatible apps

`tuxapp` requires some significant modifications or workarounds to make these apps working which may be resolved later.

- **Dragonfire**: https://github.com/DragonComputer/Dragonfire: installs many python packages from the .deb postinst script
- **Nylas Mail Lives** https://github.com/nylas-mail-lives/nylas-mail: hangs on startup
- **Ring** https://ring.cx/: the daemon application needs to be launched before the graphical one
- **Seafile** https://www.seafile.com/en/home/: splitted into many packages with different versions, hangs after the welcome screen
- **Steam** http://store.steampowered.com/: requires x86 libraries on the x86-64 architecuture
- **k2pdfopt** http://www.willus.com/k2pdfopt/: requires solving a CAPTCHA to download
