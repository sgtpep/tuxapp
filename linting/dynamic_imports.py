import astroid
import os

root_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

def register(linter):
  astroid.MANAGER.register_transform(astroid.AssignName, transform)

def transform(node):
  if not node.col_offset and isinstance(node.assign_type().value, astroid.Call) and isinstance(node.assign_type().value.func, astroid.Attribute) and node.assign_type().value.func.attrname == 'load_source':
    class_node = astroid.Class(node.name, None)
    class_node.locals = astroid.MANAGER.ast_from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), node.name)).locals
    node.frame().locals[node.name] = [class_node]
