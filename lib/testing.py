# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import glob
import functools
import os
import stat
import sys
import textwrap
import time

from lib import (
  tuxapp,
  utilities,
)

def check_app_process_output(function):
  @functools.wraps(function)
  def wrapper(app, distribution):
    timestamp = time.time()
    output = function(app, distribution)
    if any(extract_app_library(app, line) for line in output.splitlines()):
      if not tuxapp.is_silent():
        print(output, file=sys.stderr)
    elif time.time() - timestamp < get_process_timeout() - 0.5 and not is_app_process_output_ignored(app, output):
      print('\n{}'.format(output), file=sys.stderr)
      raise AssertionError('{} terminated unexpectedly on {}'.format(app, distribution))
    return output
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
  (('--bind', tuxapp.get_app_path(app), tuxapp.get_app_path(app)) if app else ()) + \
  tuple(option for path in build_bwrap_readonly_bind_paths() for option in ('--ro-bind', path, path)) + \
  (('--ro-bind', get_app_xauthority_path(app), get_app_xauthority_path(app)) if app and os.path.isfile(get_app_xauthority_path(app)) else ()) + \
  (('--setenv', 'TUXAPP_TRACE', '1') if is_trace else ()) + \
  ('bash', '-l') + \
  ((tuxapp.get_app_runner_path(app),) + arguments if app else ())

build_bwrap_readonly_bind_paths = lambda: \
  tuple(path for pattern in (
    '/usr/lib/*-linux-gnu/alsa-lib',
    '/usr/lib/*-linux-gnu/pulseaudio',
    '/usr/lib/locale',
    '/usr/share/alsa',
  ) for path in glob.iglob(pattern))

build_root_bwrap_arguments = lambda distribution: \
  utilities.install_missing_package('bubblewrap', 'bwrap') and \
  ('bwrap', '--bind', tuxapp.get_app_root_path(distribution), '/',
    '--bind', '/etc/resolv.conf', '/etc/resolv.conf',
    '--bind', tuxapp.make_directories(tuxapp.get_app_temp_path(distribution)), get_distribution_cache_path(distribution),
    '--dev', '/dev',
    '--proc', '/proc',
    '--tmpfs', '/tmp',
  ) + \
  (('--ro-bind', '/etc/machine-id', '/etc/machine-id') if distribution == 'xenial' else ()) + \
  ('env', '-u', 'LANG') + \
  (() if is_debian_distribution(distribution) else ('PATH=/usr/sbin:/usr/bin:/sbin:/bin',)) + \
  get_distribution_fakeroot_arguments(distribution) + \
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
  tuxapp.write_file(tuxapp.get_app_root_file_path('arch', 'etc/pacman.d/mirrorlist'), 'Server = {}\n'.format(get_arch_mirror_url('$repo/os/$arch'))) and \
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

configure_debian_container = lambda distribution: \
  tuxapp.write_file(tuxapp.get_app_root_file_path(distribution, 'etc/apt/apt.conf.d/50keep-downloaded-packages'), 'Binary::apt::APT::Keep-Downloaded-Packages "true";\n') and \
  (not is_debian_distribution(distribution) or tuxapp.write_file(tuxapp.get_app_root_file_path(distribution, 'etc/apt/sources.list'), textwrap.dedent('''\
  deb http://deb.debian.org/debian {0} main
  deb http://deb.debian.org/debian-security {0}/updates main
  ''').format(distribution))) and \
  update_debian_container(distribution) and \
  call_root_script(distribution, r'''
  packages=(
    fontconfig-config
    fonts-dejavu-core
    strace
    xkb-data
  )
  DEBIAN_FRONTEND=noninteractive apt install -y "${packages[@]}"
  ''') and \
  (is_debian_distribution(distribution) or tuxapp.write_file(tuxapp.get_app_root_file_path(distribution, 'etc/bash.bashrc'), tuxapp.read_file(tuxapp.get_app_root_file_path(distribution, 'etc/bash.bashrc')).replace('(groups)', '(true)', 1))) and \
  True

