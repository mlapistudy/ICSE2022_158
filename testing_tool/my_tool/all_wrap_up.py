import os
import sys
import subprocess
import json
from collections import Counter
import ast
import logging
import argparse
from pathlib import Path
import re

from global_vars import *
import change_code as change_code
import solve_multi as solve
import label_suggestion as label_suggestion
import sentiment_suggestion as sentiment_suggestion
from code_extraction.extract import Extractor

METADATA_IMG = {} # {img_path : API_result}
METADATA_TEXT = {} # {text_content : API_result}

logger = logging.getLogger(__name__)

def run_command(command):
  print(command)
  proc = subprocess.Popen(command, shell=True)
  proc.wait()

def generate_test_file(input_file, info_file, test_file, target_function):
  func_params = ""
  line_map = {}  # test_file -> input file
  line_fix = 0

  content = change_code.read_wholefile(input_file, preprocess=False)
  # extra_line = solve.get_extra_info(info_file, "import fix")
  python_fuzz_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
  extra_line = f'import os, sys\nsys.path.append("{python_fuzz_path}")'
  # extra_line = "\n".join(extra_line) + "\nfrom fuzztool.pythonfuzz.main import PythonFuzz\n"
  extra_line = extra_line + "\nfrom fuzztool.pythonfuzz.main import PythonFuzz\n"
  line_fix += 3

  f = open(test_file, "w")
  f.write(extra_line+"\n")
  line_fix += 1
  code_lines = content.split("\n")
  for (line_no, line) in enumerate(code_lines):
    # if function head
    if line.strip().startswith("def ") and ("def"+target_function+"(" in line.replace(" ","").replace("\t","")):
      func_name, params, default_value = change_code.extract_function_info(line)
      if func_name == target_function:
        f.write("@PythonFuzz\n")
        f.write(line+"\n")
        func_params = ""
        line_fix += 1
        line_map[line_fix+line_no] = line_no

        next_line = line_no+1
        while code_lines[next_line].strip().startswith("#") or len(code_lines[next_line].strip())==0:
          next_line = next_line + 1
        indent = change_code.extract_indent(code_lines[next_line])

        for (i, param) in enumerate(params):
          f.write(indent + param + " = sys.argv[" + str(i-len(params)) + "]\n")
          if eval(default_value[i]) == "API_input" :
            func_params += "API_input "
          else:
            func_params += param + " "
          line_fix += 1
        continue

    f.write(line+"\n")
    line_map[line_fix+line_no] = line_no
  
  f.write(target_function+"()\n")
  f.close()
  func_params = func_params[:-1]
  return func_params, params, line_map

def crash_bug_template():
  bug = {
        "bug_type": "Crash",
        "code_file": "",
        "lines_of_code": [],
        "function_name": "",
        "func_def_line": -1,
        "description": "The software crashes under these inputs.",
        "test_input": []
    }
  return bug

def accuracy_bug_template():
  bug = {
        "bug_type": "Accuracy",
        "code_file": "",
        "lines_of_code": [],
        "function_name": "",
        "func_def_line": -1,
        "description": "Your program suffers from accuracy problems: its judgement differs from most human beings for at least %2.f%% of the test inputs." % (100*(1-ACCURACY_THRESHOLD)),
        "test_input": [],
        "fix_suggestion": ""
    }
  return bug

def coverage_bug_template():
  bug = {
        "bug_type": "Dead Code",
        "code_file": "",
        "lines_of_code": [],
        "function_name": "",
        "func_def_line": -1,
        "description": "Your program contains dead code.",
        "test_input": []
    }
  return bug

def parse_covered_lines(coverage_list):
  result = coverage_list
  start = result.index("{")+1
  end = result.index("}")
  lines = result[start:end].replace(" ","").split(",")
  lines = [int(x) for x in lines]
  lines.sort()
  return lines

def parse_jump_lines(correct_jump):
  jumps = []
  correct_jump = correct_jump.split(",")
  for item in correct_jump:
    if not "->" in item:
      continue 
    lines = item.strip().split("->")
    lines = [eval(x) for x in lines]
    jumps.append(lines)
  return jumps

# true for correct, false for wrong
def judge_correct_execution(correct_jumps, actual_lines):
  if len(correct_jumps)==0:
    return True
  for jump in correct_jumps:
    if not jump[0] in actual_lines:
      return False
    if not jump[1] in actual_lines:
      return False
    if actual_lines.index(jump[0])+1 != actual_lines.index(jump[1]):
      return False
  return True

