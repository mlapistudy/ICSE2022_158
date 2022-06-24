import os
import sys
import logging
import traceback
import operator
from optparse import OptionParser
import math
import subprocess


from symbolic.loader import *
from symbolic.explore import ExplorationEngine

from global_vars import *
import reverse_API.vision as vision_reverse
import reverse_API.speech as speech_reverse
import reverse_API.language as language_reverse
import label_suggestion as label_suggestion

logger = logging.getLogger(__name__)

def get_ml_api(filename):
  used_ml_api = []
  ml_api_to_input = []
  output_to_ml_api = {}
  If_statement_changes = {}
  with open(filename, 'r', encoding='utf8') as file_obj:
    text = file_obj.read()
  for line in text.split("\n")[::-1]:
    if line.startswith("# used_ml_api:"):
      used_ml_api = line.replace("# used_ml_api:","").strip().split(", ")
    if line.startswith("# ml_api_to_input:"):
      ml_api_to_input = eval(line.replace("# ml_api_to_input:","").strip())
    if line.startswith("# output_to_ml_api:"):
      output_to_ml_api = eval(line.replace("# output_to_ml_api:","").strip())
    if line.startswith("# If_statement_changes:"):
      If_statement_changes = eval(line.replace("# If_statement_changes:","").strip())
    
  return used_ml_api, ml_api_to_input, output_to_ml_api, If_statement_changes

def find_default_value(fields, var):
  while "___" in var:
    var = var.replace("___","__")
  tmp = var.split("__")[-1]
  for tuples in fields:
    field, value = tuples
    if value == "\"\"":
      value = ""
    if tmp == field:
      return value
  return 0

def get_fields_name(fields):
  field_names = []
  for tuples in fields:
    field, value = tuples
    field_names.append(field)
  return field_names

def find_value_in_solution(outputs, param):
  for output in outputs:
    name, value = output
    if name == param:
      return value
  return None

# TODO: support score
def get_search_keyword(outputs, api_set, output_to_ml_api):
  labels = {}
  scores = {}
  for output in outputs:
    name, value = output
    if not name in output_to_ml_api.keys():
      continue
    if not output_to_ml_api[name] in api_set:
      continue
    if output_to_ml_api[name] == "face_detection" or output_to_ml_api[name] == "text_detection":
      continue
    if name.endswith("__description"):
      if not value == find_default_value(API_Fields["label_detection"], name):
        labels[name.replace("__description","")] = value
    if name.endswith("__name"):
      if not value == find_default_value(API_Fields["object_localization"], name):
        labels[name.replace("__name","")] = value
    if name.endswith("__score"):
      if not value == find_default_value(API_Fields["label_detection"], name):
        scores[name.replace("__score","")] = value
  if "face_detection" in api_set:
    face_label = parse_face(outputs)
    if len(face_label)>0:
      labels["face_label_from_api"] = face_label

  if len(labels)==0:
    return ""

  search_keyword = ""
  for var in labels.keys():
    label = labels[var]
    if label in scores.keys():
      score = scores[var]
      if score < 0.5:
        continue
    if len(search_keyword)>0 and len(label)>0:
      if not label in search_keyword:
        search_keyword += " " + label
    else:
      search_keyword = label
  return search_keyword


def find_text(outputs, output_to_ml_api):
  fields = API_Fields["text_detection"]

  text = ""
  for output in outputs:
    name, value = output
    if not name in output_to_ml_api.keys():
      continue
    if not output_to_ml_api[name] == "text_detection":
      continue
    if name.endswith("___description"):
      if len(value.strip()) > 0:
        text += value.strip() + " "
  return text.strip()

# TODO: work on multiple faces
def parse_face(outputs):
  fields = API_Fields["face_detection"]
  field_names = get_fields_name(fields)
  faces = {}

  for output in outputs:
    name, value = output
    for i in range(len(field_names)):
      field = field_names[i]
      if "likelihood" in field and name.endswith("__"+field):
        var_name = name.replace("__"+field,"")
        if not var_name in faces.keys():
          faces[var_name] = [None, None, None, None] #anger, joy, surprise, sorrow
        faces[var_name][i] = value
  if len(faces)==0:
    return ""

  files = []
  for var in faces.keys():
    face = faces[var]
    # normailize to 1,2,3,4
    minimum = find_min_list(face)
    if minimum == None:
      continue

    face2 = [minimum-1 if i==None else i for i in face]
    indexs = norm_list(face2)
    anger_index, joy_index, surprise_index, sorrow_index = indexs
    highest_index = indexs.index(max(indexs))
    if anger_index<=2 and joy_index<=2 and surprise_index<=2 and sorrow_index<=2:
      return "serious human face"
    if highest_index == 0:
      return "angry human face"
    if highest_index == 1:
      return "joyful human face"
    if highest_index == 2:
      return "surprise human face"
    else:
      return "sad human face"
  return ""

# TODO: support score
def solve_vision_keyword(outputs, fields, desc_name, score_name):
  labels = {}
  scores = {}
  mid_name = "__mid"
  for output in outputs:
    name, value = output
    if name.endswith(desc_name):
      if not value == find_default_value(fields, name):
        labels[name.replace(desc_name,"")] = value
    if name.endswith(score_name):
      if not value == find_default_value(fields, name):
        scores[name.replace(score_name,"")] = value
    if name.endswith(mid_name):
      if not value == find_default_value(fields, name):
        label_to_mid, mid_to_label = label_suggestion.get_label_list(is_label=True)
        if value in mid_to_label.keys():
          labels[name.replace(mid_name,"")] = mid_to_label[value]
  if len(labels)==0:
    return ""

  search_keyword = ""
  for var in labels.keys():
    label = labels[var]
    if label in scores.keys():
      score = scores[var]
      if score < 0.5:
        continue
    if len(search_keyword)>0 and len(label)>0:
      if not label in search_keyword:
        search_keyword += " " + label
    else:
      search_keyword = label
  return search_keyword

