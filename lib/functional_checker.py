import astroid
import pylint.checkers
import pylint.interfaces

class FunctionalChecker(pylint.checkers.BaseChecker):
  __implements__ = (pylint.interfaces.IAstroidChecker,)
  name = 'functional-checker'
  previous_function_name = None

  msgs = {
    'W0001': ("Variable %s is re-assigned", 'reassigned-variable', ''),
    'W0002': ("Function %s is not defined in sorted order", 'unordered-function-definition', ''),
    'W0003': ("Function %s has imperative statements in its body", 'imperative-function-body', ''),
    'W0004': ("Function %s has no return statement at the end", 'function-without-return', ''),
  }

  def visit_assignname(self, node): # pylint: disable=imperative-function-body
    frame = node.frame()
    if node.name in frame.locals and getattr(frame.locals[node.name][0], 'is_defined', None):
      self.add_message('reassigned-variable', args=node.name, node=node)
    elif node.name != '_':
      node.is_defined = True

  def visit_functiondef(self, node): # pylint: disable=imperative-function-body
    if not node.col_offset:
      if node.name < self.previous_function_name:
        self.add_message('unordered-function-definition', args=node.name, node=node)
      self.previous_function_name = node.name
    body = node.body[:-1] if isinstance(node.body[-1], astroid.Return) else node.body
    if not all(isinstance(child, astroid.Assign) for child in body):
      self.add_message('imperative-function-body', args=node.name, node=node)
    elif not isinstance(node.body[-1], astroid.Return):
      self.add_message('function-without-return', args=node.name, node=node)

def register(linter): # pylint: disable=imperative-function-body
  linter.register_checker(FunctionalChecker(linter))
