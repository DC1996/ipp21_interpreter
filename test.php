<?php 

/*******************************
VUT FIT IPP Project 2021, part 3.
PHP Test for automatic testing of
parse.php and interpret.py

Author: David Czirok, xcziro00
********************************/

$arg_parser  = new ArgumentParser();
$html_out = new HTMLOutput();
$file_tester = new Tester();

$result = true;
$arg_parser->parse_arguments();
$file_tester->html_output = $html_out;

// Loop through the files to be tested
foreach($arg_parser->test_files as $test_file) 
{
	$src_test = $test_file[1] . ".src";
	$out_test = $test_file[1] . ".out";
	$rc_test  = $test_file[1] . ".rc";
	$in_test  = $test_file[1] . ".in";
    
	// test existence of test files, generate missing
	if (!file_exists($rc_test)) exec("touch $rc_test && echo \"0\" > $rc_test");
	if (!file_exists($out_test)) exec("touch $out_test");
	if (!file_exists($in_test)) exec("touch $in_test");

	if($arg_parser->is_parse_only)
	{
		$result = $file_tester->test_parse_only($src_test, $rc_test, $out_test, $arg_parser);
	}

	else if($arg_parser->is_int_only) 
	{
		$result = $file_tester->test_int_only($src_test, $rc_test, $out_test, $in_test, $arg_parser);
	}
	else
	{
		$result = $file_tester->test_both($src_test, $rc_test, $out_test, $in_test, $arg_parser);
	}

	$html_out->append_test($test_file[1] . " --- ", $result);
}

$html_out->show_header();
$html_out->show_results($file_tester->num_of_tests, $file_tester->tests_passed, $file_tester->tests_failed);
$html_out->show_tests();

exec("rm -rf return_code test_output int_out delta.xml");
exit(0);

/* =========================== CLASSES ============================= */
class HTMLOutput
{
	private $tests = "";
	function append_test($test_name, $result) { 
		if($result == true)
			$this->tests .= "<p>$test_name\t<span style=\"color:green\">PASSED</span></p>\n"; 
		else
			$this->tests .= "<p>$test_name\t<span style=\"color:red\">FAILED</span></p>\n"; 
	}

	function show_header()
	{
		echo "<!DOCTYPE=HTML>\n";
		echo "<head> <title> IPP Test.php </title> </head>";
		echo "<h1> IPP 2021 Test Script [ xcziro00 ] </h1> <br> <br>";
	}
	function show_tests() {echo $this->tests;}

	function show_results($nof_tests, $passed, $failed) 
	{
		echo "\n<h2>Total number of test: " . $nof_tests . "</h2>";
		echo "\n<h3 style=\"color:green;\">Successful tests: " . $passed . "</h3>";
		echo "\n<h3 style=\"color:red;\">Failed tests:     " . $failed . "</h3>";
		echo "\n<br><br>\n";
	}
}

/*	Depending on the arguments,
	tests a file with parser,
	interpreter or both...
*/
class Tester
{
	// test counters
	public $tests_passed = 0;
	public $tests_failed = 0;
	public $num_of_tests = 0;

	private $ret = "return_code";
	private $out = "test_output";
	private $int_out = "int_out";

	public $html_output;

	function evaluate_test($diff_rc, $is_xml=false, $xml_rc=false, $is_out=false, $out_rc=false)
	{
		$this->num_of_tests++;
		if(!$diff_rc)
		{
			if ($is_xml) 
			{
				if(!$xml_rc) 
				{
					$this->tests_passed++;
					return true;
				}
				else
				{
					$this->test_failed++;
					return false;
				}
			}
			else if($is_out) 
			{
				if(!$out_rc) 
				{
					$this->tests_passed++;
					return true;
				}
				else
				{
					$this->tests_failed++;
					return false;
				}
			}
			else 
			{
				$this->tests_passed++;
				return true;
			}
		}
		else
		{ 
			$this->tests_failed++;
			return false;
		}
	}

	function test_parse_only($src, $rc, $out, $files) 
	{
		$is_xml = false;
		$xml_rc = 0; 
		$diff_rc; 

		exec("php7.4 $files->parse_script < $src > $this->out", $o, $ret_code);
		exec("echo $ret_code > $this->ret", $o, $r);
		exec("diff --ignore-all-space $this->ret $rc", $o, $diff_rc);

		if($ret_code == 0)
		{
			$is_xml = true;
			exec("java -jar $files->jexamxml $this->out $out delta.xml $files->jexamcfg", $o, $xml_rc);
		}

		return $this->evaluate_test($diff_rc, $is_xml, $xml_rc);
	}

	function test_int_only($src, $rc, $out, $in, $files) 
	{
		$is_out = false;
		$out_rc = 0; 
		$diff_rc; 

		if(!file_exists($in))
			exec("python3.8 $files->int_script --source=$src > $this->out",
				$o, $ret_code);
		else
			exec("python3.8 $files->int_script --source=$src --input=$in> $this->out", 
				$o, $ret_code);

		exec("echo $ret_code > $this->ret", $o, $r);
		exec("diff --ignore-all-space $this->ret $rc", $o, $diff_rc);

		if($ret_code == 0)
		{
			$is_out = true;
			exec("diff --ignore-all-space $this->out $out", $o, $out_rc);
		}

		return $this->evaluate_test($diff_rc, false, false, $is_out, $out_rc);
	}

