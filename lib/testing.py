# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import functools
import glob
import os
import stat
import sys
import textwrap
import time

from lib import (
  appfile,
  tuxapp,
  utilities,
)

def check_app_process_timeout(function):
  @functools.wraps(function)
  def wrapper(app, *args, **kwargs):
    timestamp = time.time()
    result = function(app, *args, **kwargs)
    if time.time() - timestamp < get_process_timeout() - 0.5 and not any(extract_app_library(app, line) for line in result.splitlines()) and not is_app_process_output_ignored(app, result):
      print('\n{}'.format(result), file=sys.stderr)
      raise AssertionError('{} exited unexpectedly'.format(app))
    else:
      return result
  return wrapper

def test_app_worker(app):
  return test_app(app)

build_bwrap_arguments = lambda distribution, app=None, arguments=(), is_trace=False: \
  utilities.install_missing_package('bubblewrap', 'bwrap') and \
  ('bwrap', '--bind', tuxapp.get_app_root_path(distribution), '/',
    '--bind', '/run', '/run',
    '--dev-bind', '/dev', '/dev',
    '--proc', '/proc',
    '--ro-bind', '/etc/resolv.conf', '/etc/resolv.conf',
    '--ro-bind', '/sys', '/sys',
    '--setenv', 'TUXAPP_TEST', '1',
    '--tmpfs', '/tmp',
  ) + \
  tuple(option for path in build_bwrap_readonly_bind_paths() for option in ('--ro-bind', path, path)) + \
  (('--setenv', 'TUXAPP_TRACE', '1') if is_trace else ()) + \
  (('--bind', tuxapp.get_app_path(app), tuxapp.get_app_path(app)) if app else ('--bind', os.path.expanduser('~'), os.path.expanduser('~'))) + \
  ('bash', '-l') + \
  ((tuxapp.get_app_runner_path(app),) + arguments if app else ())

build_bwrap_readonly_bind_paths = lambda: \
  tuple(path for pattern in (
    '/usr/lib/*-linux-gnu/alsa-lib',
    '/usr/lib/*-linux-gnu/pulseaudio',
    '/usr/lib/locale',
    '/usr/share/alsa',
  ) for path in glob.iglob(pattern)) + \
  ((get_xauthority_path(),) if tuxapp.is_existing_command('xvfb-run') and os.path.isfile(get_xauthority_path()) else ())

build_root_bwrap_arguments = lambda distribution: \
  utilities.install_missing_package('bubblewrap', 'bwrap') and \
  ('bwrap', '--bind', tuxapp.get_app_root_path(distribution), '/',
    '--bind', '/etc/resolv.conf', '/etc/resolv.conf',
    '--bind', tuxapp.make_directories(tuxapp.get_app_temp_path(distribution)), '/var/cache/pacman/pkg' if distribution == 'arch' else '/var/cache/apt/archives',
    '--dev', '/dev',
    '--proc', '/proc',
    '--tmpfs', '/tmp',
  ) + \
  ('env', '-u', 'LANG') + \
  (('fakechroot', 'fakeroot') if distribution == 'arch' else ('fakeroot-sysv',)) + \
  ('bash', '-l')

call_root_script = lambda distribution, script: \
  tuxapp.call_process(build_root_bwrap_arguments(distribution) + ('-c', textwrap.dedent(r'''
  set -eu -o pipefail
  (
    {}
  ){}
  ''').format(
    script,
    ' &> /dev/null' if tuxapp.is_silent() else '',
  )))

configure_arch_container = lambda: \
  tuxapp.write_file(os.path.join(tuxapp.get_app_root_path('arch'), 'etc/pacman.d/mirrorlist'), 'Server = {}\n'.format(get_arch_mirror_url('$repo/os/$arch'))) and \
  call_root_script('arch', r'''
  pacman-key --init
  pacman-key --populate archlinux
  packages=(
    base
    strace
    ttf-dejavu
    xkeyboard-config
  )
  pacman -Sy --force --needed --noconfirm "${packages[@]}"
  ''')