# return a list of jumps that it fails to meet
def find_wrong_execution(correct_jumps, actual_lines):
  unsat_jumps = []
  if len(correct_jumps)==0:
    return unsat_jumps
  for jump in correct_jumps:
    if not jump[0] in actual_lines:
      unsat_jumps.append(str(jump))
      continue
    if not jump[1] in actual_lines:
      unsat_jumps.append(str(jump))
      continue
    if actual_lines.index(jump[0])+1 != actual_lines.index(jump[1]):
      unsat_jumps.append(str(jump))
      continue
  return unsat_jumps


def jumps_fix_line(line_map, jumps, to_string=True):
  after_fix = []
  for jump in jumps:
    after_fix.append([line_map[x] for x in jump])
  if not to_string:
    return after_fix 
  jump_string = ""
  for jump in after_fix:
    jump_string += str(jump[0]) + "->" + str(jump[1]) + ", "
  return jump_string

def get_acc_bug_fix(result_group, result_groups, constraint_file, test_file):
  suggestions = set()
  for api, keyword in result_group["ml_keywords"]:
    # Improper if-condition - static checking
    if_condition = None
    if api in ["label_detection", "object_localization", "web_detection", "landmark_detection", "logo_detection", "classify_text"] and "[" in keyword:
      start = keyword.index("[")+1
      end = keyword.index("]")
      if_condition = keyword[start:end]
      if len(if_condition.strip())==0:
        continue
      if api in ["web_detection", "landmark_detection", "logo_detection"]:
        # suggest = "[[Improper if-condition - 1]] The if-condition [%s] used for API [%s]'s result may be problematic." %(if_condition, api)
        suggest = "* You may want to revise this branch predicate [%s]." %(if_condition)
        suggestions.add(suggest)
      if api in ["classify_text"]:
        in_label = label_suggestion.is_in_text_set(if_condition)
        if not in_label:
          suggest = "* You checked for label [%s] in this branch. However, [%s] is not a possible output of API [%s]." %(if_condition, if_condition, api)
          suggestions.add(suggest)
      elif api in ["label_detection", "object_localization"]:
        is_label = (api=="label_detection")
        # in_label = label_suggestion.is_in_label_set(if_condition, is_label=is_label)
        in_label, new_label = label_suggestion.is_in_label_set_suggestion(if_condition, is_label=is_label)
        if not in_label:
          suggest = "* You checked for label [%s] in this branch. However, [%s] is not a possible output of API [%s]." %(if_condition, if_condition, api)
          if not (new_label is None):
            suggest += " Do you mean [%s]?" % (new_label)
          suggestions.add(suggest)

    # Improper if-condition - infer from API result
    if api in ["label_detection", "object_localization", "classify_text"] and "[" in keyword:
      
      pos_files = get_pos_groups(result_group, api=api)
      neg_files = get_neg_groups(result_group, result_groups, api=api)
      # new_condition, acc = label_suggestion.label_suggestion_pos(metadata, metadata.keys(), min_coverage=ACCURACY_THRESHOLD, get_acc=True)
      if api in ["label_detection", "object_localization"]:
        pos_files = [x for x in pos_files if x in METADATA_IMG.keys()]
        neg_files = [x for x in neg_files if x in METADATA_IMG.keys()]
        new_condition, acc = label_suggestion.label_suggestion_pos_filter(if_condition, METADATA_IMG, pos_files, min_coverage=ACCURACY_THRESHOLD, get_acc=True)
        new_condition = new_condition[:MAX_CANDIDATE]
        cur_pass = label_suggestion.passed_files_pos(METADATA_IMG, pos_files, new_condition)
        acc =  len(cur_pass)/max(1, len(pos_files))
        false_positive = label_suggestion.passed_files_pos(METADATA_IMG, neg_files, new_condition)
      elif api in ["classify_text"] and "[" in keyword:
        pos_files = [x for x in pos_files if x in METADATA_TEXT.keys()]
        neg_files = [x for x in neg_files if x in METADATA_TEXT.keys()]
        new_condition, acc = label_suggestion.classify_text_suggestion(if_condition, METADATA_TEXT, pos_files, min_coverage=ACCURACY_THRESHOLD, get_acc=True)
        new_condition = new_condition[:MAX_CANDIDATE]
        cur_pass = label_suggestion.passed_files_pos(METADATA_TEXT, pos_files, new_condition)
        acc =  len(cur_pass)/max(1, len(pos_files))
        new_condition = ["\""+x+"\"" for x in new_condition]
        false_positive = label_suggestion.passed_files_pos(METADATA_TEXT, neg_files, new_condition)
      # new_condition = new_condition[:MAX_CANDIDATE]
      precision = acc*len(pos_files)/ max(1, (acc*len(pos_files)+len(false_positive)))
      old_recall, total = get_recall(result_group)
      old_recall /= max(1,total)
      old_precision, total = get_precision(result_group, result_groups)
      old_precision /= max(1,total)
      overall_correct = (acc*len(pos_files) + len(neg_files)-len(false_positive)) / (len(pos_files) + len(neg_files))
      correct_sum, total_sum = get_all_correct(result_groups)
      old_overall_correct = correct_sum / max(1,total_sum)
      # suggest = "[[Improper if-condition - 2]] The if-condition [%s] do not cover all possible result from API [%s]. A possible fix is using condition [%s] to cover %2.f%% cases (recall), which has %2.f%% precision." %(if_condition, api, " OR ".join(new_condition), acc*100, 100*precision)
      suggest = "* If you replace this branch condition with [%s], your program will agree with most human beings' judgement for %2.f%% of the test inputs, an improvement from %2.f%% of your original code." %(" OR ".join(new_condition), overall_correct*100, old_overall_correct*100)
      
      old_fscore = 2*old_recall*old_precision / max(1,(old_recall+old_precision))
      fscore = 2*acc*precision / max(1,(acc+precision))
      if acc > old_recall and fscore >= old_fscore:
        suggestions.add(suggest)      

    # Misinterpreted outputs
    # Another part is at check_log
    if api in ["analyze_sentiment"]:
      # suggest = "[[Misinterpreted outputs - 1]] API [%s] has two fields: score and magnitude. Both of them should be used to judge the text's sentiment." %(api)
      suggest = "* API [%s] has two fields: score and magnitude. Both of them should be used to judge the text's sentiment." %(api)
      suggestions.add(suggest)
  
  suggestions = list(suggestions)
  suggestions.sort()
  return '  \n'.join(suggestions)

