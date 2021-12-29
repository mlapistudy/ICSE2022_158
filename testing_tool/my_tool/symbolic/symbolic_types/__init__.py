# Copyright: see copyright.txt

from .symbolic_int import SymbolicInteger as SymInt
from .symbolic_int import SymbolicObject as SymObj
from .symbolic_dict import SymbolicDict as SymD
from .symbolic_str import SymbolicStr as SymS
from .symbolic_type import SymbolicType as SymType
from .symbolic_float import SymbolicFloat as SymFloat

SymObj.wrap = lambda conc, sym : SymbolicInteger("se",conc,sym)
SymbolicInteger = SymInt
SymbolicDict = SymD
SymbolicStr = SymS
SymbolicType = SymType
SymbolicFloat = SymFloat

def getSymbolic(v):
	exported = [(int,SymbolicInteger),(dict,SymbolicDict),(str,SymbolicStr),(float,SymbolicFloat)]# exported = [(int,SymbolicInteger),(dict,SymbolicDict),(str,SymbolicStr)]
	for (t,s) in exported:
		if isinstance(v,t):
			return s
	return None



