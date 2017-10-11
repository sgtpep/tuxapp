import astroid
import pylint.checkers
import pylint.interfaces

class OrderChecker(pylint.checkers.BaseChecker):
  __implements__ = (pylint.interfaces.IAstroidChecker,)
  decorator = None
  function = None
  name = 'order-checker'
  variable = None

  msgs = {
    'W0001': ("Decorator %s is not defined in sorted order", 'unordered-decorator', ''),
    'W0002': ("Function %s is not defined in sorted order", 'unordered-function', ''),
    'W0003': ("Variable %s is not defined in sorted order", 'unordered-variable', ''),
  }

  def visit_assignname(self, node):
    if not node.col_offset:
      if self.variable and self.variable > node.name:
        self.add_message('unordered-variable', args=node.name, node=node)
      self.variable = node.name

  def visit_functiondef(self, node):
    if not node.col_offset:
      if len(node.body) == 2 and isinstance(node.body[0], astroid.FunctionDef) and isinstance(node.body[1], astroid.Return):
        if self.decorator and self.decorator > node.name:
          self.add_message('unordered-decorator', args=node.name, node=node)
        self.decorator = node.name
      else:
        if self.function and self.function > node.name:
          self.add_message('unordered-function', args=node.name, node=node)
        self.function = node.name

def register(linter):
  linter.register_checker(OrderChecker(linter))
