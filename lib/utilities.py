# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import functools
import os
import sys

from lib import (
  tuxapp,
)

@tuxapp.silence
def call_parallel(function, iterable, number=10):
  import contextlib
  import multiprocessing
  with contextlib.closing(multiprocessing.Pool(number)) as pool:
    return functools.reduce(lambda result, process_result: result and process_result, pool.imap_unordered(functools.partial(call_parallel_worker, function), iterable), True)

def call_parallel_worker(function, item):
  try:
    return function(item)
  except AssertionError as exception:
    if exception.args:
      print(exception.args[0], file=sys.stderr)
    return False
  except: # pylint: disable=bare-except
    import traceback
    traceback.print_exc()
    print(file=sys.stderr)
    return False

@tuxapp.check(lambda path, *args, **kwargs: 'Unknown image format: {}'.format(os.path.basename(path)))
def detect_image_extension(path):
  if 'imghdr' not in sys.modules:
    import imghdr
    imghdr.tests.append(lambda header, file: (b'<?xml ' in header or b'<svg ' in header) and 'svg')
    imghdr.tests.append(lambda header, file: header[:4] == b'\0\0\1\0' and 'ico')
  return sys.modules['imghdr'].what(path)

build_github_url = lambda repository, url='': repository and 'https://github.com/{}{}'.format(repository, url and '/{}'.format(url))

call_process_verbose = \
  tuxapp.log('Running the command: {}')(
    lambda arguments: tuxapp.call_process(arguments)
  )

connect_data = lambda: tuxapp.connect_data(get_data_path())

get_data_path = lambda: os.path.join(tuxapp.get_app_path(tuxapp.get_name()), 'data')

get_github_url_pattern = lambda: r'(?<!\.)\bgithub\.com/([\w-]+/[\w-]+)'

install_missing_package = lambda package, command=None: \
  tuxapp.is_existing_command(command or package) or \
  install_package(package)

install_package = \
  tuxapp.log('Installing {}')(
  tuxapp.check('{} is not installed')(
    lambda package: \
      not tuxapp.is_silent() and \
      tuxapp.is_existing_command('apt') and \
      call_process_verbose('sudo apt update && sudo apt install -y {}'.format(tuxapp.quote_argument(package)))
  ))

open_url = \
  tuxapp.do(lambda url, *args, **kwargs: url and tuxapp.is_existing_command('xdg-open') and tuxapp.call_process('xdg-open {} > /dev/null 2>&1 &'.format(tuxapp.quote_argument(url))))(
    lambda url: url
  )

query_data = lambda key: tuxapp.query_data(get_data_path(), key)

update_data = lambda key, value='': tuxapp.update_data(get_data_path(), key, value)

update_data_items = lambda items: tuxapp.update_data_items(get_data_path(), items)
