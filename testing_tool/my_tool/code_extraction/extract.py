import cProfile
import pstats
import io
import time
import sys, os
import jedi
import token, tokenize
import logging
import json
import ast


# ============================================
# copy from ../change_code.py
# extract_function_code and extract_function are modified
# ============================================

# which char in input_str is related to the first bracket in input_str
# return -1 as error, 0 as no bracket
def find_correspond_bracket(input_str):
  # open_brackets = '([{<'
  # close_brackets = ')]}>'
  # brackets_map = {')': '(', ']': '[', '}': '{', '>': '<'}
  open_brackets = '([{'
  close_brackets = ')]}'
  brackets_map = {')': '(', ']': '[', '}': '{'}

  stack = []
  contain_bracket = False
  for i in range(len(input_str)):
    char = input_str[i]
    if char in open_brackets:
      stack.append(char)
      contain_bracket = True
    elif char in close_brackets:
      if len(stack) < 1:
        return -1
      elif brackets_map[char] == stack[-1]:
        stack.pop()
        if len(stack) == 0:
          return i
      else: 
        return -1
    else:
      continue
  if contain_bracket:
    return -1
  else:
    return 0

# function definition
def extract_function_info(function_head):
  if not "def" in function_head:
    return
  line = function_head
  start = line.find("(")+1
  end = line.rfind(")")
  params_coarse = line[start:end].split(",")

  # solve things like category_index=["apple","book","cat","car","dog"]
  params = []
  is_break = False
  for param in params_coarse:
    if is_break:
      params[-1] = params[-1] + "," + param.strip()
      # if the first open bracket has its close bracket
      if find_correspond_bracket(params[-1]) >= 0:
        is_break = False
    else:
      params.append(param)
      # if the first open bracket doesn't have its close bracket
      if find_correspond_bracket(param) < 0:
        is_break = True

  default_value = []
  for i in range(len(params)):
    if "=" in params[i]:
      ind = params[i].find("=")
      default_value.append(params[i][ind+1:])
      params[i] = params[i][:ind]
    else:
      default_value.append(None)
  name_start = line.find("def")+3
  name = line[name_start:start-1].strip()
  return name, params, default_value

def extract_function_code(content_line_by_line, line_of_func, params):
  function_code = ""
  # content_line_by_line = content.split("\n")
  flag = False
  self_flag = False # whether it is defined inside a class
  indent = 0
  last_line = line_of_func
  for line_no, line in enumerate(content_line_by_line):
    if len(line.strip()) <= 0:
      continue
    # if comment
    if line.strip().startswith("#"):
      continue
    if line_no == line_of_func:
      indent = len(line) - len(line.lstrip())
      flag = True
      # deal with def xx(self, ...
      if params[0]=="self":
        self_flag = True
        params = params[1:]
      line = line[:line.find("(")+1] + ", ".join(params) + ")"
    # if (line.strip().startswith("def")) and not (function_name in line):
    else:
      if indent >= len(line) - len(line.lstrip()):
        flag = False
    if flag:
      # remove self.
      if self_flag and "self" in line:
        all_names = jedi.names(line, all_scopes=True, definitions=True, references=True)
        col_fix = 0
        for name in all_names:
          if name.name == "self":
            start = name.column + col_fix
            end = start + len(name.name)
            if line[end:].strip().startswith("."):
              start2 = end + line[end:].find(".") + 1
              line = line[:start] + line[start2:]
              col_fix -= start2 - start
      function_code = function_code + line[indent:] + "\n"
      last_line_no = line_no
  return function_code, last_line_no

def read_functions(content_line_by_line):
  Functions = {}
  code_outside = []
  last_func_line_no = -1
  stop_flag = False
  for line_no, line in enumerate(content_line_by_line):
    # already extracted
    if line_no <= last_func_line_no:
      continue
    # if comment
    stripped_line = line.strip()
    if stripped_line.startswith("#") or len(stripped_line)==0:
      continue

    # if function head
    if line.strip().startswith("def"):
      func_name, params, _ = extract_function_info(line)
      function_code, last_func_line_no = extract_function_code(content_line_by_line, line_no, params)
      # NOTE: line numbers start from 1 instead of 0 to match other codes
      line_no += 1
      Functions[func_name] = (function_code, line_no)
    elif not stop_flag:
      if line.replace(" ","").startswith("if__name__=="):
        stop_flag = True
      elif not stripped_line.startswith("class") and not stripped_line.startswith("import ") and not stripped_line.startswith("from "):
        code_outside.append(stripped_line)
  return Functions, code_outside