def solve_label(outputs, find_keyword=False):
  search_keyword = solve_vision_keyword(outputs, API_Fields["label_detection"], "__description", "__score")
  if find_keyword:
    if len(search_keyword) > 0:
      return ("label_detection", "image of [" + str(search_keyword)+"]")
    else:
      return ("label_detection", "any type of image")
  if LOCAL_TEST:
    return [search_keyword]
  files = vision_reverse.image_classification(search_keyword, max_num=OUTPUT_PRE_SOLUTION)
  return files

def solve_object(outputs, find_keyword=False):
  search_keyword = solve_vision_keyword(outputs, API_Fields["object_localization"], "__name", "__score")
  if find_keyword:
    if len(search_keyword) > 0:
      return ("object_localization", "image of [" + str(search_keyword)+"]")
    else:
      return ("object_localization", "any type of image")
  if LOCAL_TEST:
    return [search_keyword]
  files = vision_reverse.image_classification(search_keyword, max_num=OUTPUT_PRE_SOLUTION)
  return files

def solve_landmark(outputs, find_keyword=False):
  search_keyword = solve_vision_keyword(outputs, API_Fields["landmark_detection"], "__description", "__score")
  if find_keyword:
    if len(search_keyword) > 0:
      return ("landmark_detection", "image of [" + str(search_keyword)+"]")
    else:
      return ("landmark_detection", "any type of image")
  if LOCAL_TEST:
    return [search_keyword]
  files = vision_reverse.image_classification(search_keyword, max_num=OUTPUT_PRE_SOLUTION)
  return files

def solve_web(outputs, find_keyword=False):
  search_keyword = solve_vision_keyword(outputs, API_Fields["web_detection"], "__description", "__score")
  if find_keyword:
    if len(search_keyword) > 0:
      return ("web_detection", "image of [" + str(search_keyword)+"]")
    else:
      return ("web_detection", "any type of image")
  if LOCAL_TEST:
    return [search_keyword]
  files = vision_reverse.image_classification(search_keyword, max_num=OUTPUT_PRE_SOLUTION)
  return files

def solve_text_detection(outputs, find_keyword=False):
  fields = API_Fields["text_detection"]

  text = ""
  break_flag = [False, False, False, False] # space, line break, hyphen, sure space
  type_flag = True
  cares_type = False
  for output in outputs:
    name, value = output
    if name.endswith("__description") or name.endswith("__text"):
      if len(value) > 0:
        text += value + " "
    if (name.endswith("__SPACE")) and value==True:
      break_flag[0] = True
    if name.endswith("__LINE_BREAK") and value==True:
      break_flag[1] = True
    if name.endswith("__HYPHEN") and value==True:
      break_flag[2] = True
    if (name.endswith("__SURE_SPACE") or name.endswith("__EOL_SURE_SPACE")) and value==True:
      break_flag[3] = True
    if name.endswith("__type"):
      type_flag = value
      cares_type = True
  text = text[:-1].strip()
  if cares_type:
    if not type_flag:
      break_flag = list(map(operator.not_, break_flag))
    if break_flag[0]:
      text += " "
    if break_flag[1]:
      text += "\n"
    if break_flag[2]:
      text += "-"
    if break_flag[3]:
      text += "      "
    # make sure space and newline will be detected
    if len(text) > 0:
      if text.startswith(" ") or text.startswith("\n"):
        text = "@" + text
      if text.endswith(" ") or text.endswith("\n"):
        text = text + "@"
  
  if find_keyword:
    return ("text_detection","image with text [" +text+ "]")
  if LOCAL_TEST:
    return [text]
  files = vision_reverse.text_detection(text, max_num=OUTPUT_PRE_SOLUTION_TEXT)
  return files


# find min, ignore None
def find_min_list(list):
  minimum = None
  for a in list:
    if a == None:
      continue
    if minimum == None:
      minimum = a
    else:
      minimum = min(minimum, a)
  return minimum

# turn list to 1234, while remaing > < relationship
def norm_list(list):
  list2 = [0] * len(list)
  for i in range(len(list)):
    for j in range(len(list)):
      if list[i] >= list[j]:
        list2[i] += 1
  return list2

# TODO: support face location, multiple faces
# currently, we only care about the relative relationship of feelings
def solve_face(outputs, find_keyword=False):
  fields = API_Fields["face_detection"]
  field_names = get_fields_name(fields)
  faces = {}

  for output in outputs:
    name, value = output
    for i in range(len(field_names)):
      field = field_names[i]
      if "likelihood" in field and name.endswith("__"+field):
        var_name = name.replace("__"+field,"")
        if not var_name in faces.keys():
          faces[var_name] = [None, None, None, None] #anger, joy, surprise, sorrow
        faces[var_name][i] = value

  if len(faces)==0:
    # empty file
    if find_keyword:
      return ("face_detection","blank image")
    files = vision_reverse.image_classification("")
    return files

  files = []
  for var in faces.keys():
    face = faces[var]
    # normailize to 1,2,3,4
    minimum = find_min_list(face)
    if minimum == None:
      files = vision_reverse.image_classification("")
      continue
    face2 = [minimum-1 if i==None else i for i in face]
    face2 = norm_list(face2)
    for i in range(len(face2)):
      if face[i] == None:
        face2[i] = "UNKNOWN"
      elif face2[i] <= 1:
        face2[i] = "VERY_UNLIKELY"
      elif face2[i] == 2:
        face2[i] = "UNLIKELY"
      elif face2[i] == 3:
        face2[i] = "POSSIBLE"
      elif face2[i] == 4:
        face2[i] = "VERY_LIKELY"
      else:
        face2[i] = "UNKNOWN"
    if find_keyword:
      return ("face_detection","image with [" +vision_reverse.face_detection_face_type(tuple(face2))+ "]")
    if LOCAL_TEST:
      return [str(face2)]
    f_file = vision_reverse.face_detection(tuple(face2), max_num=OUTPUT_PRE_SOLUTION)
    if type(f_file) is list:
      files = files + f_file
    else:
      files.append(f_file)

  return files


