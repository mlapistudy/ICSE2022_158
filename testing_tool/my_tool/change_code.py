import os,io
import jedi
import token, tokenize

from global_vars import *



def read_wholefile(filename, preprocess=True):
  with open(filename, 'r', encoding='utf8') as file_obj:
    text = file_obj.read()
  if preprocess:
    return text.replace(".lower()","")
  else:
    return text

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
  
  params = [x.strip() for x in params if len(x.strip())>0]
  default_value = []
  for i in range(len(params)):
    if "=" in params[i]:
      ind = params[i].find("=")
      default_value.append(params[i][ind+1:].strip())
      params[i] = params[i][:ind].strip()
    else:
      default_value.append(None)
  name = line[4:start-1]
  return name, params, default_value

# function call
# TODO: consider , in one function parameter
def extract_function_call(function_call):
  line = function_call
  start = line.find("(")+1
  end = line.rfind(")")
  # params = line[start:-1].split(",")
  params_coarse = line[start:end].split(",")
  params = []
  is_break = False
  for param in params_coarse:
    if is_break:
      params[-1] = params[-1] + "," + param.strip()
      if find_correspond_bracket(params[-1]) >= 0:
        is_break = False
    else:
      params.append(param)
      if find_correspond_bracket(param) < 0:
        is_break = True

  for i in range(len(params)):
    if "=" in params[i]:
      ind = params[i].find("=")
      # not ==
      if not params[i][ind+1:].strip().startswith("="):
        params[i] = params[i][ind+1:]
  name = line[:start-1]
  return name, params

def extract_function_code(content_line_by_line, line_of_func):
  function_code = ""
  # content_line_by_line = content.split("\n")
  flag = False
  indent = 0
  for line_no, line in enumerate(content_line_by_line):
    if len(line.strip()) <= 0:
      continue
    # if comment
    if line.strip().startswith("#"):
      continue
    if line_no == line_of_func:
      indent = len(line) - len(line.lstrip())
      flag = True
    # if (line.strip().startswith("def")) and not (function_name in line):
    else:
      if indent >= len(line) - len(line.lstrip()):
        flag = False
    if flag:
      # if import
      if line.strip().startswith("import ") or line.strip().startswith("from "):
        continue
      function_code = function_code + line[indent:] + "\n"
  return function_code

def read_functions(content_line_by_line):
  Functions = {}
  for line_no, line in enumerate(content_line_by_line):
    # if comment
    if line.strip().startswith("#"):
      continue
    # if function head
    if line.strip().startswith("def"):
      func_name, _, _ = extract_function_info(line)
      Functions[func_name] = extract_function_code(content_line_by_line, line_no)
  return Functions

# which char in input_str is related to the first bracket in input_str
# return -1 as error, 0 as no bracket
def find_correspond_bracket(input_str):
  # open_brackets = '([{<'
  # close_brackets = ')]}>'
  # brackets_map = {')': '(', ']': '[', '}': '{', '>': '<'}
  open_brackets = '([{'
  close_brackets = ')]}'
  brackets_map = {')': '(', ']': '[', '}': '{'}
  quotation = '\'"'

  stack = []
  contain_bracket = False
  last_quotation = ''
  for i, char in enumerate(input_str):
    if char in quotation:
      if i>0:
        if input_str[i-1] == '\\':
          continue
      if last_quotation == '':
        last_quotation = char
      elif last_quotation == char:
        last_quotation = ''
      continue
    if len(last_quotation)>0:
      continue # things happen in string, don't need to do anything
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


def extract_indent(line):
  indent_pos = len(line) - len(line.lstrip())
  indent = line[:indent_pos]
  return indent