# ============================================
# new implementation
# ============================================

# output_file: store cProfile result. None for not save
# use_prev_profile: whether run cProfile or not
# target_function: the function to be tested
# use_static: whether to use static function call tracer (pyan)
#             or dynamical profiling (cProfile)
# filenames: required if use_static is set to True
# target_function_namespace: required if use_static is set to True
# function_args: the args of target_function
# output: list of functions in formart of [name, file, line_no]
def get_call_graph(
  output_file,
  use_prev_profile,
  target_function,
  use_static,
  filenames,
  target_function_name,
  root,
  *function_args
):

  function_calls = []
  if not use_static:

    # === proflie
    if not use_prev_profile:
      pr = cProfile.Profile()
      pr.enable()
      my_result = target_function(*function_args)
      pr.disable()
      time.sleep(0.5)

      s = io.StringIO()
      ps = pstats.Stats(pr, stream=s)  #.sort_stats('tottime')
      ps.print_stats()
      content = s.getvalue()
      if output_file:
        with open(output_file, 'w') as f:
            f.write(content)
    else:
      with open(output_file, 'r', encoding='utf8') as file_obj:
        content = file_obj.read()

    # === extract info
    
    # target_function itself
    # https://blog.csdn.net/jpch89/article/details/86764245
    function = [target_function.__code__.co_name, target_function.__code__.co_filename, target_function.__code__.co_firstlineno]
    function_calls.append(function)
    # print(target_function.__code__.co_code.decode('unicode_escape'))# not working

    start_record = False
    for line in content.split("\n"):
      line = line.strip()
      if len(line) == 0:
        continue
      
      if line.startswith("ncalls  tottime  percall  cumtime  percall filename:lineno(function)"):
        start_record = True
        continue

      # if "{method 'disable' of '_lsprof.Profiler' objects}" in line:
      #   continue
    
      if start_record:
        info = line.split()

        # not user defined function
        if not len(info)==6:
          continue
        info = info[-1]
        if info.startswith("{") or info.startswith("<"):
          continue

        info = info.split(":")
        if not len(info)==2:
          print("[Error] Cannot parse \"" + line + "\"")
          continue
        filename = info[0]
        info = info[1]

        info = info.split("(")
        if not len(info)==2:
          print("[Error] Cannot parse \"" + line + "\"")
          continue
        lineno = info[0]
        name = info[1][:-1]

        if "lib/python3" in filename or "lib/python2" in filename:
          continue
        if name.startswith("<"):
          continue

        function = [name, filename, lineno]
        function_calls.append(function)

  # profile using pyan
  else:
    if filenames == None or target_function_name == None:
      raise ValueError("get_call_graph: using static function call tracer must define filenames and target_function_name")

    sys.path.append(os.path.dirname(os.path.realpath(__file__)))
    from pyan.trace_functions import pyan_trace_functions
    # print(f"function name: {target_function.__name__}")
    function_calls = pyan_trace_functions(filenames=filenames, function=target_function_name, root=root)

  return function_calls


def remove_repeated_functions(function_calls):
  new_calls = []
  printed_func = set()
  for func in function_calls:
    funcname, filename, lineno = func
    func_id = funcname+"("+filename+")"
    if not func_id in printed_func:
      new_calls.append(func)
      printed_func.add(func_id)
  return new_calls




