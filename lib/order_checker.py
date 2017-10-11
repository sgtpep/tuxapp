import astroid
import pylint.checkers
import pylint.interfaces

class OrderChecker(pylint.checkers.BaseChecker):
  __implements__ = (pylint.interfaces.IAstroidChecker,)
  name = 'order-checker'
  previous_decorator = None
  previous_function = None
  previous_lambda = None

  msgs = {
    'W0001': ("Decorator %s is not defined in sorted order", 'unordered-decorator', ''),
    'W0002': ("Function %s is not defined in sorted order", 'unordered-function', ''),
    'W0003': ("Lambda %s is not defined in sorted order", 'unordered-lambda', ''),
  }

  def visit_assignname(self, node):
    if not node.col_offset and isinstance(node.assign_type().value, astroid.Lambda):
      if self.previous_lambda and self.previous_lambda > node.name:
        self.add_message('unordered-lambda', args=node.name, node=node)
      self.previous_lambda = node.name

  def visit_functiondef(self, node):
    if not node.col_offset:
      if len(node.body) >= 2 and isinstance(node.body[-2], astroid.FunctionDef) and isinstance(node.body[-1], astroid.Return):
        if self.previous_decorator and self.previous_decorator > node.name:
          self.add_message('unordered-decorator', args=node.name, node=node)
        self.previous_decorator = node.name
      else:
        if self.previous_function and self.previous_function > node.name:
          self.add_message('unordered-function', args=node.name, node=node)
        self.previous_function = node.name

def register(linter):
  linter.register_checker(OrderChecker(linter))
