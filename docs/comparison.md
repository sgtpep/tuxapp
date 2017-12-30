# Comparison

Comparison of `tuxapp` with other app distribution formats.

## AppImage

`AppImage` authors assume some libraries are already present on user's system but depending on a distribution or installed desktop environment (or lack of it) they may be missing, and a user gets something like `error while loading shared libraries: libfoobar.so`. The only way to run an app distributed as `AppImage` sandboxed and secure is to call it using `firejail --appimage`, but at the moment of writing it doesn't work with the `AppImage type 2` format and `firejail 0.9.44.8` (`Debian stretch` and `Ubuntu zesty`). The `--appimage` argument isn't available on earlier versions of `firejail`.

`tuxapp` detects and downloads all libraries required by an app and patches it to use them. Apps installed with `tuxapp` run sandboxed automatically if `firejail` is installed.

## Flatpak

`Flatpak` uses containerization-like technologies. It results in the bigger size of app distributions and slightly worse integration with the system and other apps.

`tuxapp` apps are just regular apps which are sandboxed using `firejail` if it's available.

## snap

To sandbox installed apps the `snap` technology relies on the `AppArmor` kernel system which is enabled only on Ubuntu-based distributions and maybe few others. Also, looks like the `snap` technology is targeted on Ubuntu and is not tested against other distributions.

`tuxapp` is distribution agnostic. Apps installed using it intended to work on any distribution and tested on at least five distributions. `tuxapp` provides security on any system where `firejail` is installed.