def solve_stt(outputs, find_keyword=False):
  fields = API_Fields["recognize"]

  transcript = ""
  for output in outputs:
    name, value = output
    if name.endswith("__transcript"):
      # if default value, then it has no constraint
      if len(value.strip()) == 0:
        continue
      else:
        transcript += value.strip() + ". "
  transcript = transcript[:-2]
  if find_keyword:
    if len(transcript)==0:
      return ("recognize","audio with script ["+str(transcript)+"]")
    else:
      return ("recognize","audio without script")
  if LOCAL_TEST or (not GENERATE_AUDIO):
    return [transcript]
  if len(transcript)==0:
    files = speech_reverse.empty_audio()
    return files
  files = speech_reverse.speech_to_text(transcript)
  return files


def round_up(n, decimals=0): 
  multiplier = 10 ** decimals 
  return math.ceil(n * multiplier) / multiplier
def round_down(n, decimals=0): 
  multiplier = 10 ** decimals 
  return math.floor(n * multiplier) / multiplier

def solve_sentiment(outputs, find_keyword=False):
  fields = API_Fields["analyze_sentiment"]
  magnitudes = {}
  scores = {}
  for output in outputs:
    name, value = output
    if name.endswith("__magnitude"):
      if not value == find_default_value(fields, name):
        magnitudes[name.replace("__magnitude","")] = value
    if name.endswith("__score"):
      scores[name.replace("__score","")] = value
  if len(scores)==0 and len(magnitudes)==0:
    if find_keyword:
      return ("analyze_entities", "any kind of text")
    files = ["Nothing."]
    return files
  files = []
  for var in (scores.keys() | magnitudes.keys()):
    # set default value
    score = 0
    magnitude = -1
    special_flag = False
    if var in scores.keys():
      score = round(scores[var], 3)
      # if score > 1 or score < -1:
      #   continue
      if score > 0.9: #some settings are infeasible
        score = 0.9
      if score < -0.9:
        score = -0.9
      # adhoc fix (due to sentiment140 limit)
      if score>0.7 and score<0.8:
        score = 0.8
      elif score<-0.7 and score>-0.8:
        score = -0.8
    if var in magnitudes.keys():
      if magnitude>=0:
        magnitude = round(magnitudes[var], 3)
      else: #probably score*mag
        # special_flag = True
        pass # close this feature
    if find_keyword:
      if magnitude < 0:
        magnitude = "any"
      return ("analyze_sentiment","text of [score="+str(score)+",magnitudes="+str(magnitude)+"]")
    if LOCAL_TEST:
      return [str([score, magnitude])]

    if special_flag: #probably score*mag, e.g. Language/Tone
      text = language_reverse.analyze_sentiment_score(score, max_num=OUTPUT_PRE_SOLUTION)
    else:
      text = language_reverse.analyze_sentiment(score, magnitude, max_num=OUTPUT_PRE_SOLUTION)
    if type(text) is list:
      files = files + text
    else:
      files.append(text)
  return files

Potential_entity_types = ['UNKNOWN', 'PERSON', 'LOCATION', 'ORGANIZATION', 'EVENT', 'WORK_OF_ART', 'CONSUMER_GOOD', 'OTHER', 'PHONE_NUMBER', 'ADDRESS', 'DATE', 'NUMBER', 'PRICE']
def solve_entity(outputs, find_keyword=False):
  global Potential_entity_types
  fields = API_Fields["analyze_entities"]
  names = {}
  types = {}
  for output in outputs:
    name, value = output
    if name.endswith("__name") and isinstance(value, str):
      if value in Entity_Types: # type.name
        types[name.replace("__name","")] = value
      elif len(value)>0: # entity.name
        names[name.replace("__name","")] = value
    if name.endswith("__type"):
      if not value == find_default_value(fields, name):
        if isinstance(value, int): 
          value = Entity_Types[value]
        types[name.replace("__type","")] = value
  if len(names)==0 and len(types)==0:
    if find_keyword:
      return ("analyze_entities", "any kind of text")
    files = ["Nothing."]
    return files
  files = []
  for var in (names.keys() | types.keys()):
    # set default value
    entity_name = None
    entity_type = None
    if var in names.keys():
      entity_name = names[var]
    if var in types.keys():
      entity_type = types[var]
      Potential_entity_types = [x for x in Potential_entity_types if not entity_type==x]
    if find_keyword:
      return ("analyze_entities","text containing entity ["+str([entity_name, entity_type])+"]")
    if LOCAL_TEST:
      return [str([entity_name, entity_type])]
    new_files = language_reverse.analyze_entities(entity_type, name=entity_name, max_num=OUTPUT_PRE_SOLUTION)
    files += new_files
  files = [x.replace("\t"," ").replace("\n"," ").replace("\r"," ") for x in files]
  return files

def solve_entity_sentiment(outputs, find_keyword=False):
  return solve_entity(outputs, find_keyword)

Potential_syntax_types = Syntax_Types.copy()
def solve_analyze_syntax(outputs, find_keyword=False):
  global Potential_syntax_types
  fields = API_Fields["analyze_syntax"]
  types = {}
  for output in outputs:
    name, value = output
    if name.endswith("__tag"):
      if not value == find_default_value(fields, name):
        if isinstance(value, int): 
          value = Syntax_Types[value]
        types[name.replace("__tag","")] = value
  if len(types)==0:
    if find_keyword:
      return ("analyze_syntax", "any kind of text")
    files = ["Nothing."]
    return files
  files = []
  for var in types.keys():
    syntax_type = types[var]
    Potential_syntax_types = [x for x in Potential_syntax_types if not syntax_type==x]
    if find_keyword:
      return ("analyze_syntax", "text containing syntax ["+str(syntax_type)+"]")
    if LOCAL_TEST:
      return [syntax_type]
    new_files = language_reverse.analyze_syntax(syntax_type, max_num=OUTPUT_PRE_SOLUTION)
    files += new_files
  files = [x.replace("\t"," ").replace("\n"," ").replace("\r"," ") for x in files]
  return files

