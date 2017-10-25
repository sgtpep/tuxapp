import astroid
import pylint.checkers
import pylint.interfaces

class OrderChecker(pylint.checkers.BaseChecker):
  __implements__ = (pylint.interfaces.IAstroidChecker,)
  name = 'order-checker'
  previous_class = None
  previous_decorator = None
  previous_function = None
  previous_lambda = None

  msgs = {
    'W0001': ("%s %s is misplaced", 'misplaced-item', ''),
    'W0002': ("%s %s is not defined in sorted order", 'unordered-item', ''),
  }

  def visit_assignname(self, node):
    if not node.col_offset and isinstance(node.assign_type().value, astroid.Lambda):
      if self.previous_lambda and self.previous_lambda > node.name:
        self.add_message('unordered-item', args=("Lambda", node.name), node=node)
      self.previous_lambda = node.name

  def visit_classdef(self, node):
    if not node.col_offset:
      if self.previous_class and self.previous_class > node.name:
        self.add_message('unordered-item', args=("Class", node.name), node=node)
      self.previous_class = node.name
      if self.previous_function or self.previous_lambda:
        self.add_message('misplaced-item', args=("Class", node.name), node=node)

  def visit_functiondef(self, node):
    if not node.col_offset:
      if len(node.body) >= 2 and isinstance(node.body[-2], astroid.FunctionDef) and isinstance(node.body[-1], astroid.Return):
        if self.previous_decorator and self.previous_decorator > node.name:
          self.add_message('unordered-item', args=("Decorator", node.name), node=node)
        self.previous_decorator = node.name
        if self.previous_class or self.previous_function or self.previous_lambda:
          self.add_message('misplaced-item', args=("Decorator", node.name), node=node)
      else:
        if self.previous_function and self.previous_function > node.name:
          self.add_message('unordered-item', args=("Function", node.name), node=node)
        self.previous_function = node.name
        if self.previous_lambda:
          self.add_message('misplaced-item', args=("Function", node.name), node=node)

def register(linter):
  linter.register_checker(OrderChecker(linter))
