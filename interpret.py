#!/usr/bin/env python3

"""
VUT FIT IPP Project 2021, part 2.
IPPcode21 Interpreter

Author: David Czirok, xcziro00
"""
import xml.etree.ElementTree as xml
import re, sys, argparse, os.path
from os import path

# Error codes
EXIT_SUCCESS   = 0	# Successful execution
FILE_IO_ERR    = 11 # File doesn't exist or cannot be opened
BAD_PARAMS_ERR = 10 # Wrong parameter or wrong combination

WRONG_XML_ERR  = 31 # Not "Well-formed" input xml  
LEX_OR_SYN_ERR = 32 # Uknown/unsupported xml element, order or other lex., sem. errors in input xml

SEM_ERR52 = 52 # Undefined label or redefinition of variable
SEM_ERR53 = 53 # Wrong operand types
SEM_ERR54 = 54 # Undefined variable, frame exists
SEM_ERR55 = 55 # Frame does not exist
SEM_ERR56 = 56 # Missing value (in variables, or data stack, call stack)
SEM_ERR57 = 57 # Wrong operand type (division by zero, wrong return code for EXIT)
SEM_ERR58 = 58 # String manipulation error

UNDEF = "undefined"

''' =================== FUNCTIONS AND CLASSES =================== '''
def error_exit(message, exit_code):
	print("Error: " + message, file=sys.stderr)
	exit(exit_code)

class VarData:
	''' Structure to hold variable type and value'''
	def __init__(self, value_type, value):
		self.type = value_type;
		self.value = value;

