# tuxapp

[**TuxApp.org**](https://tuxapp.org/) is an effort to build an open, community-driven and independent catalog of *Linux®* applications. We believe that apps should be easily installable, up-to-date and work effortlessly on any *Linux®* distribution of any version. Being distributed in the binary form it's more secure to run them sandboxed, isolated from system and user's sensitive files. To seamlessly solve these longstanding problems we've built a tool, [**tuxapp**](https://github.com/sgtpep/tuxapp), that downloads and installs the latest official releases of *Linux®* applications including dependencies without root permissions and allows to run them sandboxed.

## Usage

### Install, execute, update and remove an app

- Install or update Firefox: `tuxapp firefox`
- Execute Firefox: `tuxapp -e firefox`
- Check Firefox for updates: `tuxapp -c firefox`
- Update Firefox: tuxapp -u firefox
- Remove Firefox: `tuxapp -r firefox`

### Other actions

- List apps available for installation: `tuxapp -a`
- Check installed apps for updates: `tuxapp -c`
- Show help: `tuxapp -h`
- List installed apps: `tuxapp -l`
- Purge cache: `tuxapp -p`
- Update installed apps: `tuxapp -u`