def get_pos_groups(result_group, api=None):
  pos_files = set()
  for test in result_group["tests"]:
    file_name = test["API input"]
    pos_files.add(file_name)
    if api in ["label_detection", "object_localization"]:
      if not file_name in METADATA_IMG.keys():
        result = label_suggestion.get_image_info(file_name, api)
        if len(result)>0:
          METADATA_IMG[file_name] = label_suggestion.get_image_info(file_name, api)
    if api in ["classify_text"]:
      if not file_name in METADATA_TEXT.keys():
        result = label_suggestion.get_text_info(file_name, api)
        if len(result)>0:
          METADATA_TEXT[file_name] = result
  return pos_files

def get_neg_groups(result_group, result_groups, api=None):
  neg_files = set()
  correct = result_group["correct"]
  if len(correct) == 0:
    return neg_files
  for group2 in result_groups:
    if correct == group2["correct"]:
      continue
    for test2 in group2["tests"]:
      file_name = test2["API input"]
      neg_files.add(file_name)
      if api in ["label_detection", "object_localization"]:
        if not file_name in METADATA_IMG.keys():
          METADATA_IMG[file_name] = label_suggestion.get_image_info(file_name, api)
      if api in ["classify_text"]:
        if not file_name in METADATA_TEXT.keys():
          METADATA_TEXT[file_name] = label_suggestion.get_text_info(file_name, api)
  return neg_files

def get_precision(result_group, result_groups):
  correct = result_group["correct"]
  if len(correct) == 0:
    return 0, 0
  correct_jumps = parse_jump_lines(correct)
  precision = 0
  total_precision = 0
  for group2 in result_groups:
    for test2 in group2["tests"]:
      if not "actual" in test2.keys():
        continue
      actual_lines = parse_covered_lines(test2["actual"])
      unsat_jumps = find_wrong_execution(correct_jumps, actual_lines)
      if len(unsat_jumps)==0:
        total_precision += 1
        if (correct == group2["correct"]):
          precision += 1
  total_precision = max(1, total_precision)
  return precision, total_precision

def get_recall(result_group):
  correct = result_group["correct"]
  if len(correct) == 0:
    return 0,0
  correct_jumps = parse_jump_lines(correct)
  acc = 0
  total = 0.0
  for test in result_group["tests"]:
    if not "actual" in test.keys():
      continue
    actual_lines = parse_covered_lines(test["actual"])
    unsat_jumps = find_wrong_execution(correct_jumps, actual_lines)
    if len(unsat_jumps)==0:
      acc += 1
    total += 1
  return acc, total

def get_all_correct(result_groups):
  correct_sum = 0
  total_sum = 0
  for result_group in result_groups:
    acc, total = get_recall(result_group)
    correct_sum += acc
    total_sum += total
  return correct_sum, total_sum