class Extractor():
  def __init__(self,
               json_file_path: str,
              #  target_function,
               *function_args):
    """
      Args:
        json_file_path: file path to json file generated by VS Code Plugin
        target_function: target function to be executed
        *function_args:  arguments to the given target_function
    """
    if json_file_path != "":
      self.json_data = json.load(open(json_file_path))
    else:
      self.json_data = {}

    self.logger = logging.getLogger(__name__)
    self.imported_packages = set()
    # stores whether it has dynamically executed the whole code
    # dynamic execution is needed when import cannot be analyzed statically
    self.executed_dynamic = False
    self.target_function = None
    # self.function_args = function_args
    self.function_args = self.get_function_args()

    # stores file -> removed empty lines/comments information
    self.empty_lines = {}

  def get_function_args(self):
    """
      Get function args for specified function from the input json file
    """
    res = []
    if "input_types" not in self.json_data:
      self.logger.critical(f"input_types not in input json specified")
      return ()
    for item in self.json_data["input_types"]:
      res.append(self.get_default_input(item, return_string=False))
    return tuple(res)

  def get_all_lines(self, slineno, elineno):
    res = []
    while slineno <= elineno:
      res.append(slineno)
      slineno += 1
    return res

  def append_empty_line_info(self, src_file, line):
    self.logger.debug(f"Found {line} to be empty in {src_file}")
    if src_file not in self.empty_lines:
      self.empty_lines[src_file] = set()
    for i in line:
      self.empty_lines[src_file].add(i)

  def get_empty_line_numbers(self, src_file):
    i = 1
    res = []
    with open(src_file, "r") as fd:
      for entry in fd.readlines():
        if entry.strip() == "":
          res.append(i)
        i += 1
    self.append_empty_line_info(src_file, res)

  def readfile_without_comments(self, src_file):
    self.get_empty_line_numbers(src_file)
    source = open(src_file)
    new_content = ""
    prev_toktype = token.INDENT
    first_line = None
    last_lineno = -1
    last_col = 0
    tokgen = tokenize.generate_tokens(source.readline)
    for toktype, ttext, (slineno, scol), (elineno, ecol), ltext in tokgen:
      if False:   # Change to if True to see the tokens fly by.
        print("%10s %-14s %-20r %r" % (
            tokenize.tok_name.get(toktype, toktype),
            "%d.%d-%d.%d" % (slineno, scol, elineno, ecol),
            ttext, ltext
            ))
      if slineno > last_lineno:
        last_col = 0
      if scol > last_col:
        new_content += " " * (scol - last_col)
      if toktype == token.STRING and prev_toktype == 58: # newline
        self.append_empty_line_info(src_file, self.get_all_lines(slineno, elineno))
        pass
      elif toktype == token.STRING and (prev_toktype == token.DEDENT or prev_toktype == token.INDENT):
        self.append_empty_line_info(src_file, self.get_all_lines(slineno, elineno))
        # Docstring
        pass
      elif toktype == tokenize.COMMENT:
        self.append_empty_line_info(src_file, self.get_all_lines(slineno, elineno))
        # Comment
        pass
      # elif toktype == tokenize.NL:
      #   self.append_empty_line_info(src_file, self.get_all_lines(slineno, elineno))
      else:
        new_content += ttext
      prev_toktype = toktype
      last_col = ecol
      last_lineno = elineno
    lines = new_content.split("\n")
    # fix indent of tabs
    with open(src_file, 'r', encoding='utf8') as file_obj:
        content = file_obj.read().split("\n")
    for i, line in enumerate(lines):
      tab_index = 0
      while len(content[i]) > tab_index:
        if content[i][tab_index] == '\t':
          tab_index += 1
        else:
          break
      lines[i] = "  "*tab_index + line[tab_index:]
    return lines

  def process_module_obj(self, module_obj):
    """
      Determines whether the given module object corresponds to a system module or not
      If corresponds to system module, also add it to self.imported_packages

      Args:
        module_obj: a module object dynamically executed

      Returns:
        tuple (whether the module object is a system module
               module file path)
    """
    is_system = False
    if str(module_obj).endswith("(built-in)>"):
      # self.imported_packages.add(line.strip())
      is_system = True
      module_file = "Unknown"
    else:
      module_name = module_obj.__name__ # it may be different from module
      if '__file__' in dir(module_obj) and module_obj.__file__ != None:
        module_file = module_obj.__file__
      elif '__path__' in dir(module_obj):
        module_file = module_obj.__path__._path[0]
      else:
        module_file = "Unknown"
        print("[Error] can not retrieve info from package " + module_fix)
      # from system packages
      self.logger.debug(f"module_file retrieved to be {module_file}")
      if "lib/python3" in module_file or "lib/python2" in module_file or "lib/python/site-packages" in module_file:
        # self.imported_packages.add(line.strip())
        is_system = True
      self.logger.debug(f"is_system is determined to be {is_system}")
    return is_system, module_file

  def sort_and_print_dict(self):
    for key, value in self.empty_lines.items():
      value = list(value)
      value.sort()
      self.empty_lines[key] = value
    f4_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), "empty_line.json")
    self.logger.info(f"empty_lines dict is computed to be {self.empty_lines}")
    self.logger.info(f"Writing empty_line dict to {f4_filename}")
    with open(f4_filename, "w") as f4:
      f4.write(json.dumps(self.empty_lines, indent=2))

  def get_all_rename_info(self,
                          current_file: str,
                          import_lines: str) -> (dict, dict):
    """
      Get all the module/function rename information

      Args:
        current_file: file path of the file that includes this import statement
        import_lines: importation lines to be analyzed
      
      Returns:
        tuple (file_rename:     {imported name -> origin name},
               function_rename: {imported name -> origin name})
    """
    file_rename = dict()
    modules_dict, functions_dict, modules, _ = self.get_import_modules(import_lines)

    for key, value in modules_dict.items():
      is_system, _ = self.get_single_module_path(value[0], current_file, value[1])
      if not is_system:
        file_rename[key] = value

    for module in modules:
      is_system, _ = self.get_single_module_path(module[0], current_file, module[1])
      if not is_system:
        file_rename[module[0]] = module[0]

    return file_rename, functions_dict


  def get_all_module_path(self,
                          current_file: str,
                          import_lines: str) -> list:
    """
      Get all module path information of `import_lines`

      Args:
        current_file: file path of the file that includes this import statement
        import_lines: importation lines to be analyzed
      
      Returns:
        list of files that got imported
    """
    res = []

    modules_dict, _, modules, module_function_mapping = self.get_import_modules(import_lines)
    # modules += modules_dict.values() # stores all the imported module names

    # each module is a 2-tuple, first pos stores the module name and second
    # pos stores the module level (for relative imports)
    for module in modules:
      # print(module)
      is_system, module_file = self.get_single_module_path(module[0], current_file, module[1])
      if not is_system:
        res.append(module_file)
      # if it is a system module, then add the corresponding import line
      else:
        self.imported_packages.add(f"import {module[0]}")
        for entry in module_function_mapping:
          if entry[0] == module[0]:
            self.imported_packages.add(f"from {module[0]} import {entry[1]}")

    # for these values, if they are system packages, we actually need to write `import as` statement
    for key, value in modules_dict.items():
      is_system, module_file = self.get_single_module_path(value[0], current_file, value[1])
      if not is_system:
        res.append(module_file)
      else:
        self.imported_packages.add(f"import {value[0]} as {key}")

    return res
  
  def dynamic_execution(self):
    """
      Dynamically execute code from the given entry point

      Args:    None
      Returns: None
    """
    try:
      self.logger.info(f"dynamically executing code")
      self.logger.debug(f"self.targe_function: {self.target_function}")
      self.logger.debug(f"self.function_args: {self.function_args}")
      pr = cProfile.Profile()
      pr.enable()
      my_result = self.target_function(*self.function_args)
      pr.disable()
      time.sleep(0.5)

      s = io.StringIO()
      ps = pstats.Stats(pr, stream=s)  #.sort_stats('tottime')
      ps.print_stats()
      self.logger.info(f"finished dynamically executing code")
    except Exception as e:
      self.logger.error(f"dynamic_execution encountered the following error: {e}")

    self.executed_dynamic = True

  def get_single_module_path(self,
                             module: str,
                             current_file: str,
                             module_level=0) -> (bool, str):
    """
      Get the imported module path + whether user-defined info
      corresponding to a single module.
      If dynamic analysis fails, then need to run application from entry-point

      Args:
        module:       name of the module that appears on the import line
        current_file: file path of the file that includes this import statement
        module_level: default to 0, corresponding to how many dots in relative import
      
      Returns:
        tuple (whether this module is system module,
               the module path for user-defined modules)
    """

    try:
      self.logger.debug(f"exec module: {module}")
      exec("import " + module)
      module_obj = eval(module)
      if module_obj:
        if isinstance(module_obj, tuple): 
          self.logger.critical(f"get_single_module_path expected a single module, but dynamically executed multiple modules")
        else:
          return self.process_module_obj(module_obj) # returned: is_system, module_file

    # TODO: determine whether other errors are possible
    #       ModuleNotFoundError is what appears in Python 3.8, to be tested in 3.6
    except (UnboundLocalError, ModuleNotFoundError) as e:
      # if dynamic analysis fails, then if never dynamically executed code,
      # execute it from start
      # otherwise, use static analysis to help
      if module_level == 0:
        if self.executed_dynamic:
          # meaning: if no relative import, then is a failed attempt to get module
          #          information. Just print out traceback info
          self.logger.error("get_single_module_path failed to retrieve absolute import module path by dynamic processing")
          import traceback
          traceback.print_exc()
          return (True, current_file)
        else:
          self.dynamic_execution()
          return self.get_single_module_path(module, current_file, module_level)

      else:
        while module_level != 0:
          directory, _ = os.path.split(current_file)
          module_level -= 1
        return (False, os.path.join(directory, module + ".py"))


  def get_import_modules(self, import_line: str) -> (dict, dict, list, list):
    """
      Retrieve relevant information from the specified importation line
      supports the following styles of importation:
        1. import a, b               | Single/Multiple imports, no renaming
        2. import a, b as c, d       | Single/Multiple imports, partial/all renaming
        3. from a import b           | Singly import function
        4. from a import b as c      | Singly import function, renaming function

      Args:
        import_line: string of the line containing information about import

      Returns:
        tuple (dict{renamed modules   -> (imported modules, level)},
               dict{renamed functions -> imported functions},
               [(imported modules without renaming, level)],
               [(imported module name, imported function)])
    """
    self.logger.debug(f"get_import_modules: receieved import_line: {import_line}")
    ast_line = ast.parse(import_line)
    modules_mapping = dict()
    functions_mapping = dict()
    no_rename_modules = []
    module_function_mapping = []
    for statement in ast_line.body:
      if isinstance(statement, ast.ImportFrom):
        no_rename_modules.append((statement.module, statement.level))
        for name in statement.names:
          if name.asname != None:
            # module_function_mapping.append((statement.module, name.name))
            # no_rename_functions.append(name.name)
          # else:
            functions_mapping[name.asname] = name.name

          # regardless whether function is renamed, append to the last list
          module_function_mapping.append((statement.module, name.name))
  
      elif isinstance(statement, ast.Import):
        for name in statement.names:
          if name.asname == None:
            no_rename_modules.append((name.name, 0))
          else:
            modules_mapping[name.asname] = (name.name, 0)

      else:
        self.logger.debug(f"get_import_modules expected an import statement, but receieved otherwise: {statement}")
    
    return (modules_mapping,
            functions_mapping,
            no_rename_modules,
            module_function_mapping)

  def extract(
    self,
    dest_file,
    add_extra
    # target_function,
    # use_static,
    # filenames,
    # target_function_name,
    # root,
    # *function_args,
  ):
    # use_static = False
    # If the input JSON file contains the following fields, then
    # by default, assume we want to run the static analyzer
    if "func_name" in self.json_data and "code_file" in self.json_data and "func_def_line" in self.json_data and "workspace" in self.json_data:
      func_name = self.json_data["func_name"]
      code_file = self.json_data["code_file"]
      func_def_line = self.json_data["func_def_line"]
      workspace = self.json_data["workspace"].rstrip("/")
      use_static = True
      root = workspace
      filenames = root.rstrip("/") + "/**/*.py"

      self.logger.debug(f"appending {os.path.dirname(os.path.realpath(code_file))} to system path")
      sys.path.append(os.path.dirname(os.path.realpath(code_file)))
      code_file_suffix = os.path.split(self.json_data["code_file"])[1].replace(".py", "")
      self.logger.debug(f"executing the following line: from {code_file_suffix} import {func_name} as test")
      exec(f"from {code_file_suffix} import {func_name} as test")
      # TODO: figure out why this wouldn't work
      # self.target_function = test

      target_function_name = os.path.relpath(code_file, start=workspace)
      target_function_name = target_function_name.rstrip("/").replace(".py", "")
      target_function_name += f"/{func_name}"
      target_function_name = os.path.join(os.path.split(workspace)[1], target_function_name)
      target_function_name = target_function_name.replace("/", ".")

      self.logger.info(f"filenames: {filenames}")
      self.logger.info(f"target_function_name: {target_function_name}")
      self.logger.info(f"root: {root}")

    else:
      self.logger.error("Cannot find all desired fields in input json data")

    function_calls = get_call_graph("profile.txt", False, self.target_function, use_static, filenames, target_function_name, root, *self.function_args)
    self.logger.info("====== [INFO] related functions (called during execution) ======")
    for func in function_calls:
      self.logger.info(func)
    self.logger.info("================================================================")
    self.generate_one_file(function_calls, dest_file)
    
    f = open(dest_file, 'a')
    if add_extra:
      f.write("if __name__ == '__main__': \n")
      func_call_code = "  " + function_calls[0][0] + "()"
      # REVIEW: make sure that this is no longer needed
      # for i, arg in enumerate(self.function_args):
      #   if i == 0:
      #     func_call_code += str(arg)
      #   else:
      #     func_call_code += ", " + str(arg)
      f.write(func_call_code + "\n\n")
    f.close()
  
  def generate_one_file(self, function_calls, dest_file):
    """
    main function for processing multiple files into one

    Args:
      function_calls: a list of function names traced from analyzer
      dest_file: file location to write to
    """
    self.imported_packages = set()

    function_calls = remove_repeated_functions(function_calls)

    # read files
    File_to_functions = {}     # filename -> {function name -> function code}
    File_to_imports = {}       # filename -> code related to import
    Code_outside_func = []
    for func in function_calls:
      funcname, filename, lineno = func
      if not filename in File_to_functions.keys():
        content_line_by_line = self.readfile_without_comments(filename)
        functions, code_outside = read_functions(content_line_by_line)
        File_to_functions[filename] = functions
        Code_outside_func += code_outside
        
        # REVIEW: probably can just dump everything to AST for lexical analysis
        imports_code = ""
        for line in content_line_by_line:
          if line.strip().startswith("import "):
            imports_code += line.strip() + "\n"
          if line.strip().startswith("from ") and " import " in line:
            imports_code += line.strip() + "\n"
        File_to_imports[filename] = imports_code

    # if some functions are not called with given parameters
    checked_files = set()
    unchecked_files = set(File_to_imports.keys())
    while len(unchecked_files) > 0:
      related_user_code_files = set()
      for file in unchecked_files:

          related_user_code_files.update(self.get_all_module_path(file, File_to_imports[file]))
          self.logger.debug(f"related_user_code_files set is now: {related_user_code_files}")

      unchecked_files = set()
      for filename in related_user_code_files:
        if not filename in checked_files:
          unchecked_files.add(filename)
          # read these file
          content_line_by_line = self.readfile_without_comments(filename)
          functions, code_outside = read_functions(content_line_by_line)
          File_to_functions[filename] = functions
          Code_outside_func += code_outside
          
          # REVIEW: probably can just dump everything to AST for lexical analysis
          imports_code = ""
          for line in content_line_by_line:
            if line.strip().startswith("import "):
              imports_code += line.strip() + "\n"
            if line.strip().startswith("from ") and " import " in line:
              imports_code += line.strip() + "\n"
          File_to_imports[filename] = imports_code
    

    # manage imports
    File_to_rename = {}
    
    for file in File_to_imports.keys():

      file_rename, function_rename = self.get_all_rename_info(file, File_to_imports[file])

      File_to_rename[file] = (function_rename, file_rename)
      self.logger.info(f"function_rename: {function_rename}; file_rename: {file_rename}")

    # stores the function name mappings by line numbers
    # the entry information is as follows:
    # ("func_name", curr_linenb) -> (original_file, original_linenb)
    func_mapping_dict = dict()

    f2 = open(dest_file, 'w')
    f2_linenb = 0     # stores the current line number info
    for package in self.imported_packages:
      f2.write(package +"\n"); f2_linenb += 1
    f2.write("\n# ==================\n"); f2_linenb += 2
    for code in Code_outside_func:
      if code.strip().startswith("@"):
        continue
      f2.write(code +"\n"); f2_linenb += 1
    f2.write("\n# ==================\n"); f2_linenb += 2

    # write functions
    checked_functions = set() # store origin name
    mentioned_functions = set() # store origin name
    for func in function_calls[::-1]:
      funcname, filename, lineno = func
      func_code = File_to_functions[filename][funcname][0]
      (function_rename, file_rename) = File_to_rename[filename]
      checked_functions.add(funcname)

      k = 0
      for line in func_code.split("\n"):
        all_names = jedi.names(line, all_scopes=True, definitions=True, references=True)
        col_fix = 0
        for name in all_names:
          # if it is a function name
          if (not name.name in checked_functions) and (not name.name in mentioned_functions):
            end = name.column + col_fix + len(name.name)
            if line[end:].strip().startswith("("):
              if name.name in function_rename.keys():
                mentioned_functions.add(function_rename[name.name])
              else:
                mentioned_functions.add(name.name)
          # no longer need filename prefix
          if name.name in file_rename.keys():
            start = name.column + col_fix
            end = start + len(name.name)
            if line[end:].strip().startswith("."):
              start2 = end + line[end:].find(".") + 1
              line = line[:start] + line[start2:]
              col_fix -= start2 - start
          # rename function name
          if name.name in function_rename.keys():
            start = name.column + col_fix
            end = start + len(name.name)
            line = line[:start] + function_rename[name.name] + line[end:]
            col_fix += len(function_rename[name.name]) - len(name.name)
        
        # TODO: check if this is the optimal method:
        if line.strip().startswith("def"):
          line += ":"

        # check if function is the user-specified function
        # if so, change default parameters
        # print(f"funcname: {funcname}, filename: {filename}, {lineno}")
        if funcname == self.json_data["func_name"] and filename == self.json_data["code_file"] and lineno == self.json_data["func_def_line"] and k == 0:
          line = self.change_default_param(line)

        f2.write(line + "\n"); f2_linenb += 1

        # k == 0 signifies the function head analysis
        if k == 0:
          func_mapping_dict[(funcname, f2_linenb)] = (filename, lineno)

        # increase k so that it only processes the first line
        # ,i.e., function definition line
        k += 1
      # f2.write(func_code)
      f2.write("\n# ==================\n"); f2_linenb += 2

    # if some functions are not called with given parameters
    # print(mentioned_functions)
    self.logger.info("======= [INFO] related functions (inferred by analysis) ========")
    while len(mentioned_functions)>0:
      func_to_be_check = mentioned_functions
      mentioned_functions = set()
      for funcname in func_to_be_check:
        if funcname in checked_functions:
          continue
        filename = None
        for code_file in File_to_functions.keys():
          if funcname in File_to_functions[code_file]:
            filename = code_file
            lineno = File_to_functions[code_file][funcname][1]
        if filename:
          self.logger.info(str([funcname, filename, lineno]))
        else:
          self.logger.info("[Error] Cannot find function \'" + funcname + "\'. Please change *function_args to cover its reference.")
          continue
        func_code = File_to_functions[filename][funcname][0]
        (function_rename, file_rename) = File_to_rename[filename]
        checked_functions.add(funcname)
        
        k = 0
        for line in func_code.split("\n"):
          all_names = jedi.names(line, all_scopes=True, definitions=True, references=True)
          col_fix = 0
          for name in all_names:
            # if it is a function name
            if (not name.name in checked_functions) and (not name.name in mentioned_functions):
              end = name.column + col_fix + len(name.name)
              if line[end:].strip().startswith("("):
                if name.name in function_rename.keys():
                  mentioned_functions.add(function_rename[name.name])
                else:
                  mentioned_functions.add(name.name)
            # no longer need filename prefix
            if name.name in file_rename.keys():
              start = name.column + col_fix
              end = start + len(name.name)
              if line[end:].strip().startswith("."):
                start2 = end + line[end:].find(".") + 1
                line = line[:start] + line[start2:]
                col_fix -= start2 - start
            # rename function name
            if name.name in function_rename.keys():
              start = name.column + col_fix
              end = start + len(name.name)
              line = line[:start] + function_rename[name.name] + line[end:]
              col_fix += len(function_rename[name.name]) - len(name.name)

          # TODO: check if this is the optimal method
          if line.strip().startswith("def"):
            line += ":"
          

          f2.write(line + "\n"); f2_linenb += 1

          if k == 0:
            func_mapping_dict[(funcname, f2_linenb)] = (filename, lineno)          

          k += 1
        f2.write("\n# ==================\n"); f2_linenb += 2

    # write the mappiing dictionary to file so that other files can read
    # write to the current directory for all_wrap_up.py to access
    f3_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), "function_mapping.json")

    tuple2str = lambda x : x[0] + "," + str(x[1])
    func_mapping_dict = dict((tuple2str(k), v) for k,v in func_mapping_dict.items())

    self.logger.info(f"func_mapping_dict is computed to be {func_mapping_dict}")
    self.logger.info(f"Writing func_mapping_dict to {f3_filename}")
    with open(f3_filename, "w") as f3:
      f3.write(json.dumps(func_mapping_dict, indent=2))

    # write the empty line information to file so that other files can read
    # write to the current directory for all_wrap_up.py to access
    self.sort_and_print_dict()

  def change_default_param(self, func_line: str):
    """
    change the default function parameters
    according to data from VS Code plugin

    Args:
      func_line: function definition line string
    
    Returns:
      A string of the function definition line with added
      default parameters
    """
    self.logger.info(f"Specified function definition line is {func_line}")

    if len(self.json_data["input_types"]) == 0:
      res = func_line
    else:
      first_split = func_line.split("(", maxsplit=1)
      # print(first_split)
      if len(first_split) != 2:
        self.logger.critical(f"Function definition line splitting with ( returns unexpected length")
      
      second_split = first_split[1].split(")")
      if len(second_split) != 2:
        self.logger.critical(f"Function definition line splitting with ) returns unexpected length")    

      # new_params would record the new parameters with
      # default values added
      new_params = []
      i = 0
      for params in second_split[0].split(","):
        if i + 1 > len(self.json_data["input_types"]):
          self.logger.critical(f"input json data's input_types has less entries than required by actual function definition line. Expect index out of range error below")

        if params.strip() in self.json_data["API_param"]:
          new_params.append(params + '="API_input"')
        else:
          new_params.append(params + "=" + self.get_default_input(self.json_data["input_types"][i]))
        i += 1
      
      # print(f"new_params is {new_params}")
      res = first_split[0]
      res += "("
      # everything except the last parameter needs to be appended with comma
      for params in new_params[:-1]:
        res += params + ", "
        # print(f"res is {res}")
      res += new_params[-1]
      res += "):"

    self.logger.info(f"Modified function definition line is {res}")

    return res
    

  def get_default_input(self, param_type: str, return_string=True):
    if param_type == "string":
      if return_string:
        return "'abc'"
      else:
        return 'abc'
    elif param_type == "integer":
      if return_string:
        return "1"
      else:
        return 1
    elif param_type == "float":
      if return_string:
        return "1.1"
      else:
        return 1.1
    elif param_type == "boolean":
      if return_string:
        return "True"
      else:
        return True
    else:
      self.logger.critical(f"get_default_input receieved a param_type other than string, integer, float, boolean. It receieved: {param_type}. Returning default value for string")
      return "abc"


if __name__ == '__main__':
  pass