class Inst:
	''' Class for handling and processing instructions'''
	def __init__(self):
		self.global_frame = {}
		self.is_tmp = False;
		self.local_frame = []
		self.temp_frame = {}
		
		self.inst_index = 0
		self.inst_stack = []
		self.inst_list = []
		
		self.labels = []
		
		self.stack = []
		
		self.is_source = False;
		self.is_input = False;
		self.input_text = []
		self.input = ""
		self.source = ""

	def load_file(self):
		with open(self.input) as f:
			for i in f: self.input_text.insert(0, i.rstrip())

	def increment_index(self): self.inst_index += 1 

	def fetch_instruction(self): return self.inst_list[self.inst_index]

	def check_arg_count(self, arguments, argc):
		if len(arguments) != argc:
			error_exit("Wrong argument count for instruction...", LEX_OR_SYN_ERR)

	def check_var_types(self, type1, type2):
		if UNDEF in [type1, type2]: error_exit("Variable value undefined...", SEM_ERR56)
		if type1 != type2: error_exit("Wrong operand types...", SEM_ERR53)

	def check_var_errors(self, var):
		name = (var.split("@")[1])
		if "GF" in var:
			if name not in self.global_frame:
				error_exit("Variable " + var + " undefined.", SEM_ERR54)
		elif "LF" in var:
			if not self.local_frame:
				error_exit("Frame does not exist.", SEM_ERR55)
			elif name not in self.local_frame[-1]:
				error_exit("Variable " + var + " undefined.", SEM_ERR54)
		elif "TF" in var:
			if not self.is_tmp:
				error_exit("Frame does not exist.", SEM_ERR55)
			elif name not in self.temp_frame:
				error_exit("Variable " + var + " undefined.", SEM_ERR54)

	def get_frame(self, var):
		if "GF" in var: return self.global_frame
		if "LF" in var: return self.local_frame[-1]
		if "TF" in var: return self.temp_frame

	def set_frame_variable(self, var, vtype, value):
		frame, name = var.split('@')
		self.get_frame(frame)[name] = VarData(vtype, value)

	def get_arg_info(self, argument):
		if argument.attrib["type"] == "var":
			self.check_var_errors(argument.text)
			frame, name = argument.text.split('@')
			variable = self.get_frame(frame)[name]
			return variable.type, variable.value
		else:
			vtype = argument.attrib["type"]
			value = argument.text
			if vtype == "string":
				if value == None: value = ""
				else: value = re.sub(r"\\(\d{3})", lambda w: chr(int(w.group(1))), value)
			elif vtype == "int":
				try:
					value = int(value)
				except:
					error_exit("Cannot convert " + value + " to integer...", LEX_OR_SYN_ERR)
			return vtype, value

	def stack_push(self, vtype, value): self.stack.append(VarData(vtype, value))

	def stack_pop(self): 
		if not self.stack: error_exit("Stack is empty...", SEM_ERR56)
		return self.stack.pop()

	# CREATEFRAME
	def createframe(self, args):
		self.is_tmp = True
		self.temp_frame = {}

	# PUSHFRAME
	def pushframe(self, args):
		if not self.is_tmp:  error_exit("Frame does not exist", SEM_ERR55)
		self.is_tmp = False
		self.local_frame.append(self.temp_frame.copy())
	
	# POPFRAME
	def popframe(self, args):
		if not self.local_frame: error_exit("Frame does not exist", SEM_ERR55)
		self.is_tmp = True;
		self.temp_frame = self.local_frame.pop()
		
	# DEFVAR <var>
	def defvar(self, args):
		self.check_arg_count(args, 1)
		var = args[0].text
		frame, name = var.split('@')
		
		if "GF" in var:
			if name in self.global_frame: 
				error_exit("Variable " + var +" already defined.", SEM_ERR52)

		elif "LF" in var:
			if not self.local_frame: 
				error_exit("Local frame does not exist", SEM_ERR55)
			elif name in self.local_frame[-1]:
				error_exit("Variable " + var +" already defined.", SEM_ERR52)

		elif "TF" in var:
			if self.is_tmp == False:
				error_exit("Temporary frame does not exist", SEM_ERR55)
			elif name in self.temp_frame:
				error_exit("Variable " + var +" already defined.", SEM_ERR52)
			
		self.set_frame_variable(var, UNDEF, 0)

	# MOVE <var> <symb>
	def move(self, args):
		self.check_arg_count(args, 2)
		arg1_type, arg1_value = self.get_arg_info(args[0])
		arg2_type, arg2_value = self.get_arg_info(args[1])

		if arg2_type == UNDEF: error_exit("Variable " + args[1].text + " undefined...", SEM_ERR56)

		self.set_frame_variable(args[0].text, arg2_type, arg2_value)

	# WRITE <symb>
	def write(self, args):
		self.check_arg_count(args, 1)
		arg1_type, arg1_value = self.get_arg_info(args[0])
		if arg1_type == UNDEF: error_exit("Variable " + args[0].text + " undefined...", SEM_ERR56)
		if arg1_type == "nil": arg1_value = ""
		if self.fetch_instruction().attrib["opcode"].upper() == "DPRINT":
			print(arg1_value, end='', file=sys.stderr)
		else:
			print(arg1_value, end='')

	# READ <var> <type>
	def read(self, args):
		self.check_arg_count(args, 2)

		arg1_type, arg1_value = self.get_arg_info(args[0])
		arg2_type, arg2_value = self.get_arg_info(args[1])

		if arg2_value not in ["int", "string", "bool"]:
			error_exit("Bad type to read " + arg2_value + "...", SEM_ERR53) 
		
		# Load input
		try:
			if self.is_input: read_var = self.input_text.pop()
			else: read_var = input()
		
			if arg2_value == "int":
				result = int(read_var)
			elif arg2_value == "bool":
				if read_var.upper() == "TRUE": result = "true"
				else: result = "false"
			else:
				result = re.sub(r"\\(\d{3})", lambda w: chr(int(w.group(1))), read_var)
		except:
			arg2_value = "nil"
			result = "nil"

		self.set_frame_variable(args[0].text, arg2_value, result)

	# PUSHS <symb>
	def pushs(self, args):
		self.check_arg_count(args, 1)

		arg1_type, arg1v = self.get_arg_info(args[0])
		if arg1_type == UNDEF: error_exit("Variable undefined...", SEM_ERR56)

		self.stack_push(arg1_type, arg1v)

	# POPS <var>
	def pops(self, args):
		self.check_arg_count(args, 1)
		
		arg1_type, arg1_value = self.get_arg_info(args[0])

		variable = self.stack_pop()
		self.set_frame_variable(args[0].text, variable.type, variable.value)

	# ADD, SUB, MUL, IDIV <var> <symb1> <symb2>
	def arithmetic_operators(self, args):
		self.check_arg_count(args, 3)

		res0_type, res0v = self.get_arg_info(args[0])
		arg1_type, arg1v = self.get_arg_info(args[1])
		arg2_type, arg2v = self.get_arg_info(args[2])

		self.check_var_types(arg1_type, "int")
		self.check_var_types(arg2_type, "int")
		if res0_type != UNDEF: self.check_var_types(res0_type, "int")

		result = args[0].text
		inst_name = self.fetch_instruction().attrib["opcode"].upper()

		if inst_name == "ADD": res0v = (arg1v + arg2v)
		if inst_name == "SUB": res0v = (arg1v - arg2v)
		if inst_name == "MUL": res0v = (arg1v * arg2v)
		if inst_name == "IDIV": 
			if arg2v == 0: error_exit("Division by zero...", SEM_ERR57)
			res0v = (arg1v // arg2v)
		
		self.set_frame_variable(result, "int", res0v)

	# AND, OR, NOT, LT, GT, EQ <var> <symb1> <symb2> 
	def logical_operators(self, args):
		inst_name = self.fetch_instruction().attrib["opcode"].upper()
		
		if inst_name == "NOT": self.check_arg_count(args, 2)
		else: self.check_arg_count(args, 3)

		res0_type, res0v = self.get_arg_info(args[0])
		arg1_type, arg1v = self.get_arg_info(args[1])
		
		result = args[0].text
		if inst_name == "NOT":
			self.check_var_types(arg1_type, "bool")
			if arg1v == "true": 
				self.set_frame_variable(result, "bool", "false")
			else: 
				self.set_frame_variable(result, "bool", "true")

		elif inst_name in ["AND", "OR"]:
			arg2_type, arg2v = self.get_arg_info(args[2])
			self.check_var_types(arg1_type, "bool")
			self.check_var_types(arg2_type, "bool")

			if((inst_name == "AND" and arg1v == "true" and arg2v == "true") 
			or (inst_name == "OR" and (arg1v == "true" or arg2v == "true"))):
				self.set_frame_variable(result, "bool", "true")
			else:
				self.set_frame_variable(result, "bool", "false")

		elif inst_name in ["LT", "GT", "EQ"]:
			arg2_type, arg2v = self.get_arg_info(args[2])
			# nil
			if inst_name == "EQ" and (arg1_type == "nil" or arg2_type == "nil"): ...
			elif arg1_type == "nil" or arg2_type == "nil": 
				error_exit("Cannot compare nil...", SEM_ERR53)
			else: self.check_var_types(arg1_type, arg2_type)

			if((inst_name == "EQ" and arg1v == arg2v) 
			or (inst_name == "LT" and arg1v < arg2v) 
			or (inst_name == "GT" and arg1v > arg2v)):
				self.set_frame_variable(result, "bool", "true")
			else:
				self.set_frame_variable(result, "bool", "false")
	
	# TYPE <var> <symb>
	def type(self, args):
		self.check_arg_count(args, 2)

		res0_type, res0v = self.get_arg_info(args[0])
		arg1_type, arg1v = self.get_arg_info(args[1])

		res0v = "" if arg1_type == UNDEF else arg1_type

		self.set_frame_variable(args[0].text, "string", res0v)

	# INT2CHAR <var> <symb>
	def int2char(self, args):
		self.check_arg_count(args, 2)

		res0_type, res0v = self.get_arg_info(args[0])
		arg1_type, arg1v = self.get_arg_info(args[1])
		
		self.check_var_types(arg1_type, "int")
		try:
			self.set_frame_variable(args[0].text, "string", chr(arg1v))
		except: 
			error_exit("Cannot convert given int to char...", SEM_ERR58)

	# STRI2INT <var> <symb>
	def stri2int(self, args):
		self.check_arg_count(args, 3)

		res0_type, res0v = self.get_arg_info(args[0])
		arg1_type, arg1v = self.get_arg_info(args[1])
		arg2_type, arg2v = self.get_arg_info(args[2])
		
		self.check_var_types(arg1_type, "string")
		self.check_var_types(arg2_type, "int")

		try:
			assert(arg2v >= 0)
			self.set_frame_variable(args[0].text, "int", ord(arg1v[arg2v]))
		except:
			error_exit("Cannot convert given int to char...", SEM_ERR58)

	# CONCAT <var> <symb1> <symb2>
	def concat(self, args):
		self.check_arg_count(args, 3)

		res0_type, res0v = self.get_arg_info(args[0])
		arg1_type, arg1v = self.get_arg_info(args[1])
		arg2_type, arg2v = self.get_arg_info(args[2])

		self.check_var_types(arg1_type, "string")
		self.check_var_types(arg2_type, "string")

		self.set_frame_variable(args[0].text, "string", arg1v + arg2v)

	# STRLEN <var> <symb>
	def strlen(self, args):
		self.check_arg_count(args, 2)

		res0_type, res0v = self.get_arg_info(args[0])
		arg1_type, arg1v = self.get_arg_info(args[1])
		
		self.check_var_types(arg1_type, "string")
		self.set_frame_variable(args[0].text, "int", len(arg1v))

	# GETCHAR <var> <symb1> <symb2>
	def getchar(self, args):
		self.check_arg_count(args, 3)

		res0_type, res0v = self.get_arg_info(args[0])
		arg1_type, arg1v = self.get_arg_info(args[1])
		arg2_type, arg2v = self.get_arg_info(args[2])

		self.check_var_types(arg1_type, "string")
		self.check_var_types(arg2_type, "int")

		try:
			assert(arg2v >= 0)
			self.set_frame_variable(args[0].text, "string", list(arg1v)[arg2v])
		except:
			error_exit("Cannot get given character...", SEM_ERR58)

	# SETCHAR <var> <symb1> <symb2>
	def setchar(self, args):
		self.check_arg_count(args, 3)

		res0_type, res0v = self.get_arg_info(args[0])
		arg1_type, arg1v = self.get_arg_info(args[1])
		arg2_type, arg2v = self.get_arg_info(args[2])
		
		self.check_var_types(arg1_type, "int")
		self.check_var_types(arg2_type, "string")
		self.check_var_types(res0_type, "string")

		try:
			assert(arg1v >= 0)
			res0v = list(res0v)
			res0v[arg1v] = arg2v[0]
			self.set_frame_variable(args[0].text, "string", "".join(res0v))
		except:
			error_exit("Cannot set given character...", SEM_ERR58)

	# BREAK 
	def _break(self, args):
		self.check_arg_count(args, 0)

		print("Inst number: @", GLOBAL_LOC, file=sys.stderr)
		print("-- GLOBAL FRAME --", file=sys.stderr)
		for x in self.global_frame:
			print(x, self.global_frame[x].value_type, "@", self.global_frame[x].value, file=sys.stderr)
		print("-- LOCAL FRAME -- ", file=sys.stderr)
		for frame in self.local_frame:
			print("---", file=sys.stderr)
			for x in frame:
				print(x, frame[x].value_type, "@", frame[x].value, file=sys.stderr)
		print("-- TEMPORARY FRAME --", file=sys.stderr)
		for x in self.temp_frame:
			print(x, self.temp_frame[x].value_type, "@", self.temp_frame[x].value, file=sys.stderr)

	# CALL <label>
	def _call(self, args):
		self.inst_stack.append(self.inst_index)
		
		# Find and set label instruction index
		label = [l for l in self.labels if (l[0].text == args[0].text)]
		if not label: error_exit("Label " + args[0].text + " does not exist", SEM_ERR52)
			
		self.inst_index = self.inst_list.index(label[0])

	# JUMP <label>
	def jump(self, args):
		self.check_arg_count(args, 1)

		label = [l for l in self.labels if (l[0].text == args[0].text)]
		if not label: error_exit("Label " + args[0].text + " does not exist", SEM_ERR52)

		self.inst_index = self.inst_list.index(label[0])
	
	# JUMPIFEQ, JUMPIFNEQ <label> <symb1> <symb2>
	def jumpif(self, args):
		self.check_arg_count(args, 3)

		label = [l for l in self.labels if (l[0].text == args[0].text)]
		if not label: error_exit("Label " + args[0].text + " does not exist", SEM_ERR52)

		arg1_type, arg1v = self.get_arg_info(args[1])
		arg2_type, arg2v = self.get_arg_info(args[2])

		if UNDEF in [arg1_type, arg2_type]: error_exit("Variable undefined...", SEM_ERR56)

		inst_name = self.fetch_instruction().attrib["opcode"].upper()
		if (arg1_type == arg2_type) or ("nil" in [arg1_type, arg2_type]):
			if ((inst_name == "JUMPIFEQ" and arg1v == arg2v) 
			or (inst_name == "JUMPIFNEQ" and arg1v != arg2v)):
				self.inst_index = self.inst_list.index(label[0])
		else:
			error_exit("Bad operand types...", SEM_ERR53)

	# RETURN
	def _return(self, args):
		if not self.inst_stack: error_exit("Call stack is empty...", SEM_ERR56)
		self.inst_index = self.inst_stack.pop()

	# LABEL <label>
	def label(self, args): 
		self.check_arg_count(args, 1)
		return

	# EXIT <symb>
	def _exit(self, args):
		self.check_arg_count(args, 1)
		arg1_type, arg1v = self.get_arg_info(args[0])
		self.check_var_types(arg1_type, "int")
		
		if arg1v < 0 or arg1v > 49: error_exit("Bad exit code...", SEM_ERR57)

		exit(arg1v) 
		
# instructions
inst_function_list = {
		# Frame and variable manipulation instructions
		"CREATEFRAME": Inst.createframe, 
		"POPFRAME": Inst.popframe, 
		"PUSHFRAME": Inst.pushframe, 
		"DEFVAR": Inst.defvar, "MOVE": Inst.move, 
		"WRITE": Inst.write, "READ": Inst.read,

		# Instructions for arithmetic operations
		"ADD": Inst.arithmetic_operators, "SUB": Inst.arithmetic_operators, 
		"MUL": Inst.arithmetic_operators, "IDIV": Inst.arithmetic_operators,
	    
	 	# Instrcutions for logical operations
	 	"AND": Inst.logical_operators, "OR": Inst.logical_operators, "NOT": Inst.logical_operators,
	 	"LT": Inst.logical_operators, "GT": Inst.logical_operators, "EQ": Inst.logical_operators,
	    
	    # String manipulating instructions
	    "INT2CHAR": Inst.int2char, "STRI2INT": Inst.stri2int, 
	    "SETCHAR": Inst.setchar,   "GETCHAR": Inst.getchar,
	    "STRLEN": Inst.strlen,     "CONCAT": Inst.concat,
	    
	 	# Jump instructions 
	    "JUMP": Inst.jump, "CALL": Inst._call, "RETURN": Inst._return,
	    "JUMPIFEQ": Inst.jumpif, "JUMPIFNEQ": Inst.jumpif, 	    
	    
	    "PUSHS": Inst.pushs,
	    "POPS": Inst.pops,
	 	"TYPE": Inst.type, 
	    "EXIT": Inst._exit,
	    "BREAK": Inst._break,
	    "DPRINT": Inst.write,
	    "LABEL": Inst.label
 }

''' ==================================== MAIN PROGRAM  ================================================'''
# Argument parsing setup
arg_parser = argparse.ArgumentParser(description="Interpret for IPPcode21",
	usage="python3.8 interpret.py --source=file --input=file --help")
arg_parser.add_argument("--source", dest="source", type=str, nargs=1, help="XML source file")
arg_parser.add_argument("--input", dest="input", type=str, nargs=1, help="User input file")

args = arg_parser.parse_args() # Process arguments

instructions = Inst()

instructions.is_input  = True if getattr(args, "input") != None else False
instructions.is_source = True if getattr(args, "source") != None else False

# No arguments were given
if not instructions.is_source and not instructions.is_input:
	arg_parser.print_usage()
	error_exit("Missing arguments...", BAD_PARAMS_ERR)

''' ------------------------------------------------------------------------------'''
if instructions.is_source:
	instructions.source = getattr(args, "source")[0]
	if not path.exists(instructions.source): error_exit("Source file doesn't exist...", FILE_IO_ERR)

if instructions.is_input:
	instructions.input = getattr(args, "input")[0]
	if not path.exists(instructions.input): error_exit("Input file doesn't exist...", FILE_IO_ERR)
	instructions.load_file()

# load XML from source file or STDIN [check if can be opened correctly]
try: 
	program = xml.parse((getattr(args, "source")[0] if instructions.is_source else sys.stdin)).getroot()
except:
	error_exit("XML not well-formed...", WRONG_XML_ERR) # or 32

''' ============================= CHECK XML INTEGRITY ================================================'''
orders = []
try:
	for instruction in program: instruction[:] = sorted(instruction, key=lambda child: child.tag)
	if program.tag != "program": error_exit("Bad root xml element...", LEX_OR_SYN_ERR)
	for element in program:
		if element.attrib["order"] not in orders: orders.append(element.attrib["order"])
		else: error_exit("Duplicit instruction order...", LEX_OR_SYN_ERR)

		if int(element.attrib["order"]) < 1: error_exit("Bad instruction order number...", LEX_OR_SYN_ERR)

		if not element.attrib["opcode"]: error_exit("Missing instruction opcode...", LEX_OR_SYN_ERR)

		if element.tag != "instruction": error_exit("Bad xml element...", LEX_OR_SYN_ERR)
		for n, arg in enumerate(element):
			if ("arg"+str(n+1)) != arg.tag: error_exit("Bad xml element...", LEX_OR_SYN_ERR)
except:
	error_exit("Bad XML...", LEX_OR_SYN_ERR)

# Get all instructions (sorted), labels
instructions.inst_list = sorted(program.findall('.//instruction'),key=lambda inst: int(inst.attrib['order']))
for x in instructions.inst_list: instructions.labels = program.findall('.//instruction[@opcode="LABEL"]')

duplicates = [] # fileter out duplicate labels
for label in instructions.labels:
	if not label[0].text in duplicates: duplicates.append(label[0].text)
	else: error_exit("Duplicate label "+ label[0].text+ "..", SEM_ERR52)

''' ========================= PROCESS INSTRUCTIONS ==========================================='''
# Iterate through the instructions
while True:
	if instructions.inst_index >= len(instructions.inst_list): break

	# Call corresponding handle function
	inst = instructions.fetch_instruction()

	# Process instruction
	if (inst.attrib["opcode"].upper()) in inst_function_list:
		inst_function_list[(inst.attrib["opcode"]).upper()](instructions, list(inst))
	else:
		error_exit("Uknown instruction...", LEX_OR_SYN_ERR)

	instructions.increment_index()

exit(EXIT_SUCCESS)
