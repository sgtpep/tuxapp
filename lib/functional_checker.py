import astroid
import pylint.checkers
import pylint.interfaces

class FunctionalChecker(pylint.checkers.BaseChecker):
  __implements__ = (pylint.interfaces.IAstroidChecker,)
  name = 'functional-checker'
  previous_function = None

  msgs = {
    'W0001': ("Variable %s is re-assigned", 'reassigned-variable', ''),
    'W0002': ("Function %s is not defined in sorted order", 'unordered-function', ''),
    'W0003': ("Function %s has imperative statements in its body", 'imperative-function', ''),
    'W0004': ("Function %s has no return statement at the end", 'no-return', ''),
  }

  def is_decorator(self, node):
    return len(node.body) == 2 and isinstance(node.body[0], astroid.FunctionDef) and isinstance(node.body[1], astroid.Return)

  def visit_assignname(self, node):
    frame = node.frame()
    if node.name in frame.locals and getattr(frame.locals[node.name][0], 'is_defined', None):
      self.add_message('reassigned-variable', args=node.name, node=node)
    elif node.name != '_':
      node.is_defined = True

  def visit_functiondef(self, node):
    if not node.col_offset:
      if self.previous_function and self.previous_function.name > node.name:
        if not self.is_decorator(self.previous_function) or self.is_decorator(node):
          self.add_message('unordered-function', args=node.name, node=node)
      self.previous_function = node
    if not self.is_decorator(node):
      body = node.body[:-1] if isinstance(node.body[-1], astroid.Return) \
        else node.body
      if not all(isinstance(child, astroid.Assign) for child in body):
        self.add_message('imperative-function', args=node.name, node=node)
      elif not isinstance(node.body[-1], astroid.Return):
        self.add_message('no-return', args=node.name, node=node)

def register(linter):
  linter.register_checker(FunctionalChecker(linter))