Potential_text_types = ["art", "beauty", "business", "computer", "finance", "food", "game", "pet"]
def solve_text_classify(outputs, find_keyword=False):
  global Potential_text_types
  fields = API_Fields["classify_text"]
  labels = {}
  scores = {}
  for output in outputs:
    name, value = output
    if name.endswith("__name"):
      if not value == find_default_value(fields, name):
        labels[name.replace("__name","")] = value
    if name.endswith("__score"):
      if not value == find_default_value(fields, name):
        scores[name.replace("__confidence","")] = value
  if len(labels)==0:
    if find_keyword:
      return ("classify_text", "any kind of text")
    return language_reverse.classify_text("", max_num=OUTPUT_PRE_SOLUTION)

  search_keyword = ""
  files = []
  for var in labels.keys():
    label = labels[var]
    if label in scores.keys():
      score = scores[var]
      if score < 0.5:
        continue
    if len(label) == 0:
      if find_keyword:
        return ("classify_text", "any kind of text")
      files += language_reverse.classify_text("", max_num=OUTPUT_PRE_SOLUTION)
    else:
      if find_keyword:
        return ("classify_text", "text of ["+str(label)+"]")
      if LOCAL_TEST:
        return [label]
      Potential_text_types = [x for x in Potential_text_types if not label.lower() in x]
      new_files = language_reverse.classify_text(label, max_num=OUTPUT_PRE_SOLUTION)
      files += new_files
  files = [x.replace("\t"," ").replace("\n"," ").replace("\r"," ") for x in files]
  return files

# group ml api with same inputs
def group_ml_api(ml_api_to_input):
  input_to_api = {}
  for item in ml_api_to_input:
    api, var = item
    if not var in input_to_api.keys():
      input_to_api[var] = []
    input_to_api[var].append(api)
  return input_to_api.values()

def get_extra_info(file_path, keyword):
  result = []
  with open(file_path, 'r', encoding='utf8') as f:
    lines = f.readlines()
  Flag = False
  for line in lines:
    if line.startswith(">>>"):
      Flag = line.startswith(">>> ["+keyword+"]")
    elif Flag:
      result.append(line[:-1]) # remove '\n'
  if len(result)==0:
    return None
  return result

def read_wholefile(filename):
  with open(filename, 'r', encoding='utf8') as file_obj:
    text = file_obj.read()
  return text

def extract_indent(line):
  indent_pos = len(line) - len(line.lstrip())
  indent = line[:indent_pos]
  return indent

# for If_statement_changes
def search_value_to_key(dictionary, target_value):
  if not target_value in dictionary.values():
    return None
  for key, value in dictionary.items():
    if value == target_value:
      if key in dictionary.values():
        if key == dictionary[key]:
          return key
        return search_value_to_key(dictionary, key)
      else:
        return key

def print_dict_with_arrow(dictionary):
  result = "Expected branch jump: "
  for key, value in dictionary.items():
    result += str(key) + "->" + str(value) + ", "
  return result


def read_coverage(cur_dir):
  f2 = open(cur_dir+"/tmp", 'r', encoding='utf8')
  lines = f2.readlines()
  f2.close()
  run_command("rm "+cur_dir+"/tmp")
  for line in reversed(lines):
    if line.strip().startswith(">>"):
      start = line.index("{")
      end = line.index("}")+1
      return eval(line[start:end])
  return set()

def run_command(command):
  proc = subprocess.Popen(command, shell=True)
  proc.wait()

