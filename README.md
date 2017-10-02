# tuxapp

tuxapp downloads and installs the latest official releases of Linux© applications including dependencies without root permissions and allows to run them sandboxed.

## Usage of `tuxapp`

### Install, run, update and uninstall an app

- Install or update Firefox: `tuxapp firefox` or `tuxapp -i firefox`
- Run Firefox: `tuxapp -r firefox`
- Check Firefox for updates: `tuxapp -c firefox`
- Uninstall Firefox: `tuxapp -u firefox`

### Configure, disable, enable firejail

- Install or update Firefox and set permanent firejail options: `tuxapp -f "--debug --x11=xorg" firefox`
- Install or update Firefox and disable firejail permanently: `tuxapp -f off firefox`
- Install or update Firefox and enable firejail permanently: `tuxapp -f on firefox`
- Run Firefox with temporary firejail options: `tuxapp -r -f "--debug --x11=xorg" firefox`
- Run Firefox with temporarily disabled firejail: `tuxapp -r -f off firefox`
- Run Firefox with temporarily enabled firejail: `tuxapp -r -f on firefox`

### Other actions

- List apps available for installation: `tuxapp -a`
- Check installed apps for updates: `tuxapp -c`
- Show help: `tuxapp -h`
- Update all installed apps: `tuxapp -i`
- List installed apps: `tuxapp -l`
- Purge cache: `tuxapp -p`