# turn multiple functions into one
# only helps on simple functions, support multiple returns
# do not support f(g(x)).
# do not support changed order params
def inline_functions(Functions, target_function, content_line_by_line):

  Counter = {}
  def get_no(func_name):
    if func_name in Counter.keys():
      no = Counter[func_name] + 1
      Counter[func_name] = no
      return no
    else:
      Counter[func_name] = 0
      return 0

  if not target_function in Functions.keys():
    return Functions

  # get imported libs
  imported_libs = set()
  for line in content_line_by_line:
    if line.strip().startswith("import "):
      line = line[line.find("import")+6:]
      if " as " in line:
        line = line[line.rfind(" as ")+3:]
      for lib in line.split(","):
        imported_libs.add(lib.strip())
    if line.strip().startswith("from ") and " import " in line:
      line = line[line.find("import")+6:]
      if " as " in line:
        line = line[line.rfind(" as ")+3:]
      for lib in line.split(","):
        imported_libs.add(lib.strip())

  global_vars = set()
  for line in content_line_by_line:
    if len(line) == len(line.lstrip()) and "=" in line:
      global_vars.add(line.split("=")[0].strip())

  is_changed = True
  while is_changed:
    is_changed = False
    new_func = []
    for line in Functions[target_function].split('\n'):
      if line.strip().startswith("def"):
        new_func.append(line)
        continue
      
      # print("=============="+line)
      all_names = jedi.names(line, all_scopes=True, definitions=True, references=True)
      col_fix = 0
      for name in all_names:
        if name.name:
          if name.name in Functions.keys() and name.name != target_function and not name.is_definition():
            # incase user defined function has same name as ML API:
            if line[:name.column].strip().endswith("."):
              continue

            start = name.column + col_fix
            end = find_correspond_bracket(line[start:]) + start + 1
            func_call = line[start:end]
            func_name, func_inputs = extract_function_call(func_call)
            var_for_func = func_name + "_call" + str(get_no(func_name))
            col_fix += len(var_for_func) - len(func_call)
            line = line.replace(func_call, var_for_func, 1)
            
            # start inlining
            is_changed = True
            new_func.append("")
            _, func_params, default_values = extract_function_info(Functions[func_name].split("\n")[0])
            # print(str((func_inputs, func_params, default_values)))

            indent_pos = len(line) - len(line.lstrip())
            indent = line[:indent_pos]
            variable_mapping = {}
            # deal with params
            for i in range(len(func_params)):
              if i<len(func_inputs):
                new_func.append(indent+ var_for_func+"_"+func_params[i] +" = "+func_inputs[i])
              else:
                if not default_values[i]:
                  print("Error: [inline_functions] function call missing parameters")
                new_func.append(indent+ var_for_func+"_"+func_params[i] +" = "+default_values[i])
              variable_mapping[func_params[i]] = var_for_func+"_"+func_params[i]

            # deal with function body
            new_func.append(indent+ var_for_func+"_isreturned = False")
            func_content_lines = Functions[func_name].split("\n")[1:]
            indent_fix_pos = len(func_content_lines[0]) - len(func_content_lines[0].lstrip())
            indent_fix = line[:indent_fix_pos]
            has_return = False
            for to_inline in func_content_lines:
              origin_to_inline = to_inline
              # to_inline = indent_fix + to_inline[indent_pos:]
              to_inline = indent + to_inline[indent_fix_pos:]
              inline_col_fix = 0
              modified = set()
              to_inline_names = jedi.names(to_inline, all_scopes=True, definitions=True, references=True)
              for var_name_id in range(len(to_inline_names)):
                var_name = to_inline_names[var_name_id]
                # ignore field extraction
                if to_inline[var_name.column+inline_col_fix-1] == ".":
                  continue
                # ignore calling lib
                if var_name.name in imported_libs:
                  continue
                # ignore global vars
                if var_name.name in global_vars:
                  continue

                if var_name.is_definition():
                  var_col = var_name.column + inline_col_fix
                  inline_col_fix += len(var_for_func) + 1
                  variable_mapping[var_name.name] = var_for_func+"_"+var_name.name
                  to_inline = to_inline[:var_col] + variable_mapping[var_name.name] + to_inline[var_col+len(var_name.name):]
                  modified.add(var_name_id)
                  # to_inline.replace(var_name.name, variable_mapping[var_name.name], 1)
                else:
                  if var_name.name in variable_mapping.keys():
                    var_col = var_name.column + inline_col_fix
                    # remove situation like client.label_detection(image=image)
                    if to_inline[var_col+len(var_name.name):].strip().startswith("=") and not to_inline[var_col+len(var_name.name):].strip().startswith("=="):
                      continue                  
                    inline_col_fix += len(var_for_func) + 1
                    to_inline = to_inline[:var_col] + variable_mapping[var_name.name] + to_inline[var_col+len(var_name.name):]
                    modified.add(var_name_id)
                  else:
                    if not to_inline[var_name.column+len(var_name.name)+inline_col_fix:].strip().startswith("("): # not function call
                      var_col = var_name.column + inline_col_fix
                      # not so sure
                      # if to_inline[var_col+len(var_name.name):].strip().startswith("=") and not to_inline[var_col+len(var_name.name):].strip().startswith("=="):
                        # continue
                      inline_col_fix += len(var_for_func) + 1
                      variable_mapping[var_name.name] = var_for_func+"_"+var_name.name
                      to_inline = to_inline[:var_col] + variable_mapping[var_name.name] + to_inline[var_col+len(var_name.name):]
                      modified.add(var_name_id)

              # second round in case [x for x in list]
              inline_col_fix = 0
              to_inline_names = jedi.names(to_inline, all_scopes=True, definitions=True, references=True)
              for var_name_id in range(len(to_inline_names)):
                var_name = to_inline_names[var_name_id]
                if to_inline[var_name.column+inline_col_fix-1] == ".":
                  continue
                if (not var_name.is_definition()) and (not var_name_id in modified):
                  if var_name.name in variable_mapping.keys():
                    var_col = var_name.column + inline_col_fix
                    if to_inline[var_col+len(var_name.name):].strip().startswith("="):
                      continue               
                    inline_col_fix += len(var_for_func) + 1
                    to_inline = to_inline[:var_col] + variable_mapping[var_name.name] + to_inline[var_col+len(var_name.name):]
              # returns
              if to_inline.lstrip().startswith("return "):
                indent2 = extract_indent(to_inline)
                new_func.append(indent2+"if not " + var_for_func+"_isreturned:")
                new_func.append(indent2+"  "+ var_for_func+"_isreturned = True")
                to_inline = "  " + to_inline.replace("return ", var_for_func+" = ")
                has_return = True
                
              elif to_inline.lstrip().startswith("return(") or to_inline.lstrip().startswith("return[") or to_inline.lstrip().startswith("return{"):
                new_func.append(indent2+"if not " + var_for_func+"_isreturned:")
                new_func.append(indent2+"  "+ var_for_func+"_isreturned = True")
                to_inline = "  " + to_inline.replace("return ", var_for_func+" = ")
                has_return = True
              new_func.append(to_inline)
              update_if_statement_changes(origin_to_inline, to_inline)
            # if no return sentence
            if not has_return:
              new_func.append(indent_fix+var_for_func+" = None")
            # if the result of function call is not used
            if line.strip() == var_for_func:
              line = ""
      new_func.append(line)


    Functions[target_function] = "\n".join(new_func)

  # inline code outside any functions, but before target_function
  global_cmds = []
  indent_line = new_func[1]
  for i in range(1,len(new_func)):
    if len(new_func[i].strip()) > 0:
      indent_line = new_func[i]
      break
  indent_pos = len(indent_line) - len(indent_line.strip())
  indent = indent_line[:indent_pos]
  for line in content_line_by_line:
    if line.strip().startswith("import "):
      continue
    if line.strip().startswith("from ") and " import " in line:
      continue
    if line.strip().startswith("def"):
      func_name, _, _ = extract_function_info(line)
      if func_name == target_function:
        break
      else:
        continue
    if len(line) == len(line.lstrip()):
      global_cmds.append(indent+line)
  new_func = new_func[:1] + global_cmds + new_func[1:]

  new_Functions = {}
  new_Functions[target_function] = "\n".join(new_func)
  return new_Functions, imported_libs

def inline_functions_helper(src_file, dest_file, target_function):
  content_line_by_line = readfile_without_comments(src_file)
  content_line_by_line = merge_lines(content_line_by_line)
  # content_line_by_line = adhoc_fixes(content_line_by_line)

  Functions = read_functions(content_line_by_line)
  Functions = inline_readfiles(Functions, os.path.dirname(src_file))
  Functions, imported_libs = inline_functions(Functions, target_function, content_line_by_line)

  f2 = open(dest_file, 'w')
  # f2.write("import sys\n")
  # f2.write("sys.path.append('../')\n")
  f2.write("from symbolic.args import *\n")
  for line in content_line_by_line:
    if len(line.strip()) <= 0:
      continue
    if line.strip().startswith("#"):
      continue
    for client in Client:
      if (client+"(") in line:
        continue
    indent = len(line) - len(line.lstrip())
    if indent==0 and not line.startswith("def"):
      f2.write(line+"\n")
  f2.write("\n# ==================\n")
  for func_name in Functions.keys():
    f2.write(Functions[func_name])
    f2.write("\n# ==================\n")
  f2.close()


