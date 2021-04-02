import ast
import operator
import pdb

a_str = "(x/5)*2-3+SIN(CELL(x, 2, 4))"
b_str = "7/(2-y)"

r_inverses = {
  ast.Add: operator.sub,
  ast.Sub: operator.add,
  ast.Mult: operator.truediv,
  ast.Div: operator.mul,
}

l_inverses = {
  ast.Sub: lambda stack, val: -1*(stack-val),
  ast.Add: operator.sub,
  ast.Div: lambda stack, val: 1/(stack/val),
  ast.Mult: operator.truediv,
}

# `stack` is the accumlated value
def invert(tree, stack, solvefor):
    print('-----------')
    print(ast.dump(tree, indent=2))
    print(f'Accumulated stack: {stack}')
    print(f'Solving for {solvefor}')

    if type(tree) == ast.Name:  # 'x'
        if tree.id == solvefor:
            return stack
        else:
            raise Exception('other vars not supported yet')

    # this is a BinOp with a left, right, and op
    # either left or right is a Constant
    if type(tree.right) == ast.Constant:  # {x} * a
        stack = r_inverses[type(tree.op)](stack, tree.right.value)
        return invert(tree.left, stack, solvefor)
    else:  # a * {x}
        stack = l_inverses[type(tree.op)](stack, tree.left.value)
        return invert(tree.right, stack, solvefor)

if __name__ == '__main__':  

  a = ast.parse(a_str, mode='eval').body
  b = ast.parse(b_str, mode='eval').body
  pdb.set_trace()
  print(f'{a_str}')
  print(invert(a, 10, 'x'))
  #print(f'{b_str}')
  #print(invert(b, 10, 'y'))