detect_missing_app_libraries = \
  tuxapp.do(lambda app, distribution, *args, **kwargs: kwargs['result'] and print('Missing libraries for {} on {}: {}'.format(app, distribution, ', '.join(kwargs['result'])), file=sys.stderr))(
    lambda app, distribution: tuple(sorted(set(library for library in (extract_app_library(app, line) for line in test_app_process(app, distribution).splitlines()) if library)))
  )

execute_app = lambda distribution, app, arguments=(), is_trace=False: tuxapp.execute_process(build_bwrap_arguments(install_missing_container(distribution), app, arguments, is_trace))

execute_root_shell = lambda distribution: tuxapp.execute_process(build_root_bwrap_arguments(install_missing_container(distribution)))

execute_shell = lambda distribution: tuxapp.execute_process(build_bwrap_arguments(install_missing_container(distribution)))

extract_app_library = lambda app, string: \
  '' \
    if extract_library(string) in tuxapp.query_appfile(app, 'ignored-libraries').split() else \
  extract_library(string)

extract_library = lambda string: \
  'libqxcb.so' \
    if ' could not find or load the Qt platform plugin "xcb"' in string else \
  tuxapp.search(r'[\w.-]+\.so\b[\w.]*', string) \
    if '/nacl_helper: error while loading shared libraries: ' not in string else \
  ''

get_app_xauthority_path = lambda app: os.path.join(tuxapp.get_app_path(app), '.Xauthority')

get_arch_mirror_url = lambda path='': os.path.join('https://mirrors.kernel.org/archlinux/', path)

get_arch_package_url = lambda package: get_arch_mirror_url(os.path.join('extra' if package == 'fakechroot' else 'core', 'os/x86_64/'))

get_debian_container_url = lambda distribution: \
  'http://cdimage.ubuntu.com/ubuntu-base/releases/17.10/release/ubuntu-base-17.10-base-amd64.tar.gz' \
    if distribution == 'artful' else \
  'https://download.openvz.org/template/precreated/debian-8.0-x86_64-minimal.tar.gz' \
    if distribution == 'jessie' else \
  'https://download.openvz.org/template/precreated/contrib/debian-9.0-x86_64-minimal.tar.gz' \
    if distribution == 'stretch' else \
  'http://cdimage.ubuntu.com/ubuntu-base/releases/16.04/release/ubuntu-base-16.04.3-base-amd64.tar.gz' \
    if distribution == 'xenial' else \
  None

get_debian_package_url = lambda distribution, package: 'https://{}/{}/{}/{}/download'.format('packages.debian.org' if is_debian_distribution(distribution) else 'packages.ubuntu.com', distribution, tuxapp.detect_debian_architecture(), package)

get_default_distribution = lambda: 'stretch'

get_distribution_cache_path = lambda distribution: \
  '/var/cache/pacman/pkg' \
    if distribution == 'arch' else \
  '/var/cache/apt/archives'

get_distribution_fakeroot_arguments = lambda distribution: \
  ('fakechroot', 'fakeroot') \
    if distribution == 'arch' else \
  ('fakeroot-sysv',)

get_distributions = lambda: tuple(sorted(get_test_distributions()))

get_install_flag_path = lambda distribution: tuxapp.get_app_root_file_path(distribution, os.path.join('var/lib', tuxapp.get_name()))

get_process_timeout = lambda: 3

get_test_distributions = lambda: \
  (
    'stretch',
    'arch',
    'artful',
    'xenial',
    'jessie',
  )

install_arch_container = lambda: \
  tuxapp.unpack_tarball(tuxapp.download_missing_app_temp_file('arch', request_arch_container_url()), tuxapp.get_app_root_path('arch'), ('--strip-components=1',)) and \
  tuxapp.change_file_mode(tuxapp.get_app_root_file_path('arch', 'etc/ca-certificates/extracted/cadir'), lambda mode: mode | stat.S_IWUSR) and \
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
      install_debian_container(distribution)
  )

install_debian_container = lambda distribution: \
  tuxapp.unpack_tarball(tuxapp.download_missing_app_temp_file(distribution, get_debian_container_url(distribution)), tuxapp.get_app_root_path(distribution), ('--exclude={}'.format('./dev' if is_debian_distribution(distribution) else 'dev'),)) and \
  all(install_debian_container_package(distribution, package) for package in ('fakeroot', 'libfakeroot')) and \
  configure_debian_container(distribution)