# if there is readfile operations, inline file content to code
# the file path must be a hardcoded value
# TODO: support more file path input
def inline_readfiles(Functions, working_folder, inline_lines=INLINE_FILE_LINE):
  if not os.path.isdir(working_folder):
    print("[Error] inline_readfiles: working_folder must be a directory")

  for func_name in Functions.keys():
    func_lines = Functions[func_name]
    new_func_lines = ""

    Var_to_filepath = {}
    for line in func_lines.split("\n"):
      need_revise = False
      all_names = jedi.names(line, all_scopes=True, definitions=True, references=True)

      for i, name in enumerate(all_names):
        # style of f=open(xxxx) and f=open(xxx,'w')
        if name.name == "open" and line[name.column+4:].strip()[0]=='(' and line[:name.column].strip()[-1]=='=':
          if all_names[0].is_definition():
            need_revise = True
            file_var = all_names[0].name
            start = line[name.column:].find("(") + name.column
            end = start+ find_correspond_bracket(line[start:])
            file_path = line[start+1:end].split(",")[0].strip()
            # hardcoded string
            if (file_path[0]=='\"' and file_path[-1]=='\"') or (file_path[0]=='\'' and file_path[-1]=='\''):
              Var_to_filepath[file_var] = file_path[1:-1]
            else:
              print("[Error] inline_readfiles: read file must be operated on a hardcoded file path")

        # style of f.close()
        if name.name == "close" and line[name.column+5].strip()[0]=='(' and line[:name.column].strip()[-1]=='.':
          if i>=1:
            if all_names[i-1].name in Var_to_filepath.keys():
              need_revise = True
              # in case repeated assign
              Var_to_filepath.pop(all_names[i-1].name)

        # style of xx = f.readlines()
        if name.name == "readlines" and line[name.column+9:].strip()[0]=='(':
          if i>=1:
            if all_names[i-1].name in Var_to_filepath.keys():
              need_revise = True
              file_path = os.path.join(working_folder, Var_to_filepath[all_names[i-1].name])
              revised_line = line[:all_names[i-1].column] + "["
              file_content = read_wholefile(file_path, preprocess=False).split("\n")
              # only inline part of the file
              if INLINE_FILE_LINE < len(file_content):
                file_content = file_content[:INLINE_FILE_LINE]
              for file_line in file_content:
                revised_line += "\"" + file_line.replace("\"","\\\"").replace("\'","\\\'").replace("\\","\\\\").replace("\t","\\t") + "\\n\", "
              revised_line = revised_line[:-2] + "]"
              new_func_lines += revised_line + "\n"
            else:
              print("[Error] inline_readfiles: Cannot found corresponding file")
        # style of xx = f.read
        if name.name == "read" and line[name.column+4:].strip()[0]=='(':
          if i>=1:
            if all_names[i-1].name in Var_to_filepath.keys():
              need_revise = True
              file_path = os.path.join(working_folder, Var_to_filepath[all_names[i-1].name])
              if file_path.endswith(".txt"):
                revised_line = line[:all_names[i-1].column] + "\""
                file_content = read_wholefile(file_path, preprocess=False).split("\n")
                # only inline part of the file
                if INLINE_FILE_LINE < len(file_content):
                  file_content = file_content[:INLINE_FILE_LINE]
                for file_line in file_content:
                  revised_line += file_line.replace("\"","\\\"").replace("\'","\\\'").replace("\\","\\\\").replace("\t","\\t") + "\\n"
                revised_line = revised_line[:-2] + "\""
                new_func_lines += revised_line + "\n"

      if not need_revise:
        new_func_lines += line + "\n"
    Functions[func_name] = new_func_lines

  return Functions

# remove comments
# reference: https://gist.github.com/BroHui/aca2b8e6e6bdf3cb4af4b246c9837fa3#file-remove_comments-py
def readfile_without_comments(src_file):
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
      if False:#toktype == token.STRING and prev_toktype == 58: # newline
        pass
      elif toktype == token.STRING and (prev_toktype == token.DEDENT or prev_toktype == token.INDENT):
          # Docstring
          pass
      elif toktype == tokenize.COMMENT:
          # Comment
          pass
      else:
          new_content += ttext
      prev_toktype = toktype
      last_col = ecol
      last_lineno = elineno
  #adhoc fix1
  new_content = new_content.replace(".lower()","")

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

  lines = [x for x in lines if len(x.strip())>0]
  #adhoc fix2
  # lines = [x for x in lines if not 'os.path.' in x]
  return lines

def readfile_without_comments_not_support_tab(src_file):
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
      if toktype == token.STRING and (prev_toktype == token.DEDENT or prev_toktype == token.INDENT):
          # Docstring
          pass
      elif toktype == tokenize.COMMENT:
          # Comment
          pass
      else:
          new_content += ttext
      prev_toktype = toktype
      last_col = ecol
      last_lineno = elineno
  #adhoc fix1
  new_content = new_content.replace(".lower()","")
  lines = new_content.split("\n")
  lines = [x for x in lines if len(x.strip())>0]
  #adhoc fix2
  # lines = [x for x in lines if not 'os.path.' in x]
  return lines

# force one code sentence only takes one line
# requires calling readfile_without_comments first
def merge_lines(content_line_by_line):
  new_lines = []
  is_breakline = False
  for line in content_line_by_line:
    line = line.rstrip()
    if is_breakline:
      new_lines[-1] = new_lines[-1] + " " + line.strip()
      # if the first open bracket has its close bracket
      if find_correspond_bracket(new_lines[-1]) >= 0:
        is_breakline = False
    else:
      if len(line)>0:
        new_lines.append(line)
      # if the first open bracket doesn't have its close bracket
      if find_correspond_bracket(line) < 0:
        is_breakline = True
  return new_lines


