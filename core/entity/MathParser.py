# lex/parse for equations in `TABLE/AXIS/MATH` and `CONSTANT/MATH` equations.
# used to get a function tree upon which numpy functions will be mapped to 
# translate from binary data
# see: https://github.com/dabeaz/sly/blob/master/example/calc/calc.py
from sly import Lexer, Parser

class MathLexer(Lexer):
  # ignore whitespace
  ignore = ' \t'
  tokens = {
    # ...general syntax
    NAME,
    # ...keywords
    TRUE, FALSE, HEX_LITERAL,
    # ...signed int, decimal, OR hex literal
    NUMBER,
    L_PAREN, R_PAREN,
    # ...math operators
    PLUS, MINUS, TIMES, DIVIDE, MODULO,
    #...comparison
    EQUALITY, GREATER_THAN, LESS_THAN, GREATER_THAN_EQUAL,
    LESS_THAN_EQUAL, NOT_EQUAL,
    # ...logical operators
    LOGICAL_OR, LOGICAL_AND, BITWISE_LEFT, BITWISE_RIGHT,
    BITWISE_OR, BITWISE_AND, BITWISE_XOR, BITWISE_NOR, BITWISE_NAND,
    # ...'functions' - map to numpy api
    ABS, AVG, EXP, LOG, POW, SQR, SUM, LOG10, RADIANS, DEGREES,
    # if(condition, true, false) is an expression like everything else - recursive.
    # tunerpro help warns to avoid circular references e.g. CELL
    IF,
    ROUND, MROUND, SIN, COS, TAN, SINH, COSH, TANH, ASINH, ACOSH,
    ATANH, ASIN, ACOS, ATAN,
    # XDF FUNCTIONS
    ADDRESS, THIS, THAT,
    # ...table functions
    ROW, COL, ROWS, COLS, CELL,
    # ...axis functions
    INDEX, INDEXES, CELL
    # xdf help hints to some sort of uninmplemented set of scalar functions?
  }
  # specifiy regexes for tokens
  NAME = r'[a-zA-Z_][a-zA-Z0-9_]*'
  # ...keywords
  TRUE = r'true|TRUE'
  FALSE = r'false|FALSE'
  HEX_LITERAL = r'0[xX][0-9a-fA-F]+'
  NUMBER = r'\d+'
  LPAREN = r'\('
  RPAREN = r'\)'
  PLUS = r'\+'
  MINUS = r'-'
  TIMES = r'\*'
  DIVIDE = r'/'
  MODULO = r'%'
  EQUALITY = r'=='
  GREATER_THAN = r'>'
  LESS_THAN = r'<'
  GREATER_THAN_EQUAL = r'>='
  LESS_THAN_EQUAL = r'<='
  NOT_EQUAL = r'!='
  LOGICAL_OR = r'\|\|'
  LOGICAL_AND = r'&&'
  BITWISE_LEFT = r'<<'
  BITWISE_RIGHT = r'>>'
  BITWISE_OR = '\|'
  BITWISE_AND = '&'
  BITWISE_XOR = '\^'
  BITWISE_NOR = '!\|'
  BITWISE_NAND = '!&'
  # ...functions
  ABS = 'ABS'
  
  
  # Ignored pattern
  ignore_newline = r'\n+'
  # Extra action for newlines
  def ignore_newline(self, t):
    self.lineno += t.value.count('\n')

  def error(self, t):
    print("Illegal character '%s'" % t.value[0])
    self.index += 1
    
class MathParser(Parser):
  tokens = MathLexer.tokens
  # precedence ordered low to high
  precedence = (
    ('left', PLUS, MINUS),
    ('left', TIMES, DIVIDE),
    ('right', UMINUS)
  )

  def __init__(self):
    self.names = { }

  # example had statements - we do not, only closed form expressions
  @_('expr')
  def statement(self, p):
    print(p.expr)

  @_('expr PLUS expr')
  def expr(self, p):
    return p.expr0 + p.expr1

  @_('expr MINUS expr')
  def expr(self, p):
    return p.expr0 - p.expr1

  @_('expr TIMES expr')
  def expr(self, p):
    return p.expr0 * p.expr1

  @_('expr DIVIDE expr')
  def expr(self, p):
    return p.expr0 / p.expr1

  @_('MINUS expr %prec UMINUS')
  def expr(self, p):
    return -p.expr

  @_('LPAREN expr RPAREN')
  def expr(self, p):
    return p.expr

  @_('NUMBER')
  def expr(self, p):
    return int(p.NUMBER)

  @_('NAME')
  def expr(self, p):
    try:
      return self.names[p.NAME]
    except LookupError:
      print(f'Undefined name {p.NAME!r}')
      return 0