def print_tuples_with_arrow(ml_keywords):
  result = ""
  for api, keyword in ml_keywords:
    result += str(api) + " -> " + str(keyword) + "; "
  return result

def print_ml_keyword(ml_keywords):
  result = []
  for api, keyword in ml_keywords:
    result.append(str(keyword))
  return " and ".join(result)

def check_log(constraint_file, test_file, log_file, param_list, line_map):
  bugs = []
  log_result = change_code.read_wholefile(log_file, preprocess=False)
  log_result = log_result.split("\n")
  
  result_groups = []
  for line in log_result:
    if len(line.strip()) == 0:
      continue
    if line.startswith("Expected branch jump:"):
      result_groups.append({"correct": line[len("Expected branch jump:"):].strip(), "tests": []})
    elif line.startswith("ML API keywords:"):
      result_groups[-1]["ml_keywords"] = eval(line[len("ML API keywords:"):].strip())
    elif line.startswith("[exact params]"):
      result_groups[-1]["tests"][-1]["params"] = line[len("[exact params]"):].strip()
    elif line.startswith(" >> covered lines:"):
      result_groups[-1]["tests"][-1]["actual"] = line[len(" >> covered lines:"):].strip()
    elif line.startswith("/"):
      result_groups[-1]["tests"].append({"API input": line[1:]})
  result_groups = [x for x in result_groups if len(x["tests"])>0]
  
  # crash bugs
  crash_bug = crash_bug_template()
  contain_success_execution = False
  for result_group in result_groups:
    for test in result_group["tests"]:
      if not "actual" in test.keys():
        test_input = {}
        values = eval(test["params"])
        for i, param in enumerate(param_list):
          test_input[param] = eval(values[i])
        crash_bug["test_input"].append(test_input)
        # each result_group only show several example
        if len(crash_bug["test_input"]) >= MAX_INPUT_EXAMPLE:
          break 
      else:
        contain_success_execution = True
  if not contain_success_execution:
    crash_bug["description"] = "Your program crashes on all test inputs. It probably contains syntax errors."
  if len(crash_bug["test_input"])>0:
    bugs.append(crash_bug)
  crash_bug = None
  
  #===========================================================================
  # accuracy bugs
  for result_group in result_groups:
    correct = result_group["correct"]
    all_unsat_jumps = Counter()
    wrong_tests = []
    if len(correct) == 0:
      continue
    correct_jumps = parse_jump_lines(correct)
    acc = 0
    total = 0.0
    max_unsat_jumps = 0
    for test in result_group["tests"]:
      if not "actual" in test.keys():
        continue
      actual_lines = parse_covered_lines(test["actual"])
      unsat_jumps = find_wrong_execution(correct_jumps, actual_lines)
      for jumps in unsat_jumps:
        all_unsat_jumps[jumps] += 1
      if len(unsat_jumps)==0:
        acc += 1
      else:
        if max_unsat_jumps < len(unsat_jumps):
          max_unsat_jumps = len(unsat_jumps)
        wrong_tests.append(test)
      total += 1
    if total <=0:
      continue

    # skip constraint="" case
    skip_flag = False
    if total == 1:
      for api, keyword in result_group["ml_keywords"]:
        if keyword in ["any type of image" , "audio without script", "any kind of text"]:
          skip_flag = True
          break
    if skip_flag:
      continue

    if acc/total < ACCURACY_THRESHOLD:
      acc_bug = accuracy_bug_template()
      acc_bug["lines_of_code"] = set()
      precision, total_precision = get_precision(result_group, result_groups)

      for key, value in all_unsat_jumps.most_common():
        if value > total * (1-ACCURACY_THRESHOLD) or len(acc_bug["lines_of_code"])==0:
          key = eval(key)
          acc_bug["lines_of_code"].add(key[0])
          acc_bug["lines_of_code"].add(key[1])
      acc_bug["lines_of_code"] = list(acc_bug["lines_of_code"])
      acc_bug["lines_of_code"].sort()
      
      jumps_after_fixed = jumps_fix_line(line_map, correct_jumps, to_string=True)
      # acc_bug["description"] = "There exists an accuracy bug. For a certain type of test inputs that expects path [%s], it fails %2.f%% cases (recall).\n" % (jumps_after_fixed , 100*(1-acc/total))
      # acc_bug["description"] += " And %2.f%% cases goes to this branch should go to other branches (precision)." % (100*(1-precision/total_precision))
      # acc_bug["description"] += " In this type of test inputs, we expect the ML input has the following property: " + print_tuples_with_arrow(result_group["ml_keywords"])
      acc_bug["description"] = "Your program suffers from accuracy problems: its judgement differs from most human beings for %2.f%% of the test inputs on line [%s]. For example, most people think these inputs are [%s], and yet your program does not." % (100*(1-acc/total), jumps_after_fixed, print_ml_keyword(result_group["ml_keywords"]))
      
      test_input = {}
      for wrong_test in wrong_tests[:MAX_INPUT_EXAMPLE]:
        values = eval(wrong_test["params"])
        test_input = {}
        for i, param in enumerate(param_list):
          test_input[param] = eval(values[i])
        acc_bug["test_input"].append(test_input)

      fix_suggestion = get_acc_bug_fix(result_group, result_groups, constraint_file, test_file)
      acc_bug["fix_suggestion"] = fix_suggestion

      bugs.append(acc_bug)
      acc_bug = None
  
  #===========================================================================
  # accuracy bugs - sentiment detection
  senti_groups = [None, None] #[pos, neg]
  for result_group in result_groups:
    correct = result_group["correct"]
    ml_keywords = result_group["ml_keywords"]
    if len(correct) > 0:
      continue
    sentiment_flag = False
    for api, keyword in ml_keywords:
      if api == "analyze_sentiment":
        sentiment_flag = True
        if keyword.startswith("positive text"):
          senti_groups[0] = result_group
        if keyword.startswith("negative text"):
          senti_groups[1] = result_group
        break
  if senti_groups[0]!= None and senti_groups[1]!=None:
    line_frequency = Counter()
    def group_tests(senti_group):
      behavior = {}
      for test in senti_group["tests"]:
        result = test["actual"]
        if not result in behavior.keys():
          behavior[result] = []
        behavior[result].append(test)
        for line in parse_covered_lines(result):
          line_frequency[line] += 1
      return behavior

    behavior = [group_tests(x) for x in senti_groups]
    line_frequency_max = max(line_frequency.values())
    all_keys = list(set(behavior[0].keys()).union(set(behavior[1])))
    all_keys.sort()
    senti_count = [[],[]]
    for i in range(2):
      for key in all_keys:
        if key in behavior[i].keys():
          senti_count[i].append(len(behavior[i][key]))
        else:
          senti_count[i].append(0)
    # print(senti_count)
    min_portion = sum(senti_count[0]) // len(senti_count[0])
    for i in range(len(senti_count[0])):
      if senti_count[0][i]>=min_portion and senti_count[1][i]>=min_portion:
        acc_bug = accuracy_bug_template()
        acc_bug["lines_of_code"] = []
        for line in parse_covered_lines(all_keys[i]):
          if line_frequency[line] < line_frequency_max:
            acc_bug["lines_of_code"].append(line)
        
        pos_text = [x["API input"] for x in behavior[0][all_keys[0]]]
        neg_text = [x["API input"] for x in behavior[1][all_keys[0]]]
        rule, accuracy = sentiment_suggestion.sentiment_classifier(pos_text, neg_text)
        # acc_bug["description"] = "There exists an accuracy bug. Both positive (%2.f%%) and negative (%2.f%%) text are classified to this branch.\n" % (100*senti_count[0][i]/sum(senti_count[0]), 100*senti_count[1][i]/sum(senti_count[1]))
        acc_bug["description"] = "Your program suffers from accuracy problems: it fails to differentiate text inputs with positive sentiment from those with negative sentiment on this line. %2.f%% of positive text inputs and %2.f%% of negative inputs get mixed together here." % (100*senti_count[0][i]/sum(senti_count[0]), 100*senti_count[1][i]/sum(senti_count[1]))
        # acc_bug["fix_suggestion"] = "[[Misinterpreted Outputs - 2]]. These positive text and negative text could be distinguished by [%s], which achieves %2.f%% accuracy." % (rule, accuracy*100)
        acc_bug["fix_suggestion"] = "* If you add [%s] inside this branch, your program will be able to better differentiate positive text from negative text --- only %2.f%% of the positive text will be mixed with negative text now, an improvement from %2.f%% in your original program." % (rule, (1-accuracy)*senti_count[0][i]*100/sum(senti_count[0]), senti_count[0][i]*100/sum(senti_count[0]))
        
        for j in range(2):
          if all_keys[i] in behavior[j].keys():
            tmp_number = max(MAX_INPUT_EXAMPLE//2, 1)
            for test_no in range(tmp_number):
              test_input = {}
              values = eval(behavior[j][all_keys[i]][test_no]['params'])
              for k, param in enumerate(param_list):
                test_input[param] = eval(values[k])
              acc_bug["test_input"].append(test_input)
        bugs.append(acc_bug)
        acc_bug = None

  #===========================================================================
  # coverage bugs
  covered = set()
  uncovered_lines = []
  codelines_our = change_code.read_wholefile(test_file, preprocess=False).split("\n")
  for result_group in result_groups:
    for test in result_group["tests"]:
      if not "actual" in test.keys():
        continue
      actual_lines = parse_covered_lines(test["actual"])
      covered.update(actual_lines)
  for j in range(len(codelines_our)):
    if "if __name__ == '__main__':" in codelines_our[j] or "if __name__ == \"__main__\":" in codelines_our[j]:
      break
    if not (j+1) in covered:
      tmp = codelines_our[j].strip().replace("}","").replace("]","").replace(")","")
      if tmp.startswith("import ") or tmp.startswith("from ") or tmp.startswith("sys.path.append")  or tmp.startswith("@PythonFuzz") or tmp.startswith("def ") or tmp.startswith("#") or tmp.startswith("\"\"\"") or tmp.startswith("global") or len(tmp)==0 or codelines_our[j].strip()==codelines_our[j].rstrip():
        continue
      if tmp.strip().replace(" ", "").replace("\t", "") == "else:":
        continue
      if tmp.strip() == "continue":
        continue
      uncovered_lines.append(j+1)

  if len(uncovered_lines) > 0:
    coverage_bug = coverage_bug_template()
    coverage_bug["lines_of_code"] = uncovered_lines
    # provide some examples
    for result_group in result_groups:
      if len(result_group["tests"])>0:
        test = result_group["tests"][-1]
        test_input = {}
        values = eval(test["params"])
        for i, param in enumerate(param_list):
          test_input[param] = eval(values[i])
        coverage_bug["test_input"].append(test_input)
        if len(coverage_bug["test_input"]) >= MAX_INPUT_EXAMPLE:
          break 

    bugs.append(coverage_bug)
    coverage_bug = None
  return bugs


def locate_functions(input_file):
  def compute_size(node):
    min_lineno = node.lineno
    max_lineno = node.lineno
    for node in ast.walk(node):
      if hasattr(node, "lineno"):
          min_lineno = min(min_lineno, node.lineno)
          max_lineno = max(max_lineno, node.lineno)
    return (min_lineno, max_lineno)

  func_to_line = {}
  with open(input_file) as file:
    tree = ast.parse(file.read())
    for item in ast.walk(tree):
      if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
          start, end = compute_size(item)
          func_to_line[item.name] = (start, end)

  # for key, value in func_to_line.items():
  #   print(str(key) + "  " + str(value))
  return func_to_line

def retrieve_function(func_to_line, line_no):
  func = None
  def_line = 1
  for key, value in func_to_line.items():
      if value[0] <= line_no <= value[1]:
        if value[0] >= def_line: # function defined in function
          func = key
          def_line = value[0]
  return func, def_line


def restructure_json(bugs):
  crash_bugs = {"bug_type": "Crash",
                "bugs": []}
  acc_bugs = {"bug_type": "Accuracy",
                "bugs": []}
  cov_bugs = {"bug_type": "Dead Code",
                "bugs": []}
  for bug in bugs:
    if bug["bug_type"] == "Crash":
      del bug["bug_type"]
      crash_bugs["bugs"].append(bug)
    elif bug["bug_type"] == "Accuracy":
      del bug["bug_type"]
      acc_bugs["bugs"].append(bug)
    elif bug["bug_type"] == "Dead Code":
      del bug["bug_type"]
      cov_bugs["bugs"].append(bug)

  return [crash_bugs, acc_bugs, cov_bugs]


# map code of lines to their original numbers considering empty lines
# traced in `empty_line.json`
def change_code_lines(curr_lines_of_code, curr_func_def_line, ori_func_def_line, ori_empty_lines):
    to_remove = []
    for entry in ori_empty_lines:
        if entry < ori_func_def_line:
            to_remove.append(entry)
    for entry in to_remove:
        ori_empty_lines.remove(entry)

    if ori_empty_lines == []:
        return [i - curr_func_def_line + ori_func_def_line for i in curr_lines_of_code]

    # change_dict stores the following information:
    # from which line -> needs to append how many new lines
    change_dict = {}
    total_empty_lines = 0
    i = 0
    while i < len(ori_empty_lines):
        if i == 0:
            curr_pos = ori_empty_lines[i] - ori_func_def_line
            total_empty_lines += 1
        # still an empty line
        elif ori_empty_lines[i] == ori_empty_lines[i - 1] + 1:
            total_empty_lines += 1
        # no longer an empty line
        else:
            change_dict[curr_pos] = total_empty_lines
            curr_pos = ori_empty_lines[i] - total_empty_lines - ori_func_def_line
            total_empty_lines += 1
        i += 1
    change_dict[curr_pos] = total_empty_lines
    logger.debug(f"change_dict computed to be {change_dict}")

    res = []
    for i in curr_lines_of_code:
        diff = i - curr_func_def_line
        upper_j = -1
        for j in change_dict:
            if diff >= j and j > upper_j:
                upper_j = j
        if upper_j == -1:
            res.append(i - curr_func_def_line + ori_func_def_line)
        else:
            res.append(i - curr_func_def_line + ori_func_def_line + change_dict[upper_j])
    return res

def rreplace(s, old, new, occurrence):
  li = s.rsplit(old, occurrence)
  return new.join(li)

def change_description(text, curr_func_def_line, ori_func_def_line, ori_empty_lines):
  p_1 = re.compile('\d+->\d+')
  p_2 = re.compile('\d+')
  res = text

  for entry in p_1.findall(text):
    print(entry)
    numbers = p_2.findall(entry)
    print(numbers)
    numbers = map(lambda x: int(x), numbers)
    changes = change_code_lines(numbers, curr_func_def_line, ori_func_def_line, ori_empty_lines)
    print(changes)
    res = rreplace(res, entry, f"{changes[0]}->{changes[1]}", 1)
  return res

# all code lines are start with 1
def apply_test(file_name, function_name, output_file=None):
  if not os.path.exists(file_name):
    print("[Error] " + file_name + " not found.")
  file_name = os.path.abspath(file_name)

  test_file_dir = os.path.dirname(os.path.realpath(file_name))
  constraint_file = os.path.join(test_file_dir, "__constraint_solving.py")
  change_code.change(file_name, constraint_file, function_name) # comment for test only

  test_file = os.path.join(test_file_dir, "__our_tool.py")
  info_file = os.path.join(test_file_dir, INFO_FILE)
  func_params, param_list, line_map = generate_test_file(file_name, info_file, test_file, function_name)

  log_file = os.path.join(test_file_dir, "__generated_test.txt")
  # or use solve_precondition_full.py instead of solve_multi.py
  if not PYTHON_OHTER:
    cmd = "python3.8 solve_multi.py --m=25 --start=" +function_name+ " -o " +log_file+ " -t " +test_file+ " -f \"" +func_params+ "\" " + constraint_file
  else:
    cmd = "python3.6 solve_multi.py --m=25 --start=" +function_name+ " -o " +log_file+ " -t " +test_file+ " -f \"" +func_params+ "\" " + constraint_file
  run_command(cmd) # comment for test only

  
  if output_file == None:
    output_file = os.path.join(test_file_dir, "output.json")
  bugs = check_log(constraint_file, test_file, log_file, param_list, line_map)

  func_to_line = locate_functions(file_name)
  for i in range(len(bugs)):
    bugs[i]["code_file"] = file_name
    bugs[i]["lines_of_code"] = [line_map[x] for x in bugs[i]["lines_of_code"] if x in line_map.keys()]

    if bugs[i]["bug_type"] == "Crash": # use the main entrance
      bugs[i]["function_name"] = function_name
      bugs[i]["func_def_line"] = func_to_line[function_name][0]

    if bugs[i]["bug_type"] == "Accuracy": # use the function with smallest line_no
      line_no = bugs[i]["lines_of_code"][0]
      func_name, func_def_line = retrieve_function(func_to_line, line_no)
      bugs[i]["function_name"] = func_name
      bugs[i]["func_def_line"] = func_def_line

    if bugs[i]["bug_type"] == "Dead Code": # split coverage bug for each function
      line_to_func = {}
      for line_no in bugs[i]["lines_of_code"]:
        func_name, func_def_line = retrieve_function(func_to_line, line_no)
        if not func_name in line_to_func.keys():
          line_to_func[func_name] = []
        line_to_func[func_name].append(line_no)
      if len(line_to_func.keys()) == 1:
        bugs[i]["function_name"] = func_name
        bugs[i]["func_def_line"] = func_to_line[func_name][0]
      elif len(line_to_func.keys()) > 1: 
        splited_bugs = []
        for key, value in line_to_func.items():
          new_bug = bugs[i].copy()
          new_bug["function_name"] = key
          new_bug["func_def_line"] = func_to_line[key][0]
          new_bug["lines_of_code"] = value
          splited_bugs.append(new_bug)
        bugs[i] = splited_bugs[0]
        for i in range(1,len(splited_bugs)):
          bugs.append(splited_bugs[i])

  # re-map functions to their original location
  f3_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), "code_extraction", "function_mapping.json")
  f4_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), "code_extraction", "empty_line.json")

  # it could occur that no function mapping is stored (?)
  # if it exists, then update relevant fields in `new_bug`
  if os.path.exists(f3_filename):
    logger.info(f"found function mapping at {f3_filename}, processing")
    with open(f3_filename, "r") as f3:
      func_mapping_dict = json.load(f3)
    with open(f4_filename, "r") as f4:
      empty_line_dict = json.load(f4)

    for i in range(len(bugs)):
      curr_func_name = bugs[i]["function_name"]
      curr_func_def_line = bugs[i]["func_def_line"]
      query_key = f"{curr_func_name},{curr_func_def_line}"

      # again, it could occur that this information is not
      # present in the json dictionary (?)
      # so only process if present
      if query_key in func_mapping_dict:
        logger.info(f"found {query_key} in func_mapping_dict json file, changing relevant parameters in bug output")
        ori_file_name = func_mapping_dict[query_key][0]
        ori_func_def_line = func_mapping_dict[query_key][1]

        bugs[i]["func_def_line"] = ori_func_def_line
        bugs[i]["code_file"] = ori_file_name
        
        if ori_file_name in empty_line_dict:
          logger.info(f"changing lines_of_code from {bugs[i]['lines_of_code']}")
          # bugs[i]["lines_of_code"] = [x - curr_func_def_line + ori_func_def_line for x in bugs[i]["lines_of_code"]]
          ori_lines_of_code = bugs[i]["lines_of_code"]
          bugs[i]["lines_of_code"] = change_code_lines(ori_lines_of_code, curr_func_def_line, ori_func_def_line, empty_line_dict[ori_file_name])
          logger.info(f"to {bugs[i]['lines_of_code']}")
          bugs[i]["description"] = change_description(bugs[i]["description"], curr_func_def_line, ori_func_def_line, empty_line_dict[ori_file_name])
        # note that the function name is already taken care of in extract.py
      else:
        logger.warning(f"query_key {query_key} does not exist in function mapping json file. This indicates that the functions processed by all_wrap_up.py were not properly processed by extract.py")
        
      if bugs[i]["lines_of_code"] == []:
        bugs[i]["lines_of_code"] = [bugs[i]["func_def_line"]]
    
    # removes the file because we'd have to use the same filename
    os.remove(f3_filename)
      
  
  bugs = restructure_json(bugs)

  with open(output_file, "w") as f:
    f.write(json.dumps(bugs, sort_keys=False, indent=4))


