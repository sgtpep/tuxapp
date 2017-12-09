# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

def register(linter):
  import pylint.checkers
  class OrderChecker(pylint.checkers.BaseChecker):
    import pylint.interfaces
    __implements__ = (pylint.interfaces.IAstroidChecker,)
    msgs = {
      'W0001': ('%s %s is misplaced', 'misplaced-item', ''),
      'W0002': ('%s %s is not defined in sorted order', 'unordered-item', ''),
    }
    name = 'order-checker'

    def __init__(self, linter=None):
      super(OrderChecker, self).__init__(linter)
      self.previous_names = {}

    def visit_assignname(self, node):
      import astroid
      if not node.col_offset and isinstance(node.assign_type().value, astroid.Lambda):
        if self.previous_names.get('lambda', '') > node.name:
          self.add_message('unordered-item', args=('Lambda', node.name), node=node)
        self.previous_names['lambda'] = node.name

    def visit_classdef(self, node):
      if not node.col_offset:
        if self.previous_names.get('class', '') > node.name:
          self.add_message('unordered-item', args=('Class', node.name), node=node)
        self.previous_names['class'] = node.name
        if 'function' in self.previous_names or 'lambda' in self.previous_names:
          self.add_message('misplaced-item', args=('Class', node.name), node=node)

    def visit_functiondef(self, node):
      if not node.col_offset:
        import astroid
        if any(isinstance(node, astroid.FunctionDef) and node.name in ('decorator', 'wrapper') for node in node.body):
          if self.previous_names.get('decorator', '') > node.name:
            self.add_message('unordered-item', args=('Decorator', node.name), node=node)
          self.previous_names['decorator'] = node.name
          if 'class' in self.previous_names or 'function' in self.previous_names or 'lambda' in self.previous_names:
            self.add_message('misplaced-item', args=('Decorator', node.name), node=node)
        else:
          if self.previous_names.get('function', '') > node.name:
            self.add_message('unordered-item', args=('Function', node.name), node=node)
          self.previous_names['function'] = node.name
          if 'lambda' in self.previous_names:
            self.add_message('misplaced-item', args=('Function', node.name), node=node)

    def visit_module(self, node):
      self.previous_names = {}

  linter.register_checker(OrderChecker(linter))

  if 'file' in pylint.checkers.utils.builtins:
    del pylint.checkers.utils.builtins['file']