install_debian_container_package = lambda distribution, package: \
  tuxapp.silence(tuxapp.unpack_package)(tuxapp.download_missing_app_temp_file(distribution, request_debian_package_url(distribution, package)), tuxapp.get_app_root_path(distribution)) and \
  package

install_missing_container = lambda distribution: \
  update_old_container(distribution) and \
  distribution \
    if os.path.isfile(get_install_flag_path(distribution)) else \
  install_container(distribution) and \
  tuxapp.write_file(get_install_flag_path(distribution)) and \
  utilities.update_data((distribution, 'timestamp'), int(time.time())) and \
  distribution

is_app_process_output_ignored = lambda app, output: \
  {
    'subsurface': 'Could not initialize GLX',
    'supertuxkart': 'Fatal error, could not get visual.',
    'viber': 'Could not initialize GLX',
  }.get(app, r'\0') in output

is_debian_distribution = lambda distribution: \
  distribution in (
    'jessie',
    'stretch',
  )

request_arch_container_url = lambda: get_arch_mirror_url('iso/latest/') + tuxapp.request_grep_url(get_arch_mirror_url('iso/latest/'), ('-Po', '-m', '1', r'(?<=")archlinux-bootstrap-[^"]+'))

request_arch_package_url = lambda package: get_arch_package_url(package) + tuxapp.request_grep_url(get_arch_package_url(package), ('-Po', '-m', '1', r'(?<="){}-[^"]+'.format(package)))

request_debian_package_url = lambda distribution, package: \
  (tuxapp.get_debian_mirror_url() if is_debian_distribution(distribution) else tuxapp.get_ubuntu_mirror_url()) + \
  tuxapp.request_grep_url(get_debian_package_url(distribution, package), ('-o', '-m', '1', r'[^/]*/pool/[^"]*'))

test_app = lambda app, distribution=None: \
  test_installed_app(app, distribution) \
    if tuxapp.is_app_installed(app) else \
  (tuxapp.install_app(app) or tuxapp.remove_app(app) and False) and \
  (tuxapp.remove_app(app) if test_installed_app(app, distribution) else tuxapp.remove_app(app) and False)

test_app_process = \
  tuxapp.log('Trying {} on {}')(
  check_app_process_output(
    lambda app, distribution: \
      utilities.install_missing_package('strace') and \
      utilities.install_missing_package('xvfb', 'xvfb-run') and \
      tuxapp.read_process(r'''
      output=$({}timeout -s 9 {} {} 2>&1)
      kill -9 $(echo "$output" | grep -Po '(?<= Process )\d+') 2> /dev/null
      echo "$output"
      '''.format(
        'xvfb-run -a -f {} '.format(tuxapp.quote_argument(get_app_xauthority_path(app))) if tuxapp.is_existing_command('xvfb-run') else '',
        tuxapp.quote_argument(str(get_process_timeout())),
        tuxapp.join_arguments(build_bwrap_arguments(install_missing_container(distribution), app)).replace(' bash ', ' strace -f -e none bash ', 1),
      ), True)
  ))

test_apps = lambda apps: utilities.call_parallel(test_app_worker, apps, 4)

test_installed_app = lambda app, distribution=None: all(not detect_missing_app_libraries(app, distribution) for distribution in ((distribution,) if distribution else get_test_distributions())) # pylint: disable=superfluous-parens

update_arch_container = lambda: call_root_script('arch', r'pacman -Syu --noconfirm')

update_container = lambda distribution: \
  update_arch_container() \
    if distribution == 'arch' else \
  update_debian_container(distribution)

update_debian_container = lambda distribution: \
  call_root_script(distribution, r'''
  apt update
  DEBIAN_FRONTEND=noninteractive apt dist-upgrade -y
  ''')

update_old_container = lambda distribution: \
  update_container(distribution) and \
  tuxapp.remove_old_files(tuxapp.get_app_temp_file_path(distribution, '*'), 30) and \
  utilities.update_data((distribution, 'timestamp'), int(time.time())) \
    if int(utilities.query_data((distribution, 'timestamp')) or '0') < time.time() - 60 * 60 * 24 * 7 else \
  True