# do some adhoc fixes
def adhoc_fixes(content_line_by_line):

  new_lines = []
  
  Tokenized = {}

  max_no = len(content_line_by_line)
  line_no = -1
  while  line_no+1 < max_no:
    line_no += 1
    line = content_line_by_line[line_no]
    line_without_space = line.replace(" ","")

    # adhoc 1: ignore lower on strings, and decode('utf-8')
    line = line.replace(".lower()","")
    line = line.replace(".decode('utf-8')","").replace(".decode(\"utf-8\")","")
    # adhoc 2: remove os.path related operations
    if "os.path." in line and not line.strip().startswith("if ") and not line.strip().startswith("elif "):
      update_if_statement_changes(line, "")
      continue

    # adhoc 3: replace nltk.word_tokenize (Speech/BlindHandAssistance.py)
    if "nltk.word_tokenize(" in line_without_space:
      all_names = jedi.names(line, all_scopes=True, definitions=True, references=True)
      if len(all_names) >=3:
        if all_names[0].is_definition():
          tokenized_output = all_names[0].name
          for i, name in enumerate(all_names):
            if name.name == "word_tokenize" and line[name.column+13:].strip()[0]=='(':
              start = line[name.column:].find("(") + name.column
              end = start+ find_correspond_bracket(line[start:])              
              tokenized_input = line[start+1:end]
              Tokenized[tokenized_output] = tokenized_input
      continue
    if "nltk.pos_tag(" in line_without_space:
      all_names = jedi.names(line, all_scopes=True, definitions=True, references=True)
      if len(all_names) >=3:
        if all_names[0].is_definition():
          list_output = line[:line.find("=")]
          for i, name in enumerate(all_names):
            if name.name in Tokenized.keys():
              list_input = Tokenized[name.name]
              Tokenized.pop(name.name)
              new_lines.append(list_output +" = "+ list_input+".split()")
              break
      continue

    #adhoc 4: turn a=client.MLAPI().xxx into two lines
    ml_api_pos = -1
    for ml_api in (Vision_API+Speech_API+Language_API):
      if "."+ml_api+"(" in line_without_space:
        all_names = jedi.names(line, all_scopes=True, definitions=True, references=True)
        if all_names[0].is_definition():
          var_output = line[:line.find("=")-1]
          ml_api_pos = -1
          for name in all_names:
            if name.name == ml_api:
              ml_api_pos = name.column
              break
          if ml_api_pos<0:
            continue
          func_call_end = find_correspond_bracket(line[ml_api_pos:]) + ml_api_pos + 1
          if line[func_call_end:].strip().startswith("."):
            line1 = line[:func_call_end]
            line2 = var_output +" = "+ all_names[0].name + line[func_call_end:]
            new_lines.append(line1)
            new_lines.append(line2)
          else:
            new_lines.append(line)
    if ml_api_pos>0:
      continue

    # adhoc 5: if isinstance(text, six.binary_type):  xxx
    if line_without_space.startswith("ifisinstance(") and "if isinstance" in line.replace("  "," "):
      if_pos = line.find("if")
      line_if = line[:if_pos] + "if True:"
      new_lines.append(line_if)
      update_if_statement_changes(line, line_if)
      continue
    
    # adhoc 6: turn `total_score / len(sentiments)` to `total_score * (1.0/len(sentiments))`
    if "/len(" in line_without_space:
      len_pos = line.find("len")
      while not line[len_pos+3:].strip().startswith("(") or not line[:len_pos].endswith("/"):
        len_pos = line[len_pos+3:].find("len") + len_pos+3
      end_pos = find_correspond_bracket(line[len_pos:]) + len_pos+1
      line1 = line[:len_pos].rstrip()[:-1] + " *(1.0/" + line[len_pos:end_pos] + ")" + line[end_pos:]
      new_lines.append(line1)
      update_if_statement_changes(line, line1)
      continue

    # adhoc 7: a = enums.Entity.Type(b) -> a=b
    if "Entity.Type(" in line_without_space:
      type_pos = line.find("Type")
      while not line[type_pos+4:].strip().startswith("(") or not line[:type_pos].endswith("."):
        len_pos = line[len_pos+4:].find("Type") + type_pos+4
      type_pos += 4
      end_pos = find_correspond_bracket(line[type_pos:]) + type_pos+1
      start = line.find("Entity")
      if "enums" in line[:start]:
        start = line.find("enums")
      line1 = line[:start] + line[type_pos:end_pos].strip()[1:-1] + line[end_pos:].strip()[:]
      new_lines.append(line1)
      update_if_statement_changes(line, line1)
      continue

    # adhoc 8: response.error.message - > False
    if ".error.message" in line_without_space:
      start = None
      end_pos = None
      all_names = jedi.names(line, all_scopes=True, definitions=False, references=True)
      for name_no, name in enumerate(all_names):
        if name.name == "error" and name_no>0:
          start = all_names[name_no-1].column
        if name.name == "message":
          end_pos = name.column + len("message")
      if start!=None and end_pos!=None:
        line1 = line[:start] + "False" + line[end_pos:]
        new_lines.append(line1)
        update_if_statement_changes(line, line1)
        continue

    new_lines.append(line)
  return new_lines


def remove_comments_helper(src_file, dest_file):
  # content = read_wholefile(src_file)
  content_line_by_line = readfile_without_comments(src_file)
  content_line_by_line = merge_lines(content_line_by_line)

  content = "\n".join(content_line_by_line)
  f = open(dest_file, 'w')
  f.write(content)
  f.close()



