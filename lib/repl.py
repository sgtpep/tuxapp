from __future__ import print_function

def main(): # pylint: disable=imperative-function-body
  import atexit
  import os
  import readline
  import rlcompleter # pylint: disable=unused-variable
  history_path = os.path.expanduser("~/.python_history")
  readline.set_history_length(10000)
  os.path.exists(history_path) and readline.read_history_file(history_path)
  atexit.register(lambda: readline.write_history_file(history_path))
  reload()

def reload(*args, **kwargs): # pylint: disable=imperative-function-body, redefined-builtin
  if args or kwargs:
    return __builtins__.reload(*args, **kwargs)
  else:
    import imp
    import inspect
    import os
    if len(inspect.stack()) <= 3:
      module_paths = ["{}/tuxapp".format(os.path.dirname(os.path.dirname(reload.__file__)))]
      os.environ.get('REPL_PATH') and os.path.basename(os.environ['REPL_PATH']) != 'tuxapp' and module_paths.append(os.environ['REPL_PATH'])
      for module_path in module_paths:
        module_mtime = os.path.getmtime(module_path)
        module_name = os.path.basename(module_path)
        if module_mtime != reload.module_mtimes.get(module_name):
          reload.module_mtimes[module_name] = module_mtime
          module_variables = vars(imp.load_source(module_name, module_path))
          get_module_function_decorator = lambda module_variables, module_variable_name: lambda *args, **kwargs: reload() or module_variables[module_variable_name](*args, **kwargs) # pylint: disable=undefined-variable
          globals().update({module_variable_name: get_module_function_decorator(module_variables, module_variable_name) if hasattr(module_variable_value, '__call__') else module_variable_value for module_variable_name, module_variable_value in module_variables.items() if not module_variable_name.startswith('__')})
          print("Reloaded {}".format(module_name))
reload.__file__ = __file__
reload.module_mtimes = {}

def trace(*args, **kwargs): # pylint: disable=imperative-function-body
  import trace as trace_
  return trace_.Trace().runfunc(*args, **kwargs)

main()