	function test_both($src, $rc, $out, $in, $files) 
	{ 
		$diff_rc; 

		exec("php7.4 $files->parse_script < $src > $this->out", $o, $ret_code);
		exec("echo $ret_code > $this->ret", $o, $r);
		exec("diff --ignore-all-space $this->ret $rc", $o, $diff_rc);

		if($ret_code != 0)
		{	
			return $this->evaluate_test($diff_rc);
		}

		$is_out = false;
		$out_rc = 0; 

		if(!file_exists($in))
			exec("python3.8 $files->int_script --source=$this->out > $this->int_out",
				$o, $ret_code);
		else
			exec("python3.8 $files->int_script --source=$this->out --input=$in> $this->int_out", 
				$o, $ret_code);

		exec("echo $ret_code > $this->ret", $o, $r);
		exec("diff --ignore-all-space $this->ret $rc", $o, $diff_rc);

		if($ret_code == 0)
		{
			$is_out = true;
			exec("diff --ignore-all-space $this->int_out $out", $o, $out_rc);
		}

		return $this->evaluate_test($diff_rc, false, false, $is_out, $out_rc);
	}
}

/*  Handles the program arguments,
	and the loading of the test files...
*/
class ArgumentParser 
{
	public $test_files = [];
	public $parse_script = "./parse.php";
	public $int_script = "./interpret.py";
	public $jexamxml = "/pub/courses/ipp/jexamxml/jexamxml.jar";
	public $jexamcfg = "/pub/courses/ipp/jexamxml/options";

	public $is_int_only = false;
	public $is_parse_only = false;
	
	private $directory = "./";
	private $is_recursive = false;

	private $program_options = array(
		"help",						// prints help
		"directory::",				// which directory to search for tests
		"recursive",				// search directory recursively
		"parse-script::",			// path to parse.php file
		"int-script::",				// path to interpret.py file
		"parse-only",  				// tests parse.php only
		"int-only",    				// tests interperet.py only
		"jexamxml::",  				// /pub/courses/ipp/jexamxml/jexamxml.jar
		"jexamcfg::"   				// /pub/courses/ipp/jexamxml/options
	);

	function parse_arguments() 
	{
		// load and handle arguments
		$options = getopt("", $this->program_options);

		if(array_key_exists("help", $options)) {
			echo "Usage: php7.4 test.php [options] \n";
			echo "  --help \t\t prints usage\n";
			echo "  --directory=\"path\" \t which directory to search for tests\n";
			echo "  --recursive \t\t search given directory recursively\n";
			echo "  --parse-script=\"file\"\t path to parse.php\n";
			echo "  --int-script=\"file\" \t path to interpret.py\n";
			echo "  --parse-only \t\t test parse.php only\n";
			echo "  --int-only \t\t test interpret.py only\n";
			echo "  --jexamxml=\"file\" \t path to jexamxml.jar\n";
			echo "  --jexamcfg=\"file\" \t path to jexamxml's options file\n";

			if(count($options) > 1) exit(10); // combined with other parameters
			else exit(0);
		}

		foreach($options as $opt => $value)
		{
			switch($opt) 
			{
				case "directory": $this->directory = $value; break;
				case "recursive": $this->is_recursive = true; break;

				case "int-only": $this->is_int_only = true; break;
				case "int-script": $this->int_script = $value; break;
				case "parse-only": $this->is_parse_only = true; break;
				case "parse-script": $this->parse_script = $value; break;
				
				case "jexamxml": $this->jexamxml = $value; break;
				case "jexamcfg": $this->jexamcfg = $value; break;
			}			
		}

		// Check if given files and directory exists
		if(!is_dir($this->directory)
		or !file_exists($this->parse_script)
		or !file_exists($this->int_script)
		or !file_exists($this->jexamxml)
		or !is_readable($this->jexamcfg))
		{
			fwrite(STDERR, "Error: Bad or non-existing file/directory.\n");
			exit(41);	
		}

		// cannot combine both parse-only and int-only
		if($this->is_parse_only && $this->is_int_only) exit(10);

		// Create iterator
		if ($this->is_recursive)
			$iterator = new RecursiveIteratorIterator(
				new RecursiveDirectoryIterator($this->directory));
		else
			$iterator = new IteratorIterator(
				new RecursiveDirectoryIterator($this->directory));

		// Find test files by .src 
		$srcfiles = new RegexIterator($iterator, '/(^.+)\.src/', 
			RecursiveRegexIterator::GET_MATCH);
		
		// Transform into array and sort alphabetically
		$this->test_files = iterator_to_array($srcfiles, false);
		sort($this->test_files);
	}
}

?>