# field extraction, list extract, and some loop
def fix_var_extract(func_content):
  new_func = []
  api_related_vars = set()
  list_vars = set()
  list_vars_add_define = set()
  used_ml_api = []
  multi_api_api_2_input = [] # what is the input of an ML API [ [api, input],  ... ]
  multi_api_vars_2_api = {} # which value is related to which API

  for line in func_content:
    origin_line = line
    # if function head
    if line.strip().startswith("def"):
      new_func.append(line)
      continue

    # print("========================"+line)
    all_names = jedi.names(line, all_scopes=True, definitions=True, references=True)
    if len(all_names)<=0:
      new_func.append(line)
      continue
    
    # For testing only
    # new_func.append(str(api_related_vars))
    # new_func.append(str(list_vars))
    
    # directly call API
    is_api_related = False
    related_api = None
    for name_no, name in enumerate(all_names):
      if name.name:
        if (name.name in Vision_API or name.name in Speech_API or name.name in Language_API) and ("."+name.name+"(" in line.replace(" ","")):
          indent =  extract_indent(line)
          new_func.append(indent+"# [Extra notation] Function call of " + name.name) # for solve_precondition.py
          # TODO: there might be other cases, e.g. recognize(config, audio)
          # use the first param of API as its input
          if name_no+1 < len(all_names):
            input_param = all_names[name_no+1].name
          else: # it is another API shares similar name
            input_param = None
          used_ml_api.append(name.name)
          is_api_related = True
          related_api = name.name
          multi_api_api_2_input.append([name.name, input_param])
          break
    # thins like vision.enums.TextAnnotation.DetectedBreak.BreakType
    for i, name in enumerate(all_names):
      if name.name == "TextAnnotation" and i>0 and i+1<len(all_names):
        if all_names[i-1].name == "enums" or all_names[i+1].name == "DetectedBreak":
          is_api_related = True
          related_api = "text_detection"
    if all_names[0].is_definition() and is_api_related:
      api_related_vars.add(all_names[0].name)
      multi_api_vars_2_api[all_names[0].name] = related_api
    
    # fix dot
    contains_dot = True
    while contains_dot:
      contains_dot = False
      all_names = jedi.names(line, all_scopes=True, definitions=True, references=True)
      for name_no in range(len(all_names)):
        name = all_names[name_no]
        if name.name:
          if name.name in api_related_vars:
            is_api_related = True
            related_api = multi_api_vars_2_api[name.name]
            # if dot
            # ignore function call
            if name_no+1 < len(all_names):
              if line[all_names[name_no+1].column+len(all_names[name_no+1].name):].strip().startswith("("):
                continue
            if line[name.column+len(name.name):].strip().startswith(".") and name_no<len(all_names)-1:
              # line = line.replace(" .",".").replace(name.name+".", name.name+"__")
              # api_related_vars.add(name.name+"__"+all_names[name_no+1].name)
              field = all_names[name_no+1]
              line = line[:name.column] + name.name+"__"+field.name + line[field.column+len(field.name):]
              api_related_vars.add(name.name+"__"+field.name)
              multi_api_vars_2_api[name.name+"__"+all_names[name_no+1].name] = multi_api_vars_2_api[name.name]
              contains_dot = True
              # Not sure: solve some string case, e.g. vision/wanderStub
              if all_names[0].is_definition() and field.name in String_fields:
                list_vars.add(all_names[0].name)
                list_vars_add_define.add(all_names[0].name)
              break # one round only solve one dot

    # fix array, works for a[0], not for a[b] 
    all_names = jedi.names(line, all_scopes=True, definitions=True, references=True)
    unchanged_line = line
    for name_no in range(len(all_names)):
      name = all_names[name_no]
      if name.name:
        # Not sure if correct
        # [result.alternatives[0].transcript for result in recognition.results] case
        extra_flag = False
        if " for " in unchanged_line and " in " in unchanged_line:
          if all_names[-1].name in api_related_vars:
            extra_flag = True
        # if name.name in api_related_vars or "__" in name.name
        if name.name in api_related_vars or "__" in name.name or extra_flag:
          # if array
          if find_default_value(used_ml_api, name.name) == "\"\"":
              pass #  but not text.description[xx]
          elif line[name.column+len(name.name):].strip().startswith("["):
            start = name.column + len(name.name)+1
            # end = line[start:].find("]")+start
            end = find_correspond_bracket(line[start-1:])+start-1
            substr = line[start:end]

            # for dict, a['key']
            if substr.startswith("'") or substr.startswith("\""):
              continue

            if not name.name in list_vars:
              indent =  extract_indent(line)
              extra_line = indent + name.name + " = ["
              for var_no in range(LIST_LEN):
                extra_line += name.name + "_"+str(var_no)+"_" + ", "
                multi_api_vars_2_api[name.name + "_"+str(var_no)+"_"]= multi_api_vars_2_api[name.name]
                api_related_vars.add(name.name + "_"+str(var_no)+"_")
              new_func.append(extra_line[:-2]+"]")
              list_vars_add_define.add(name.name)
            list_vars.add(name.name)

            # if this list already be defined before, then a[0] is valid, don't need changes
            if not name.name in list_vars_add_define:
              line = line.replace("["+substr+"]", "_"+substr+"_")
            # for a[0].x cases
            if line[end:].strip().replace(" ","")[:2] == "].":
              line = line.replace("["+substr+"]", "_"+substr+"_")
              if "." in line[end:]: # a[0].x.y
                dot_pos = end + line[end:].rfind(".") # a[0].x[0].y 
                line = line[:end] + line[end:dot_pos].replace("[","_").replace("]","_").replace(".","__")+ line[dot_pos:]
                tmp_names = jedi.names(line[name.column:], all_scopes=True, definitions=True, references=True) 
                multi_api_vars_2_api[tmp_names[0].name] = related_api

            new_var_name = name.name+"_"+substr+"_"
            if name.name in api_related_vars:
              is_api_related = True
              related_api = multi_api_vars_2_api[name.name]
              api_related_vars.add(new_var_name)
              multi_api_vars_2_api[new_var_name] = multi_api_vars_2_api[name.name]
              # ignore function call
              if name_no+1 < len(all_names):
                # if all_names[name_no+1].name+"(" in line.replace(" ",""):
                if line[all_names[name_no+1].column+len(all_names[name_no+1].name):].strip().startswith("("):
                  continue
              line = line.replace(new_var_name+".", new_var_name+"__")
              # Not sure: solve some string case, e.g. vision/wanderStub
              if name_no+1<len(all_names): 
                if all_names[0].is_definition() and all_names[name_no+1].name in String_fields:
                  list_vars.add(all_names[0].name)
                  list_vars_add_define.add(all_names[0].name)

      # a=b.split(), list.append(), a=[b], a=defaultdict(int)
      if name.name:
        if (name.name=="split" or name.name=="append" or name.name=="extend") and unchanged_line[name.column+len(name.name):].strip().startswith("("):
          if all_names[0].is_definition():
            list_vars.add(all_names[0].name)
            list_vars_add_define.add(all_names[0].name)
        if "["+name.name+"]" in unchanged_line.replace(" ",""):
          if all_names[0].is_definition():
            list_vars.add(all_names[0].name)
            list_vars_add_define.add(all_names[0].name)
        if name.name=="defaultdict" and unchanged_line[name.column+len(name.name):].strip().startswith("("):
          if all_names[0].is_definition():
            list_vars.add(all_names[0].name)
            list_vars_add_define.add(all_names[0].name)
      # len(a)
      if name.name and (name_no+1)<len(all_names):
        if name.name=="len" and unchanged_line[name.column+len(name.name):].strip().startswith("("):
          len_var_name = all_names[name_no+1].name
          if find_default_value(related_api, len_var_name) == "\"\"":
            pass #  but not len(text.description)
          elif (not len_var_name in list_vars) and (len_var_name in api_related_vars):
            indent_pos = len(line) - len(line.lstrip())
            extra_line = line[:indent_pos] + all_names[name_no+1].name + " = ["
            for var_no in range(LIST_LEN):
              extra_line += all_names[name_no+1].name + "_"+str(var_no)+"_" + ", "
              if name.name in api_related_vars:
                multi_api_vars_2_api[all_names[name_no+1].name + "_"+str(var_no)+"_"]= multi_api_vars_2_api[name.name]
                api_related_vars.add(all_names[name_no+1].name + "_"+str(var_no)+"_")
            list_vars_add_define.add(all_names[name_no+1].name)
            list_vars.add(len_var_name)
            new_func.append(extra_line[:-2]+"]")
      # a=[...], a={..}
      if name.name and name.is_definition():
        if line[name.column+len(name.name):].replace(" ","").startswith("=[") or line[name.column+len(name.name):].replace(" ","").startswith("={"):
          list_vars.add(name.name)
          list_vars_add_define.add(name.name)
      # a=xx+[xx]
      if name.name and not name.is_definition() and all_names[0].is_definition():
        if line[:name.column].strip().replace(" ","").endswith("+["):
          list_vars.add(all_names[0].name)
          list_vars_add_define.add(name.name)
        if line[:name.column].strip().replace(" ","").endswith("+") and name.name in list_vars_add_define:
          list_vars.add(all_names[0].name)
          list_vars_add_define.add(name.name)


    if all_names[0].is_definition() and is_api_related:
      api_related_vars.add(all_names[0].name)
      multi_api_vars_2_api[all_names[0].name] = related_api
      line = line.replace(all_names[0].name+".", all_names[0].name+"__")
    
    # monitor var_list and api_related_vars assigns
    all_names = jedi.names(line, all_scopes=True, definitions=True, references=True)
    if len(all_names)==2:
      assign_cmd = all_names[0].name + "=" + all_names[1].name
      line_clean_up = line.strip().replace(" ","").replace("\t","")
      if (all_names[1].name in list_vars) and (assign_cmd == line_clean_up):
        list_vars.add(all_names[0].name)
      if (all_names[1].name in list_vars_add_define) and (assign_cmd == line_clean_up):
        list_vars_add_define.add(all_names[0].name)
      if all_names[1].name in api_related_vars:
        api_related_vars.add(all_names[0].name)
        multi_api_vars_2_api[all_names[0].name] = multi_api_vars_2_api[all_names[1].name]
    # dict, zip, list ops
    if len(all_names)>=1:
      assign_cmd = all_names[0].name + "="
      line_clean_up = line.strip().replace(" ","").replace("\t","")
      if line_clean_up.startswith(assign_cmd+"zip(") or line_clean_up.startswith(assign_cmd+"list(") or line_clean_up.startswith(assign_cmd+"dict("):
        list_vars.add(all_names[0].name)


    # TODO: current implementation is super adhoc
    # if l__description in r:  should be turn into ==, otherwise l__description will be always assign as ''
    # if xxx.annotations: should be turn into if True
    if is_api_related and line.strip().startswith("if"):
      if "__description in " in line.replace("  "," "):
        all_names = jedi.names(line, all_scopes=True, definitions=True, references=True)
        str_before_in = None
        str_after_in = None
        for name_no in range(len(all_names)-1):
          name = all_names[name_no]
          if "__description" in name.name:
            pos = name.column + len(name.name)
            if line[pos:].strip().startswith("in"):
              str_before_in = all_names[name_no]
              str_after_in = all_names[name_no+1]
        if str_before_in:
          pos1 = str_before_in.column
          pos2 = str_after_in.column + len(str_after_in.name)
          line = line[:pos1] + "((" + line[pos1:pos2] + ") and len(" + str_before_in.name + ")>0)" + line[pos2:]
      if len(all_names) == 1 and "__" in all_names[0].name:
        if not check_api_field(used_ml_api, all_names[0].name):
          line = line.replace(all_names[0].name, "True")

    # fix for loop
    if is_api_related and line.strip().startswith("for"):
      if not " in " in line:
        print("Error: [fix_var_extract] Assume for loop as style 'for a in list' ")
      elif " range(" in line or " range (" in line.replace("  "," "): # for i in range(n)
        # do nothing
        continue
      else:
        if " enumerate(" in line or " enumerate (" in line.replace("  "," "): # for i,j in enumerate(a)
          for_pos = line.find("for ")
          line = line[:for_pos] + line[for_pos:].replace(" enumerate (", " enumerate(")
          enum_pos = line.find("in enumerate(")
          sub_vars = line[for_pos+4:enum_pos-1].strip().split(",")
          if len(sub_vars)!=2:
            print("Error: [fix_var_extract] wrong style of 'for a,b in enumerate(c)'  ")
          sub_var = sub_vars[1].strip()
          var_list_end = find_correspond_bracket(line[enum_pos:])+enum_pos
          var_list = line[enum_pos+len("in enumerate("):var_list_end].strip()
        else: # for a in xxx
          for_pos = line.find("for ")
          in_pos = line.find(" in")+1
          colon_pos = line.rfind(":")
          sub_var = line[for_pos+4:in_pos-1].strip()
          var_list = line[in_pos+3:colon_pos].strip()
       
        var_list_origin = var_list
        var_list_names = jedi.names(var_list, all_scopes=True, definitions=True, references=True)
        for name_no, name in enumerate(var_list_names):
          if name.name in api_related_vars:
            is_api_related = True
            if name_no+1 < len(var_list_names):
              next_name = var_list_names[name_no+1]
              if var_list_origin[next_name.column+len(next_name.name):].strip().startswith("("):
                continue
            var_list = var_list.replace(name.name+".", name.name+"__")
        var_list_no_space = var_list.replace(" ","")
        if var_list.startswith("[") and var_list.endswith("]"):# for i in [a]
          pass
        elif ".items()" in var_list_no_space or ".keys()" in var_list_no_space or ".values()" in var_list_no_space:# for i in a.items()
          list_vars.add(sub_var)
          list_vars_add_define.add(sub_var)
        else:
          if not var_list in list_vars:

            # print(str((sub_var,var_list)))
            extra_line = line[:for_pos]+var_list + " = ["
            for var_no in range(LIST_LEN):
              # extra_line += sub_var + "_"+str(var_no)+"_" ", "
              extra_line += var_list + "_"+str(var_no)+"_" + ", "
              if var_list in api_related_vars:
                multi_api_vars_2_api[var_list + "_"+str(var_no)+"_"]= multi_api_vars_2_api[var_list]
                api_related_vars.add(var_list + "_"+str(var_no)+"_")


            list_vars_add_define.add(var_list)
            list_vars.add(var_list) # added with previous line
            new_func.append(extra_line[:-2]+"]")
            # api_related_vars.add(var_list)
            if var_list in api_related_vars:
              api_related_vars.add(sub_var)
              multi_api_vars_2_api[sub_var] = related_api
              line = line.replace(sub_var+".", sub_var+"__")

    # for loop will skip this part, as is_definition = False
    if all_names[0].is_definition() and is_api_related:
      api_related_vars.add(all_names[0].name)
      multi_api_vars_2_api[all_names[0].name] = related_api
      line = line.replace(all_names[0].name+".", all_names[0].name+"__")

    # fix for loop inside list, e.g. [l.description for l in response.label_annotations]
    if " for " in line:
      for_pos = line.rfind(" for ") +1
      in_pos = line.rfind(" in ") +1
      if ("[" in line[:for_pos]) and ("]" in line[for_pos:]):
        bracket_pos = line.rfind("]")
        bracket_pos2 = line.rfind("[")
        sub_var = line[for_pos+4:in_pos-1].strip()
        var_list = line[in_pos+3:bracket_pos].strip()
        tmp_names = jedi.names(sub_var, all_scopes=True, definitions=True, references=True)
        sub_var = tmp_names[0].name
        tmp_names = jedi.names(var_list, all_scopes=True, definitions=True, references=True)
        var_list = tmp_names[0].name

        result_var = line[bracket_pos2+1:for_pos]
        old_result_var = result_var
        is_api_related_inside_list = False
        # [text for i, text in enumerate(texts) if i != 0]
        if " if " in var_list:
          var_list = var_list[:var_list.rfind(" if ")].strip()
        if var_list.replace(" ","").startswith("enumerate("):
          var_list = var_list[var_list.find("(")+1 : var_list.rfind(")")]
          sub_var = sub_var.split(",")[-1].strip()
        all_names = jedi.names(line, all_scopes=True, definitions=True, references=True)
        is_assign = line[all_names[0].column+len(all_names[0].name):].strip()[0] == "="
        for name in jedi.names(var_list, all_scopes=True, definitions=True, references=True):
          if name.name:
            if name.name in api_related_vars:
              var_list = var_list.replace(name.name+".", name.name+"__")
              is_api_related_inside_list = True

        for name in jedi.names(result_var, all_scopes=True, definitions=True, references=True):
          if name.name and is_api_related_inside_list:
            result_var = result_var.replace(name.name+".", name.name+"__")
        
        # [label.description for label in labels]
        if old_result_var != result_var:
          line = line.replace(old_result_var, result_var)

        var_list_no_space = var_list.replace(" ","")
        if ".items()" in var_list_no_space or ".keys()" in var_list_no_space or ".values()" in var_list_no_space:# for i in a.items()
          list_vars.add(sub_var)
          list_vars_add_define.add(sub_var)
        else:
          if not var_list in list_vars:
            extra_line = extract_indent(line)+var_list + " = ["
            for var_no in range(LIST_LEN):
              extra_line += var_list + "_"+str(var_no)+"_" ", "
            list_vars_add_define.add(var_list)
            new_func.append(extra_line[:-2]+"]")
            list_vars.add(var_list)
          if var_list in api_related_vars and is_assign:
            # api_related_vars.add(sub_var)
            # line = line.replace(sub_var+".", sub_var+"__")
            api_related_vars.add(all_names[0].name)
            multi_api_vars_2_api[all_names[0].name] = related_api
            if sub_var+"." in line:
              field = line[line.find("[")+len(sub_var)+2:for_pos-1].strip()
              field = field.replace(".", "__")
              tmp = line[:line.find("[")] + " ["
              for var_no in range(LIST_LEN):
                tmp += var_list + "_"+str(var_no)+"___"+field+", "
              line = tmp[:-2]+"]"
          # TODO: improve this condition e.g. if any([l in monument_list for l in labels]):
          if var_list in api_related_vars and not is_assign:
            # api_related_vars.add(sub_var)
            if sub_var+"." in line:
              field = line[line.find("[")+len(sub_var)+2:for_pos-1].strip()
              field = field.replace(".", "__")
            

    # print(line)
    new_func.append(line)
    update_if_statement_changes(origin_line, line)
  
  # print("api_related_vars:"+str(api_related_vars))
  # print("list_vars:"+str(list_vars))
  return new_func, api_related_vars, list_vars, used_ml_api, multi_api_api_2_input, multi_api_vars_2_api