if __name__ == '__main__':
  # logger.info("PyExZ3 (Python Exploration with Z3)")

  sys.path = [os.path.abspath(os.path.join(os.path.dirname(__file__)))] + sys.path

  usage = "usage: %prog [options] <path to a *.py file>"
  parser = OptionParser(usage=usage)

  parser.add_option("-l", "--log", dest="logfile", action="store", help="Save log output to a file", default="")
  parser.add_option("-s", "--start", dest="entry", action="store", help="Specify entry point", default="")
  parser.add_option("-m", "--max-iters", dest="max_iters", type="int", help="Run specified number of iterations", default=0)
  parser.add_option("-o", "--output-file", dest="output_file", type="string", help="Place where save generated files", default=0)
  parser.add_option("-t", "--test-file", dest="test_file", type="string", help="File for running python fuzz", default=0)
  parser.add_option("-f", "--func-params", dest="func_params", type="string", help="If the tested function contains multiple inputs, specify them. E.g. func(buf, a) -> 'API_input a'", default="")

  (options, args) = parser.parse_args()

  if not (options.logfile == ""):
    logging.basicConfig(filename=options.logfile,level=logging.DEBUG)
    logging.getLogger().addHandler(logging.StreamHandler())
  else:
    logging.basicConfig(level=logging.DEBUG)


  if len(args) == 0 or not os.path.exists(args[0]):
    parser.error("Missing app to execute")
    sys.exit(1)

  solver = "cvc"

  filename = os.path.abspath(args[0])
  

  # Get the object describing the application
  app = loaderFactory(filename,options.entry)
  if app == None:
    sys.exit(1)

  logger.info ("Exploring " + app.getFile() + "." + app.getEntry())
  used_ml_api, ml_api_to_input, output_to_ml_api, If_statement_changes = get_ml_api(filename)
  logger.info(f"Testing API {used_ml_api}")

  result = None
  all_inputs = set()
  all_inputs_list = []

  try:
    engine = ExplorationEngine(app.createInvocation(), solver=solver, print_info=False)
    generatedInputs, returnVals, path = engine.explore(options.max_iters)

    if OUTPUT_PRE_SOLUTION * len(generatedInputs) > TOTAL_LIMIT:
      OUTPUT_PRE_SOLUTION = max(2, TOTAL_LIMIT // len(generatedInputs))
    
    # ==================================================
    # find covered path of each generatedInputs
    Solution_2_Path = []
    
    test_file_dir = os.path.dirname(os.path.realpath(filename))
    cov_test_filename = os.path.join(test_file_dir, "__cov_test.py")
    python_fuzz_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    # import_fix_code = get_extra_info(os.path.join(test_file_dir, INFO_FILE), "import fix")
    import_fix_code = f'import os, sys\nsys.path.append("{python_fuzz_path}")'
    base_code_file = read_wholefile(filename).split("\n")
    for no, code in enumerate(base_code_file):
      if code.startswith("@symbolic"):
        base_code_file[no] = "@PythonFuzz"
      if "from symbolic.args import *" in code:
        base_code_file[no] = "from fuzztool.pythonfuzz.main import PythonFuzz"
      if code.strip().replace("  ", " ").startswith("def "+options.entry):
        base_code_file[no] = "def " + options.entry + "(buf):"

    for i in range(len(generatedInputs)):
      with open(cov_test_filename, 'w') as f:
        # f.write('\n'.join(import_fix_code)+'\n')
        f.write(import_fix_code+'\n')
        for no, code in enumerate(base_code_file):
          if code.strip().startswith("#"):
            continue
          f.write(code+'\n')
          if code.strip().replace("  ", " ").startswith("def "+options.entry):
            no2 = no+1 # no+1 usually is an empty line
            while len(base_code_file[no2].strip())==0 and no2+1<len(base_code_file):
              no2 += 1
            indent = extract_indent(base_code_file[no2])
            for name, value in generatedInputs[i]:
              if isinstance(value, str):
                value = "\"" + value + "\""
              f.write(indent + str(name) +" = "+ str(value) +'\n')
        f.write(options.entry+"()\n")
      
      if not PYTHON_OHTER:
        command = "python3.8 "+ cov_test_filename +" --rss-limit-mb=20480 --timeout=60 --runs=1 --loc_file="+ cov_test_filename
      else:
        command = "python3.6 "+ cov_test_filename +" --rss-limit-mb=20480 --timeout=60 --runs=1 --loc_file="+ cov_test_filename
      run_command(command +" > "+test_file_dir+"/tmp")
      covered_lines = read_coverage(test_file_dir)
      Solution_2_Path.append(covered_lines)
      

    if not options.test_file:
      sys.exit(0)
    # find which lines are related to if statement in cov_test_filename, map them to the lines in test_file
    # python fuzz count lines from 1, so add one line before to fix
    base_code_file = [""] + read_wholefile(cov_test_filename).split("\n")
    test_code_file = [""] + read_wholefile(options.test_file).split("\n")
    Branches = {} # base_code_file -> test_code_file
    for no, code in enumerate(base_code_file):
      if "if __name__ == '__main__':" in code or "if __name__ == \"__main__\":" in code:
        break
      tmp = code.strip().replace("}","").replace("]","").replace(")","")
      if len(tmp) == 0:
        continue
      if tmp.startswith("if ") or tmp.startswith("elif ") or tmp.startswith("for ") or tmp.startswith("while "):        
        origin_code = search_value_to_key(If_statement_changes, code)
        if origin_code:
          # because we removed this substring when reading the file in change_code.py
          for no_test, code_test in enumerate(test_code_file):
            if code_test.replace(".lower()","") == origin_code:
              Branches[no] = no_test
              break
          # if origin_code in test_code_file:
          #   # Branches.append([no, code, test_code_file.index(origin_code), origin_code])
          #   Branches[no] =  test_code_file.index(origin_code)
    
    def parse_statement_to_branch(Branches, covered_lines, base_code_file, test_code_file):
      covered_lines = list(covered_lines)
      covered_lines.sort()
      should_cover_branch = {} # if_line_no -> branch_line_no
      for i, line_no in enumerate(covered_lines):
        if line_no in Branches.keys():
          if_line_no = Branches[line_no]
          branch_line_no = None
          if i+1 >= len(covered_lines):
            continue
          next_line_no = covered_lines[i+1]
          jump_flag = False

          for j in range(line_no+1, next_line_no):
            if len(base_code_file[j].strip())>0:
              jump_flag = True
          for j in range(if_line_no+1, len(test_code_file)):
            tmp_line = test_code_file[j].strip()
            if len(tmp_line) > 0:
              if (not tmp_line.replace(" ","").replace("\t","")=="else:"):
                branch_line_no = j
                break
              else:
                jump_flag = True
                break
          if jump_flag:
            expect_indent = extract_indent(test_code_file[if_line_no])
            for j in range(branch_line_no+1, len(test_code_file)):
              branch_line_no = None
              actual_indent = extract_indent(test_code_file[j])
              if expect_indent >= actual_indent:
                branch_line_no = j
                if test_code_file[j].replace(" ","").replace("\t","")=="else:":
                  for kk in range(j+1, len(test_code_file)):
                    if len(test_code_file[kk])>0:
                      branch_line_no = kk
                      break
                break
              if test_code_file[j].strip().startswith("def "):
                branch_line_no = None
                break
          should_cover_branch[if_line_no] = branch_line_no
      return should_cover_branch


    # for i in range(len(Solution_2_Path)):
    #   logger.info(Solution_2_Path[i])
    #   logger.info(Branches)
    #   result = parse_statement_to_branch(Branches, Solution_2_Path[i], base_code_file, test_code_file)
    #   logger.info(result)
    #   logger.info("===========")
    # sys.exit(0)
    Solution_2_ML_keywords = []
  
    # ==================================================
    # generate API inputs
    for i in range(len(generatedInputs)):
      logger.info(str(generatedInputs[i]) + "\t-->\t" + str(returnVals[i]))

      files = []
      if len(used_ml_api) == 1:
        if used_ml_api[0] == "label_detection":
          files = solve_label(generatedInputs[i])
          Solution_2_ML_keywords.append([solve_label(generatedInputs[i], find_keyword=True)])
        elif used_ml_api[0] == "face_detection":
          files = solve_face(generatedInputs[i])
          Solution_2_ML_keywords.append([solve_face(generatedInputs[i], find_keyword=True)])
        elif used_ml_api[0] == "text_detection" or used_ml_api[0] == "document_text_detection":
          files = solve_text_detection(generatedInputs[i])
          Solution_2_ML_keywords.append([solve_text_detection(generatedInputs[i], find_keyword=True)])
        elif used_ml_api[0] == "web_detection":
          files = solve_web(generatedInputs[i])
          Solution_2_ML_keywords.append([solve_web(generatedInputs[i], find_keyword=True)])
        elif used_ml_api[0] == "object_localization":
          files = solve_object(generatedInputs[i])
          Solution_2_ML_keywords.append([solve_object(generatedInputs[i], find_keyword=True)])
        elif used_ml_api[0] == "recognize":
          files = solve_stt(generatedInputs[i])
          Solution_2_ML_keywords.append([solve_stt(generatedInputs[i], find_keyword=True)])
        elif used_ml_api[0] == "analyze_sentiment":
          files = solve_sentiment(generatedInputs[i])
          Solution_2_ML_keywords.append([solve_sentiment(generatedInputs[i], find_keyword=True)])
        elif used_ml_api[0] == "classify_text":
          files = solve_text_classify(generatedInputs[i])
          Solution_2_ML_keywords.append([solve_text_classify(generatedInputs[i], find_keyword=True)])
        elif used_ml_api[0] == "analyze_entities":
          files = solve_entity(generatedInputs[i])
          Solution_2_ML_keywords.append([solve_entity(generatedInputs[i], find_keyword=True)])
        elif used_ml_api[0] == "analyze_entity_sentiment":
          files = solve_entity_sentiment(generatedInputs[i])
          Solution_2_ML_keywords.append([solve_entity_sentiment(generatedInputs[i], find_keyword=True)])
        elif used_ml_api[0] == "analyze_syntax":
          files = solve_analyze_syntax(generatedInputs[i])
          Solution_2_ML_keywords.append([solve_analyze_syntax(generatedInputs[i], find_keyword=True)])
        else:
          logger.info("API reverse not supported: " + used_ml_api[0])
          sys.exit(1)
      else:
        used_vision_api = []
        used_language_api = []
        used_speech_api = []
        for api in used_ml_api:
          if api in Vision_API:
            used_vision_api.append(api)
          elif api in Language_API:
            used_language_api.append(api)
          elif api in Speech_API:
            used_speech_api.append(api)
          else:
            logger.info("API reverse not supported: " + api)
            sys.exit(1)

        # only vision
        if len(used_language_api)==0 and len(used_speech_api)==0:
          files_group = []
          file_num = OUTPUT_PRE_SOLUTION
          files = set()
          ML_keywords = []
          for api_set in group_ml_api(ml_api_to_input):
            if not "text_detection" in api_set and not "document_text_detection" in api_set:
              search_keyword = get_search_keyword(generatedInputs[i], api_set, output_to_ml_api)
              if LOCAL_TEST:
                files_part = [search_keyword] # test only
              else:
                files_part = vision_reverse.image_classification(search_keyword, max_num=OUTPUT_PRE_SOLUTION)
              ML_keywords.append(("Vision APIs"), ("image of [" + str(search_keyword)+"]"))
            else:
              if "text_detection" in api_set:
                api_set.remove("text_detection")
              if "document_text_detection" in api_set:
                api_set.remove("document_text_detection")
              text = find_text(generatedInputs[i], output_to_ml_api)
              search_keyword = get_search_keyword(generatedInputs[i], api_set, output_to_ml_api)
              files_part = []
              if LOCAL_TEST:
                files_part1 = [search_keyword] # test only
              else:
                files_part1 = vision_reverse.image_classification(search_keyword, max_num=OUTPUT_PRE_SOLUTION)
              for background in files_part1:
                if LOCAL_TEST:
                  new_file = text + " " + background
                else:
                  new_file = vision_reverse.text_detection_background(text, background=background)
                files_part.append(new_file)
              ML_keywords.append(("Vision APIs", "image of [" + str(search_keyword)+"]"))
              ML_keywords.append(("text_detection", "image with text [" + str(text)+"]"))
            if len(files_part) < OUTPUT_PRE_SOLUTION:
              files_part += [files_part[-1]] * (OUTPUT_PRE_SOLUTION - len(files_part))
            files_group.append(files_part)
          # logger.info(files_group)
          for k in range(OUTPUT_PRE_SOLUTION):
            tmp_group = []
            for j in range(len(files_group)):
              tmp_group += files_group[j][k]
            files.add("|\t|".join(tmp_group))
          files = list(files)
          # logger.info(files)
          Solution_2_ML_keywords.append(ML_keywords)
        
        elif len(used_vision_api)==0 and len(used_speech_api)==0:
          files_group = []
          file_num = OUTPUT_PRE_SOLUTION
          files = set()
          ML_keywords = []
          for api_set in group_ml_api(ml_api_to_input):
            files_part2 = [""] * OUTPUT_PRE_SOLUTION
            for api in api_set:
              if api == "analyze_sentiment":
                files_part = solve_sentiment(generatedInputs[i])
                ML_keywords.append(solve_sentiment(generatedInputs[i], find_keyword=True))
              elif api == "classify_text":
                files_part = solve_text_classify(generatedInputs[i])
                ML_keywords.append(solve_text_classify(generatedInputs[i], find_keyword=True))
              elif api == "analyze_entities":
                files_part = solve_entity(generatedInputs[i])
                ML_keywords.append(solve_entity(generatedInputs[i], find_keyword=True))
              elif api == "analyze_entity_sentiment":
                files_part = solve_entity_sentiment(generatedInputs[i])
                ML_keywords.append(solve_entity_sentiment(generatedInputs[i], find_keyword=True))
              else:
                logger.info("API reverse not supported: " + api)
                continue
              if len(files_part) < OUTPUT_PRE_SOLUTION:
                files_part += [files_part[-1]] * (OUTPUT_PRE_SOLUTION - len(files_part))
              for k in range(OUTPUT_PRE_SOLUTION):
                files_part2[k] += files_part[k]
            files_group.append(files_part2)
          for k in range(OUTPUT_PRE_SOLUTION):
            tmp_group = []
            for j in range(len(files_group)):
              tmp_group.append(files_group[j][k])
            files.add("|\t|".join(tmp_group))
          files = list(files)
          Solution_2_ML_keywords.append(ML_keywords)
        else:
          logger.info("API reverse not supported: " + str(used_ml_api))
          sys.exit(1)
      logger.info("=======================\n\n")
      all_inputs.add('|\n|'.join(files))
      all_inputs_list.append('|\n|'.join(files))

    
    if options.func_params and len(used_ml_api)>1:
      logger.info("--func-params currently is not supported for multiple API calls.")
      sys.exit(1)
    
    # ==================================================
    # Parse --func_params 
    if options.func_params:
      test_func_inputs = options.func_params.split()
      values = {}
      for param in test_func_inputs:
        if param == "API_input":
          continue
        values[param] = []
        for i in range(len(generatedInputs)):
          val = find_value_in_solution(generatedInputs[i], param)
          if isinstance(val, str):
            val = "\"" + val.replace("!","\\!") + "\""
          else:
            val = str(val)
          values[param].append(val)
    
    # ==================================================
    # sentiment detection only
    if "analyze_sentiment" in used_ml_api:
      grouped_api = group_ml_api(ml_api_to_input)
      if len(grouped_api) == 1:
        pos_sentences = language_reverse.analyze_sentiment_without_hard_limit(is_positive=True, max_num=OUTPUT_PRE_SOLUTION)
        Solution_2_ML_keywords.append([('analyze_sentiment', 'positive text from Sentiment140')])
        Solution_2_Path.append("")
        all_inputs.add('|\n|'.join(pos_sentences))
        all_inputs_list.append('|\n|'.join(pos_sentences))

        neg_sentences = language_reverse.analyze_sentiment_without_hard_limit(is_positive=False, max_num=OUTPUT_PRE_SOLUTION)
        Solution_2_ML_keywords.append([('analyze_sentiment', 'negative text from Sentiment140')])
        Solution_2_Path.append("")
        all_inputs.add('|\n|'.join(neg_sentences))
        all_inputs_list.append('|\n|'.join(neg_sentences))
      else:
        # do not support multiple files
        pass 


    # ==================================================
    
    # no result or has result : one-api
    if len(used_ml_api) == 1:
      if used_ml_api[0] in Vision_API:
        all_inputs.add(vision_reverse.no_label()[0])
        if used_ml_api[0] in Vision_keyword.keys():
          if LOCAL_TEST:
            extra_files = [Vision_keyword[used_ml_api[0]]]
          else:
            extra_files = vision_reverse.image_classification(Vision_keyword[used_ml_api[0]], max_num=1)
          all_inputs.add('|\n|'.join(extra_files))
        elif used_ml_api[0] == "text_detection" or used_ml_api[0] == "document_text_detection":
          extra_files = vision_reverse.text_detection("A test string\n\tfor\tdetection.", max_num=1)
          all_inputs.add('|\n|'.join(extra_files))

      elif used_ml_api[0] in Language_API:
        if used_ml_api[0] == "classify_text":
          if len(Potential_text_types) == 0:
            extra_files = language_reverse.classify_text("", max_num=OUTPUT_PRE_SOLUTION)
          else:
            if LOCAL_TEST:
              extra_files = [Potential_text_types[0]]
            else:
              extra_files = language_reverse.classify_text(Potential_text_types[0], max_num=OUTPUT_PRE_SOLUTION)
            extra_files = [x.replace("\t"," ").replace("\n"," ").replace("\r"," ") for x in extra_files]
        elif used_ml_api[0] == "analyze_entities" or used_ml_api[0] == "analyze_entity_sentiment":
          if len(Potential_entity_types) > 0:
            if LOCAL_TEST:
              extra_files = [Potential_entity_types[-1]]
            else:
              extra_files = language_reverse.analyze_entities(Potential_entity_types[-1], max_num=OUTPUT_PRE_SOLUTION)
            extra_files = [x.replace("\t"," ").replace("\n"," ").replace("\r"," ") for x in extra_files]
        elif used_ml_api[0] == "analyze_syntax":
          if len(Potential_syntax_types) > 0:
            if LOCAL_TEST:
              extra_files = [Potential_syntax_types[-1]]
            else:
              extra_files = language_reverse.analyze_syntax(Potential_syntax_types[-1], max_num=OUTPUT_PRE_SOLUTION)
            extra_files = [x.replace("\t"," ").replace("\n"," ").replace("\r"," ") for x in extra_files]
        else:
          extra_files = []
          pass
        all_inputs.add('|\n|'.join(extra_files))
        all_inputs.add('|\n|'.join([""]))
      elif used_ml_api in Speech_API:
        all_inputs.add('|\n|'.join([""]))
        all_inputs.add('|\n|'.join(["See you next time.", "Come with me.", "Come on!", "Yes"]))

    # no result or has result : multi-apis
    grouped_api = group_ml_api(ml_api_to_input)
    if len(used_ml_api)>1:
      if len(used_language_api)==0 and len(used_speech_api)==0:
        all_inputs.add("|\t|".join(vision_reverse.no_label()*len(grouped_api) ))
        files_group = []
        for api_set in grouped_api:
          files_part = []
          for api in api_set:
            if api in Vision_keyword.keys():
              if LOCAL_TEST:
                files_part += [Vision_keyword[api]]
              else:
                files_part += vision_reverse.image_classification(Vision_keyword[api], max_num=1)
            elif "text_detection" in used_ml_api or "document_text_detection" in "text_detection":
              files_part += vision_reverse.text_detection("A test string\n\tfor\tdetection.", max_num=1)
          if len(files_part)==0:
            files_part = vision_reverse.no_label()
          files_group.append(files_part)
        extra_files = set()
        for i in range( min(len(x) for x in files_group) ):
          tmp_group = []
          for j in range(len(files_group)):
            tmp_group.append(files_group[j][i])
          extra_files.add("|\t|".join(tmp_group))
        all_inputs.add('|\n|'.join(extra_files))

      elif len(used_vision_api)==0 and len(used_speech_api)==0:
        all_inputs.add("|\t|".join([""]*len(grouped_api) ))
        files_group = []
        for api_set in grouped_api:
          files_part = []
          for api in api_set:
            if api== "classify_text":
              if len(Potential_text_types) == 0:
                files_part += language_reverse.classify_text("", max_num=OUTPUT_PRE_SOLUTION)
              else:
                if LOCAL_TEST:
                  files_part += [Potential_text_types[0]]
                else:
                  files_part += language_reverse.classify_text(Potential_text_types[0], max_num=1)
            elif "analyze_entities" in used_ml_api  or "analyze_entity_sentiment" in used_ml_api:
              if len(Potential_entity_types) > 0:
                if LOCAL_TEST:
                  files_part += [Potential_entity_types[-1]]
                else:
                  files_part += language_reverse.analyze_entities(Potential_entity_types[-1], max_num=OUTPUT_PRE_SOLUTION)
            elif used_ml_api == "analyze_syntax":
              if len(Potential_syntax_types) > 0:
                if LOCAL_TEST:
                  files_part += [Potential_syntax_types[-1]]
                else:
                  files_part += language_reverse.analyze_syntax(Potential_syntax_types[-1], max_num=OUTPUT_PRE_SOLUTION)
          files_part = [x.replace("\t"," ").replace("\n"," ").replace("\r"," ") for x in files_part]
          if len(files_part)==0:
            files_part = [""]
          files_group.append(files_part)
        extra_files = set()
        for i in range( min(len(x) for x in files_group) ):
          tmp_group = []
          for j in range(len(files_group)):
            tmp_group.append(files_group[j][i])
          extra_files.add("|\t|".join(tmp_group))
        all_inputs.add('|\n|'.join(extra_files))

    if LOCAL_TEST:
      for i in all_inputs:
        logger.info("["+i+"]")


    def record_coverage(cur_dir):
      tmp_file = os.path.join(cur_dir,"tmp")
      f2 = open(tmp_file, 'r', encoding='utf8')
      lines = f2.readlines()
      f2.close()
      for line in reversed(lines):
        if line.strip().startswith(">>"):
          if not line.endswith("\n"):
            line = line + "\n"
          f.write(line)
          break
      run_command("rm " + tmp_file)

    tested = set()
    if options.output_file and options.test_file and (not LOCAL_TEST):
      output_file = os.path.abspath(options.output_file)
      logger.info("Output file: " + output_file)
      f = open(output_file, 'w', encoding='utf8')
      for item in all_inputs:
        logger.info("Working ... ")
        if item in all_inputs_list:
          item_no = all_inputs_list.index(item)
          result = parse_statement_to_branch(Branches, Solution_2_Path[item_no], base_code_file, test_code_file)
          f.write(print_dict_with_arrow(result)+'\n')
          f.write("ML API keywords:\t"+ str(Solution_2_ML_keywords[item_no])+'\n\n')
        else:
          f.write(print_dict_with_arrow({})+'\n')
          f.write("ML API keywords:\t"+ str([])+'\n\n')
        for generated_files in item.split('|\n|'):
          if generated_files in tested:
            # f.write(">>> tested:" +str(generated_files) + "\n")
            continue
          tested.add(generated_files)
          try:
            if len(generated_files.split('|\t|')) == 1:
              generated_file = generated_files.strip()
              f.write("/"+generated_file+"\n")
              test_file = os.path.abspath(options.test_file)
              cur_dir = os.path.dirname(os.path.realpath(__file__))
              if set(used_ml_api).issubset(Vision_API) or (set(used_ml_api).issubset(Speech_API) and GENERATE_AUDIO):
                generated_file = os.path.abspath(generated_file)
              generated_file = generated_file.replace('"', '\\"').replace("!","\\!")
              if not PYTHON_OHTER:
                command = "python3.8 "+ test_file +" --rss-limit-mb=20480 --timeout=60 --runs=1 --loc_file="+ test_file
              else:
                command = "python3.6 "+ test_file +" --rss-limit-mb=20480 --timeout=60 --runs=1 --loc_file="+ test_file
              if options.func_params:
                if item in all_inputs_list:
                  matched = 0
                  for item_no in range(len(all_inputs_list)):
                    if all_inputs_list[item_no] == item:
                      matched = item_no
                      break
                  command1 = ""
                  exact_params = []
                  for param in test_func_inputs:
                    if param == "API_input":
                      command1 += " \"" + generated_file + "\""
                      exact_params.append("\""+generated_file+"\"")
                    else:
                      command1 += " " + values[param][matched]
                      exact_params.append(values[param][matched])
                  f.write("[exact params] " +str(exact_params)+ "\n")
                  run_command(command + command1 +" > "+cur_dir+"/tmp")
                  record_coverage(cur_dir)
                else:
                  for k in range(len(generatedInputs)):
                    command1 = ""
                    exact_params = []
                    for param in test_func_inputs:
                      if param == "API_input":
                        command1 += " \"" + generated_file + "\""
                        exact_params.append("\""+generated_file+"\"")
                      else:
                        command1 += " " + values[param][k]
                        exact_params.append(values[param][k])
                    f.write("[exact params] " +str(exact_params)+ "\n")
                    run_command(command + command1 +" > "+cur_dir+"/tmp")
                  record_coverage(cur_dir)
              else: 
                run_command(command + " \"" + generated_file + "\" > "+cur_dir+"/tmp")
                record_coverage(cur_dir)
            else:
              logger.info("Do not support multiple files")
              sys.exit(1)
          except:
            pass
        f.write("\n=======================\n\n")
      f.close()
      run_command("rm crash-*")
      run_command("rm timeout-*")


  except ImportError as e:
    # createInvocation can raise this
    logging.error(e)
    sys.exit(1)

  if result == None or result == True:
    sys.exit(0);
  else:
    sys.exit(1);  
