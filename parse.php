<?php

/*******************************
VUT FIT IPP Project 2021, part 1.
PHP Parser for IPPcode21 langauge

Author: David Czirok, xcziro00
********************************/

// Return codes
const EXIT_SUCCESS = 0;
const ERR_BAD_PARAMS = 10;
const ERR_BAD_HEADER = 21;
const ERR_BAD_OPCODE = 22;
const ERR_SYN_OR_SEM = 23;

// Instruction argument type regex patterns
const VAR_REGEX = "/(^(LF|GF|TF)@([\-_$&%*!?a-zA-Z][\-_$&%*!?a-zA-Z0-9]*)$)/";
const INT_REGEX = "/(^int@([+-][0-9]+|[0-9]+)$)/";
const BOOL_REGEX = "/(^bool@(true|false))/";
const STRING_REGEX = "/(^string@([^\s#\\\\]|(\\\\\d{3}))*$)/";
const LABEL_REGEX = "/(^[a-zA-Z\-_$&%*!?][a-zA-Z\-_$&%*!?0-9]*$)/";
const TYPE_REGEX = "/^(string|int|bool)$/";

// IPPcode21 instructions, defining the number and type of their args
const INSTRUCTIONS = array(
		"CREATEFRAME"=>[], "PUSHFRAME"=>[], "POPFRAME"=>[], "RETURN"=>[], "BREAK"=>[],
		"DPRINT"=>["symb"], "EXIT"=>["symb"], "WRITE"=>["symb"], "PUSHS"=>["symb"],
		"DEFVAR"=>["var"], "POPS"=>["var"], "CALL"=>["label"], "LABEL"=>["label"],
		"JUMP"=>["label"], "JUMPIFEQ"=>["label", "symb", "symb"], "READ"=>["var", "type"],
		"JUMPIFNEQ"=>["label", "symb", "symb"], "ADD"=>["var", "symb", "symb"],
		"SUB"=>["var", "symb", "symb"], "MUL"=>["var", "symb", "symb"],
		"IDIV"=>["var", "symb", "symb"], "LT"=>["var", "symb", "symb"],
		"GT"=>["var", "symb", "symb"], "EQ"=>["var", "symb", "symb"], 
		"AND"=>["var", "symb", "symb"], "OR"=>["var", "symb", "symb"], 
		"STRI2INT"=>["var", "symb", "symb"], "CONCAT"=>["var", "symb", "symb"], 
		"GETCHAR"=>["var", "symb", "symb"], "SETCHAR"=>["var", "symb", "symb"], 
		"NOT"=>["var", "symb"], "MOVE"=>["var", "symb"],"INT2CHAR"=>["var", "symb"],
		"STRLEN"=>["var", "symb"], "TYPE"=>["var", "symb"],
		);

// ******************** MAIN **************************
ini_set('display_errrors', 'stderr'); // error handling to stderr

check_options($argc, $argv);

// XML Output setup
$xml_output = xmlwriter_open_memory();
xmlwriter_set_indent($xml_output, 1);
xmlwriter_set_indent_string($xml_output, ' ');
xmlwriter_start_document($xml_output, '1.0', 'UTF-8');

// XML program element & attribute language
xmlwriter_start_element($xml_output, 'program');
xmlwriter_start_attribute($xml_output, 'language');
xmlwriter_text($xml_output, 'IPPcode21');
xmlwriter_end_attribute($xml_output);

$order = 1; // Order of instructions
$header = false;

// Load each line of code from stdin
while(($args = fgets(STDIN))) 
{	
	if(preg_match("/^#+|^\s+$/", $args)) continue; // Filter comments and whitespaces
	$args = strpos($args, "#") ? substr($args, 0, strpos($args, "#")) : $args;	

	// split line into arguments
	$args = preg_split('/ +/', rtrim(ltrim($args)), null, PREG_SPLIT_NO_EMPTY);

	if(!$header)
	{
		if($args[0] != ".IPPcode21") exit(ERR_BAD_HEADER);

		$header = true; 
		continue;
	}

	$args[0] = strtoupper($args[0]);
	print_inst_start($xml_output, $order, $args[0]);
	process_instruction($args, $xml_output);
	xmlwriter_end_element($xml_output);
}

// Print the XML to STDOUT
xmlwriter_end_document($xml_output);
echo xmlwriter_output_memory($xml_output);
exit(EXIT_SUCCESS);

// ******************** FUNCTIONS **************************
function print_help()
{
	echo "Usage: php7.4 parse.php [--help | -h] < source_file \n";
	echo "Returns XML representation of an IPPcode21 source code.\n";
}

function check_options($argc, $argv)
{
	if($argc > 1)
	{
		// --help cannot be combined with other options
		if($argc > 2) exit(ERR_BAD_PARAMS);

		if($argv[1] == "--help" || $argv[1] == "-h")
		{
			print_help();
			exit(EXIT_SUCCESS); 	
		}

		// option doesnt match --help or -h
		exit(ERR_BAD_PARAMS);
	}	
}

// Prints the xml represenation of the instruction element
function print_inst_start($output, &$order, $inst) 
{
	xmlwriter_start_element($output, 'instruction');
	xmlwriter_start_attribute($output, 'order');
	xmlwriter_text($output, $order++);
	xmlwriter_start_attribute($output, 'opcode');
	xmlwriter_text($output, $inst);
}

// Prints the xml representation of the argument element
function print_argument($output, $type, $arg, $num)
{
	// Extract type if neccesarry and strip newline from end if found
	$arg = preg_replace(sprintf("/^%s@/", $type), "", rtrim($arg, "\n"));

	xmlwriter_start_element($output, "arg{$num}");
	xmlwriter_start_attribute($output, 'type');
	xmlwriter_text($output, $type);
	xmlwriter_end_attribute($output);
	xmlwriter_text($output, $arg);
	xmlwriter_end_element($output);
}

// Find regex match for given type of argument and return type
// return false if not successful
function check_argument_regex($type, $arg)
{ 
	switch($type)
	{
		case "symb":
			if(preg_match(VAR_REGEX, $arg)) return "var";
			if(preg_match(INT_REGEX, $arg)) return "int";
			if(preg_match(BOOL_REGEX, $arg)) return "bool";
			if(preg_match(STRING_REGEX, $arg)) return "string";
			if(preg_match("/(^nil@nil$)/", $arg)) return "nil";
			break;		

		case "var":
			if(preg_match(VAR_REGEX, $arg)) return $type;
			break;

		case "label":
			if(preg_match(LABEL_REGEX, $arg)) return $type;	
			break;

		case "type":
			if(preg_match(TYPE_REGEX, $arg)) return $type; 
			break;
	}

	return false;
}

// Processes given loaded instruction
function process_instruction($args, $output)
{
	// No match for instruction
	if(!array_key_exists($args[0], INSTRUCTIONS)) exit(ERR_BAD_OPCODE); 

	$arg_pos = 1; 
	foreach(INSTRUCTIONS[$args[0]] as $argtype) 
	{
		// Process each argument type of given instruction
		if(array_key_exists($arg_pos, $args) &&
		($type = check_argument_regex($argtype, $args[$arg_pos])))
		{
			print_argument($output, $type, $args[$arg_pos], $arg_pos++); 
		}
		else exit(ERR_SYN_OR_SEM);
	}

	// More arguments then expected
	if(count($args) > $arg_pos) exit(ERR_SYN_OR_SEM);
}
?>
