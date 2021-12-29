# Copyright: copyright.txt

from . symbolic_type import SymbolicObject

#newly added, modified from symbolic_int

class SymbolicFloat(SymbolicObject,float):
  def __new__(cls, name, v, expr=None):
    return float.__new__(cls, v)

  def __init__(self, name, v, expr=None):
    SymbolicObject.__init__(self, name, expr)
    self.val = v

  def getConcrValue(self):
    return self.val

  def wrap(conc,sym):
    return SymbolicFloat("se",conc,sym)

  def __hash__(self):
    return hash(self.val)

  def _op_worker(self,args,fun,op):
    return self._do_sexpr(args, fun, op, SymbolicFloat.wrap)

# now update the SymbolicInteger class for operations we
# will build symbolic terms for

# ops =  [("add",    "+"  ),\
#   ("sub",    "-"  ),\
#   ("mul",    "*"  ),\
#   ("mod",    "%"  ),\
#   ("floordiv", "//" ),\
#   ("and",    "&"  ),\
#   ("or",     "|"  ),\
#   ("xor",    "^"  ),\
#   ("lshift", "<<" ),\
#   ("rshift", ">>" ) ]
ops =  [("add",    "+"  ),\
  ("sub",    "-"  ),\
  ("mul",    "*"  ),
  ("div", "/" ) ]

def make_method(method,op,a):
  code  = "def %s(self,other):\n" % method
  code += "   return self._op_worker(%s,lambda x,y : x %s y, \"%s\")" % (a,op,op)
  locals_dict = {}
  exec(code, globals(), locals_dict)
  setattr(SymbolicFloat,method,locals_dict[method])

for (name,op) in ops:
  method  = "__%s__" % name
  make_method(method,op,"[self,other]")
  rmethod  = "__r%s__" % name
  make_method(rmethod,op,"[other,self]")