def contain_client(code):
  for client in Client:
      if (client+"(") in code:
        return True
  return False

def find_default_value(used_ml_api, var):
  if used_ml_api==None:
    return 0
  if len(used_ml_api)==0:
    return 0
  if not isinstance(used_ml_api,list):
    used_ml_api = [used_ml_api]
  for api in used_ml_api:
    if not api in API_Fields.keys():
      print("Error: [find_default_value] "+str(api)+" not defined")
  
  for api in used_ml_api:
    while "___" in var:
      var = var.replace("___","__")
    fields = API_Fields[api]
    tmp = var.split("__")[-1]
    for tuples in fields:
      field, value = tuples
      if tmp == field:
        return value
  return 0

# used_ml_apis is list
def check_api_field(used_ml_apis, var):
  for used_ml_api in used_ml_apis:
    if not used_ml_api:
      continue
    if not used_ml_api in API_Fields.keys():
      print("Error: [check_api_field] "+str(used_ml_api)+" not defined")
      continue
    while "___" in var:
      var = var.replace("___","__")
    fields = API_Fields[used_ml_api]
    tmp = var.split("__")[-1]
    for tuples in fields:
      field, value = tuples
      if tmp == field:
        return True
  return False

# remove part of API call, change function parameter
def remove_unrelated(func_content, list_vars, used_ml_api, imported_libs):
  new_func = []
  retrieved_vars = set()
  retrieve_relation = {}

  
  # first round, remove API related code
  line_no = -1
  max_line_no = len(func_content)
  while line_no < max_line_no-1:
    line_no = line_no + 1
    line = func_content[line_no]
    # if function head
    if line.strip().startswith("def"):
      new_func.append(line)
      continue

    line_strip = line.strip().replace(" ","").replace("\t","")
    # remove API functions, file read
    if ("with io.open(" in line and "'rb') as " in line and "image_file" in line) or \
       ("with io.open(" in line and "\"rb\") as " in line and "image_file" in line) or \
       ("with open(" in line and "'rb') as " in line and "image_file" in line) or \
       ("with open(" in line and "\"rb\") as " in line and "image_file" in line) or \
       ("with io.open(file_name, \"rb\") as " in line and "audio_file" in line) or \
       ("with io.open(file_name, 'rb') as " in line and "audio_file" in line) or \
       ("with io.open(" in line and "file_name, \"rb\") as" in line) or \
       ("with io.open(" in line and "file_name, \'rb\') as" in line) or \
       ("audio_file = open" in line and "file_path, 'rb')" in line) or \
       ("audio_file = open" in line and "file_path, \"rb\")" in line):
      line_no = line_no + 1
      continue
    #=============== newly added - start ==================
    if ("withio.open(" in line_strip and "'rb')as" in line_strip and "image_file" in line_strip) or \
       ("withio.open(" in line_strip and "\"rb\")as" in line_strip and "image_file" in line_strip) or \
       ("withopen(" in line_strip and "'rb')as" in line_strip and "image_file" in line_strip) or \
       ("withopen(" in line_strip and "\"rb\")as" in line_strip and "image_file" in line_strip) or \
       ("withio.open(file_name,\"rb\")as " in line_strip and "audio_file" in line_strip) or \
       ("withio.open(file_name,'rb')as " in line_strip and "audio_file" in line_strip) or \
       ("withio.open(" in line_strip and "file_name,\"rb\")as" in line_strip) or \
       ("withio.open(" in line_strip and "file_name,\'rb\')as" in line_strip) or \
       ("audio_file=open" in line_strip and "file_path,'rb')" in line_strip) or \
       ("audio_file=open" in line_strip and "file_path,\"rb\")" in line_strip):
      line_no = line_no + 1
      continue
    if ("withio.open(" in line_strip) or ("withopen(" in line_strip):
      line_no = line_no + 1
      continue
    if ("=open(" in line_strip) or (".read()" in line_strip):
      continue
    #=============== newly added - end ==================
    if "types.Image(content=" in line or "types.Document" in line or "speech.RecognitionAudio(" in line or ("Image.open" in line) or ".Image(content=" in line or \
      "types.Image(content=" in line_strip or "types.Document" in line_strip or "speech.RecognitionAudio(" in line_strip or ("Image.open" in line_strip) or ".Image(content=" in line_strip:
      if "types.Document" in line: # speciall for solve_precondition.py
        start = line.find("types.Document")
        line2 = line[start:]
        end = find_correspond_bracket(line2)
        line2 = line2[:end]
        func_name, params = extract_function_call(line2)
        params1 = [x.strip() for x in params if not "enums.Document" in x]
        params2 = []
        for x in params1:
          start = line.find(x)
          line3 = line[:start].strip()
          if line3.endswith("="):
            if line3.replace(" ","").replace("\t","").endswith("content="):
              params2.append(x)
          else:
            params2.append(x)
        new_func.append(extract_indent(line)+"# [Extra notation] API input from: "+str(params2))
      continue
    if "RecognitionConfig" in line or "audio_file.read()" in line or "language_code=" in line or ("with io.open(" in line and "rb\") as audio_file" in line) or ("with io.open(" in line and "rb\') as audio_file" in line):
      continue
    if "enums.TextAnnotation." in line or "TextAnnotation.DetectedBreak" in line:
      continue
    if contain_client(line):
      continue
    

    # check wether a parameter has been retrieved
    all_names = jedi.names(line, all_scopes=True, definitions=True, references=True)
    for name in all_names:
      if name.name:
        if "__" in name.name:
          tmp = name.name.split("__")
          retrieved_vars.add(tmp[0])
          retrieve_relation[tmp[1]] = tmp[0]
    new_func.append(line)


  # second round, remove retrieved vars
  func_content = new_func
  new_func = []
  line_no = -1
  max_line_no = len(func_content)
  while line_no < max_line_no-1:
    line_no = line_no + 1
    line = func_content[line_no]

    # # if empty
    # if len(line.strip())==0:
    #   continue
    # if function head
    if line.strip().startswith("def"):
      new_func.append(line)
      continue
    
    # if a is never retrieved in a=client.MLAPI()
    all_names = jedi.names(line, all_scopes=True, definitions=True, references=True)
    for name in all_names:
      if line[name.column+len(name.name):].strip().startswith("(") and line[:name.column].strip().endswith("."):
        if (name.name in Vision_API) or (name.name in Speech_API) or (name.name in Language_API):
          if all_names[0].is_definition():
            output_var = line[:line.find("=")]
            line = output_var + "= \"None\"" 

    new_func.append(line)

  # third round, find vars to solve
  defined_vars = set()
  referenced_vars = set()
  var_to_solve = set()
  new_func_content = "\n".join(new_func)
  all_names = jedi.names(new_func_content, all_scopes=True, definitions=True, references=True)
  for name in all_names:
    if name.name:
      # ignore functions
      if name.column+len(name.name) < len(new_func[name.line-1]):
        if new_func[name.line-1][name.column+len(name.name)] == "(":
          continue
      if name.is_definition():
        defined_vars.add(name.name)
      else:
        if not name.name in defined_vars:
          var_to_solve.add(name.name)
        referenced_vars.add(name.name)
  
  var_to_solve = list(var_to_solve)
  var_to_solve.sort()

  func_name, func_params, func_param_value = extract_function_info(new_func[0])
  func_fix = ["@symbolic(", "def "+func_name+"("] # one for @symbolic, one for def function
  # indent_pos = len(new_func[1]) - len(new_func[1].strip())
  # indent = new_func[1][:indent_pos]
  indent_line = new_func[1]
  for i in range(1,len(new_func)):
    if len(new_func[i].strip()) > 0:
      indent_line = new_func[i]
      break
  indent_pos = len(indent_line) - len(indent_line.strip())
  indent = indent_line[:indent_pos]
  # fix origin inputs
  for i, func_param in enumerate(func_params):
    # new_code = indent + func_param +" = \"None\""
    # func_fix.append(new_code)
    if func_param:
      if func_param_value[i]:
        func_fix[0] += func_param+"="+str(func_param_value[i])+", "
      else:
        func_fix[0] += func_param+"="+str(0)+", "
      func_fix[1] += func_param+", "
  # create new inputs
  for var in var_to_solve:
    if var in imported_libs:
      continue
    var_name = var
    # if is list
    # print(var[-1])
    start = var[:-1].rfind("_")
    if start>=0:
      if var[:start] in list_vars and var.endswith("_"):
        start = var[:-1].rfind("_")
        no = int(var[start+1:-1])
        var_name = var[:start]
    default_value = find_default_value(used_ml_api, var_name)

    # print(str((var_name,default_value)))
    func_fix[0] += var+"="+str(default_value)+", "
    func_fix[1] += var+", "
  if func_fix[0].endswith(", "):
    func_fix[0] = func_fix[0][:-2]+")"
    func_fix[1] = func_fix[1][:-2]+"):"
  else:
    func_fix[0] = func_fix[0]+")"
    func_fix[1] = func_fix[1]+"):"
  func_fix.extend(new_func[1:])
  return func_fix, retrieve_relation

