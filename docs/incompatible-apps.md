# Incompatible apps

The following apps are not supported by `tuxapp` due to different issues which may require some significant modifications or workarounds:

- [Discord](https://discordapp.com/): gray window on startup
- [Dragonfire](http://dragon.computer/#dragonfire): installs many python packages from the .deb postinst script
- [MySQL Workbench](https://www.mysql.com/products/workbench/): aborts with 'Gtk:ERROR:/build/gtk+3.0-Th_a5U/gtk+3.0-3.22.24/./gtk/gtkiconhelper.c:493:ensure_surface_for_gicon: assertion failed: (destination)'
- [Ring](https://ring.cx/): no GUI is appeared
- [Sayonara Player](http://sayonara-player.com/): accesses files by hardcoded paths starting with /usr/share/sayonara
- [Seafile](https://www.seafile.com/en/home/): no GUI is appeared after the welcome screen
- [Steam](http://store.steampowered.com/): requires x86 libraries on the x86-64 architecuture
- [Vimiv](http://karlch.github.io/vimiv/): contains an extension that needs to be compiled
- [darktable](https://www.darktable.org/): an executable fails with 'symbol lookup error: <...>/libdarktable.so: undefined symbol: XXXXXXXXX'
- [k2pdfopt](http://www.willus.com/k2pdfopt/): requires solving a CAPTCHA to download
