# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

def _reload(variables, variable):
  def decorator(function):
    import functools
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
      reload()
      try:
        return variables[variable](*args, **kwargs)
      except SystemExit as exception:
        import sys
        print('Exit with code {}'.format(exception.code), file=sys.stderr)
    if not hasattr(wrapper, '__wrapped__'):
      wrapper.__wrapped__ = function
    return wrapper
  return decorator

def main():
  import atexit
  import os
  import readline
  import rlcompleter # pylint: disable=unused-variable
  readline.set_history_length(10000)
  path = os.path.expanduser('~/.python_history')
  if os.path.exists(path):
    readline.read_history_file(path)
  atexit.register(lambda: readline.write_history_file(path))
  reload()

def reload(*args, **kwargs): # pylint: disable=redefined-builtin
  # pylint: disable=too-many-branches, too-many-locals, too-many-nested-blocks
  if args or kwargs:
    try:
      from importlib import reload as builtin_reload
    except ImportError:
      from __builtin__ import reload as builtin_reload
    return builtin_reload(*args, **kwargs)
  else:
    if not hasattr(reload, '__file__'):
      reload.__file__ = __file__
    import glob
    import os
    paths = glob.glob(os.path.join(os.path.dirname(reload.__file__), '*.py'))
    if 'TUXAPP_PATH' in os.environ:
      paths.append(os.environ['TUXAPP_PATH'])
    if not hasattr(reload, 'mtimes'):
      reload.mtimes = {}
    for path in paths:
      if os.path.getmtime(path) != reload.mtimes.get(path):
        reload.mtimes[path] = os.path.getmtime(path)
        name = os.path.splitext(os.path.basename(path))[0]
        if os.path.basename(os.path.dirname(path)) == 'lib':
          module = __import__('lib.{}'.format(name), fromlist=('',))
          import sys
          reload(sys.modules['lib.{}'.format(name)])
        else:
          import imp
          module = imp.load_source(name, path)
        variables = vars(module)
        for variable, value in variables.items():
          new_value = _reload(variables, variable)(value) if callable(value) else value
          if os.path.basename(os.path.dirname(path)) == 'lib':
            if name not in globals():
              import imp
              globals()[name] = imp.new_module(name)
            setattr(globals()[name], variable, new_value)
          elif not hasattr(value, '__file__') or os.path.basename(os.path.dirname(value.__file__)) != 'lib':
            globals()[variable] = new_value

def timeit(*args, **kwargs):
  import timeit # pylint: disable=redefined-outer-name
  return timeit.timeit(*args, number=1, **kwargs)

if __name__ == '__main__':
  main()