def update_if_statement_changes(origin, new_code):
  global If_statement_changes
  # if origin == new_code:
  #   return
  if origin.strip().startswith("if") or origin.strip().startswith("elif") or origin.strip().startswith("for") or origin.strip().startswith("while"):
    If_statement_changes[origin] = new_code
  return


# main function
def change(src_file, dest_file, target_function=None):
  print("Process on "+str(src_file)+" ...")
  global If_statement_changes
  If_statement_changes = {} # origin -> new

  if not target_function:
    target_function = src_file.split("/")[-1][:-3]
  content_line_by_line = readfile_without_comments(src_file)
  content_line_by_line = merge_lines(content_line_by_line)
  content_line_by_line = adhoc_fixes(content_line_by_line)
  used_ml_api = []

  Functions = read_functions(content_line_by_line) #(content)
  Functions = inline_readfiles(Functions, os.path.dirname(src_file))
  Functions, imported_libs = inline_functions(Functions, target_function, content_line_by_line)
  
  # actually Functions will only contain one func
  for func_name in Functions.keys():
    func_content = Functions[func_name].split("\n")
    func_fix, api_related_vars, list_vars, used_ml_api, multi_api_api_2_input, multi_api_vars_2_api = fix_var_extract(func_content)
    func_fix, retrieve_relation = remove_unrelated(func_fix, list_vars, used_ml_api, imported_libs)
    Functions[func_name] = "\n".join(func_fix)

  f2 = open(dest_file, 'w')
  f2.write("from symbolic.args import *\n")
  for line in content_line_by_line:
    if len(line.strip()) <= 0:
      continue
    if line.strip().startswith("#"):
      continue
    if line.strip().startswith("import "):
      f2.write(line.strip()+"\n")
    if line.strip().startswith("from ") and " import " in line:
      f2.write(line.strip()+"\n")
  f2.write("\n# ==================\n")
  for func_name in Functions.keys():
    f2.write(Functions[func_name])
    f2.write("\n# ==================\n")
  f2.write("\n# used_ml_api: "+str(', '.join(used_ml_api)))
  f2.write("\n# ml_api_to_input: "+str(multi_api_api_2_input))
  f2.write("\n# output_to_ml_api: "+str(multi_api_vars_2_api))
  f2.write("\n# If_statement_changes: "+str(If_statement_changes))
  f2.close()





if __name__ == '__main__':
  pass
  change("test_apps/mid_value.py","test_apps/mid_value_new.py", "mid_value")