def from_plugin_json(json_file_path, output_path, log_file_path):
  """
    Wraps all processing from plugin-outputed json file
  """
  logging.basicConfig(level=logging.DEBUG, filename=log_file_path, filemode="w")
  logging.getLogger("parso.python.diff").disabled = True
  logging.getLogger().addHandler(logging.StreamHandler())

  e = Extractor(json_file_path)

  # These are a bunch of files that could have been generated from multiple testing
  log_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "testing_logs")
  if not os.path.isdir(log_folder):
    os.makedirs(log_folder)
  extracted_file_path = os.path.join(log_folder, "extracted_function.py")
  
  potential_files = ["__constraint_solving.py", "__cov_test.py", "__generated_test_modified.txt", "__generated_test_origin_code.txt", "__generated_test.txt", "__our_tool.py"]
  if Path(extracted_file_path).is_file():
    logger.info(f"Found extracted_function.py file at {extracted_file_path}, deleting...")
    os.remove(extracted_file_path)
  for potential_file in potential_files:
    potential_file_path = os.path.join(log_folder, potential_file)
    if Path(potential_file_path).is_file():
      logger.info(f"Found file to be deleted at {potential_file_path}, deleting...")
      os.remove(potential_file_path)

  e.extract(extracted_file_path, True)
  apply_test(extracted_file_path, e.json_data["func_name"], output_file=output_path)


def main():
  parser=argparse.ArgumentParser(description="schema")
  # arguments for file
  parser.add_argument("--input_json", help="plugin input json file", type=str, required=True)
  parser.add_argument("--output_json", help="tool output json file for plugin", type=str, required=True)
  parser.add_argument("--log_file", help="log file output for plugin", type=str, required=True)

  args=parser.parse_args()
  from_plugin_json(args.input_json, args.output_json, args.log_file)



if __name__ == '__main__':
  main()