configure_debian_container = lambda: \
  tuxapp.write_file(os.path.join(tuxapp.get_app_root_path('debian'), 'etc/apt/apt.conf.d/50keep-downloaded-packages'), 'Binary::apt::APT::Keep-Downloaded-Packages "true";\n') and \
  tuxapp.write_file(os.path.join(tuxapp.get_app_root_path('debian'), 'etc/apt/sources.list'), textwrap.dedent('''\
  deb http://deb.debian.org/debian {0} main
  deb http://security.debian.org/ {0}/updates main
  ''').format(appfile.get_default_package_repository())) and \
  update_debian_container() and \
  call_root_script('debian', r'''
  packages=(
    fontconfig-config
    fonts-dejavu-core
    strace
    xkb-data
  )
  DEBIAN_FRONTEND=noninteractive apt install -y "${packages[@]}"
  ''')

detect_missing_app_libraries = \
  tuxapp.do(lambda app, distribution, *args, **kwargs: kwargs['result'] and print('Missing libraries for {} on {}: {}'.format(app, distribution, ', '.join(kwargs['result'])), file=sys.stderr))(
    lambda app, distribution: tuple(sorted(set(library for library in (extract_app_library(app, line) for line in test_app_process(app, distribution).splitlines()) if library)))
  )

execute_app = lambda distribution, app, arguments=(), is_trace=False: tuxapp.execute_process(build_bwrap_arguments(install_missing_container(distribution), app, arguments, is_trace))

execute_root_shell = lambda distribution: tuxapp.execute_process(build_root_bwrap_arguments(install_missing_container(distribution)))

execute_shell = lambda distribution: tuxapp.execute_process(build_bwrap_arguments(install_missing_container(distribution)))

extract_app_library = lambda app, string: '' if extract_library(string) == 'libGL.so.1' or extract_library(string) in tuxapp.query_appfile(app, 'ignored-libraries').split() else extract_library(string)

extract_library = lambda string: \
  'libqxcb.so' \
    if ' could not find or load the Qt platform plugin "xcb"' in string else \
  tuxapp.search(r'[\w.-]+\.so\b[\w.]*', string) \
    if '/nacl_helper: error while loading shared libraries: ' not in string else \
  ''

get_arch_mirror_url = lambda path='': os.path.join('https://mirrors.kernel.org/archlinux/', path)

get_arch_package_url = lambda package: get_arch_mirror_url(os.path.join('extra' if package == 'fakechroot' else 'core', 'os/x86_64/'))

get_debian_container_url = lambda: 'https://download.openvz.org/template/precreated/contrib/debian-9.0-{}-minimal.tar.gz'.format(tuxapp.detect_architecture().replace('-', '_'))

get_debian_package_url = lambda package: 'https://packages.debian.org/{}/{}/{}/download'.format(appfile.get_default_package_repository(), tuxapp.detect_debian_architecture(), package)

get_default_distribution = lambda: 'debian'

get_distributions = lambda: \
  (
    'arch',
    'debian',
  )

get_install_mark_path = lambda distribution: os.path.join(tuxapp.get_app_root_path(distribution), 'var/lib', tuxapp.get_name())

get_process_timeout = lambda: 3

get_test_distributions = lambda: \
  (get_default_distribution(),) + \
  get_distributions()[:get_distributions().index(get_default_distribution())] + \
  get_distributions()[get_distributions().index(get_default_distribution()) + 1:]

get_xauthority_path = lambda: os.path.expanduser('~/.Xauthority')

install_arch_container = lambda: \
  tuxapp.unpack_tarball(tuxapp.download_missing_app_temp_file('arch', request_arch_container_url()), tuxapp.get_app_root_path('arch'), ('--strip-components=1',)) and \
  tuxapp.change_file_mode(os.path.join(tuxapp.get_app_root_path('arch'), 'etc/ca-certificates/extracted/cadir'), lambda mode: mode | stat.S_IWUSR) and \
  all(install_arch_container_package(package) for package in ('fakechroot', 'fakeroot', 'sed')) and \
  configure_arch_container()

install_arch_container_package = lambda package: \
  tuxapp.silence(tuxapp.unpack_tarball)(tuxapp.download_missing_app_temp_file('arch', request_arch_package_url(package)), tuxapp.get_app_root_path('arch'), ('--exclude=.*', '--warning=no-unknown-keyword')) and \
  package

install_container = \
  tuxapp.check('Failed to install {}')(
    lambda distribution: \
      install_arch_container() \
        if distribution == 'arch' else \
      install_debian_container()
  )

install_debian_container = lambda: \
  tuxapp.unpack_tarball(tuxapp.download_missing_app_temp_file('debian', get_debian_container_url()), tuxapp.get_app_root_path('debian'), ('--exclude=./dev',)) and \
  all(install_debian_container_package(package) for package in ('fakeroot', 'libfakeroot')) and \
  configure_debian_container()

install_debian_container_package = lambda package: \
  tuxapp.silence(tuxapp.unpack_package)(tuxapp.download_missing_app_temp_file('debian', request_debian_package_url(package)), tuxapp.get_app_root_path('debian')) and \
  package

install_missing_container = lambda distribution: \
  update_old_container(distribution) and \
  distribution \
    if os.path.isfile(get_install_mark_path(distribution)) else \
  install_container(distribution) and \
  tuxapp.write_file(get_install_mark_path(distribution)) and \
  utilities.update_data(('container', distribution, 'update-timestamp'), int(time.time())) and \
  distribution

is_app_process_output_ignored = lambda app, output: \
  {
    'subsurface': 'Could not initialize GLX',
    'supertuxkart': 'Fatal error, could not get visual.',
    'viber': 'Could not initialize GLX',
  }.get(app, r'\0') in output

request_arch_container_url = lambda: get_arch_mirror_url('iso/latest/') + tuxapp.request_grep_url(get_arch_mirror_url('iso/latest/'), ('-Po', '-m', '1', r'(?<=")archlinux-bootstrap-[^"]+'))

request_arch_package_url = lambda package: get_arch_package_url(package) + tuxapp.request_grep_url(get_arch_package_url(package), ('-Po', '-m', '1', r'(?<="){}-[^"]+'.format(package)))

request_debian_package_url = lambda package: tuxapp.get_debian_mirror_url() + tuxapp.request_grep_url(get_debian_package_url(package), ('-o', '-m', '1', r'[^/]*/pool/[^"]*'))

test_app = lambda app: \
  test_installed_app(app) \
    if tuxapp.is_app_installed(app) else \
  (tuxapp.install_app(app) or tuxapp.remove_app(app) and False) and \
  (tuxapp.remove_app(app) if test_installed_app(app) else tuxapp.remove_app(app) and False)

test_app_process = \
  tuxapp.log('Trying {} on {}')(
  check_app_process_timeout(
    lambda app, distribution: \
      utilities.install_missing_package('strace') and \
      utilities.install_missing_package('xvfb', 'xvfb-run') and \
      tuxapp.read_process(r'''
      output=$({}timeout -s 9 {} {} 2>&1)
      kill -9 $(echo "$output" | grep -Po '(?<= Process )\d+') 2> /dev/null
      echo "$output"
      '''.format(
        'xvfb-run -a -f {} '.format(tuxapp.quote_argument(get_xauthority_path())) if tuxapp.is_existing_command('xvfb-run') else '',
        tuxapp.quote_argument(get_process_timeout()),
        tuxapp.join_arguments(build_bwrap_arguments(install_missing_container(distribution), app)).replace(' bash ', ' strace -f -e none bash ', 1),
      ), True)
  ))

test_apps = lambda apps: utilities.call_parallel(test_app_worker, apps, 4)

test_installed_app = lambda app: all(not detect_missing_app_libraries(app, distribution) for distribution in get_test_distributions())

update_arch_container = lambda: call_root_script('arch', r'pacman -Syu --noconfirm')

update_container = lambda distribution: \
  update_arch_container() \
    if distribution == 'arch' else \
  update_debian_container()

update_debian_container = lambda: \
  call_root_script('debian', r'''
  apt update
  DEBIAN_FRONTEND=noninteractive apt dist-upgrade -y
  ''')

update_old_container = lambda distribution: \
  update_container(distribution) and \
  tuxapp.remove_old_files(tuxapp.get_app_temp_file_path(distribution, '*'), 30) and \
  utilities.update_data(('container', distribution, 'update-timestamp'), int(time.time())) \
    if int(utilities.query_data(('container', distribution, 'update-timestamp'), '0')) < time.time() - 60 * 60 * 24 else \
  True
