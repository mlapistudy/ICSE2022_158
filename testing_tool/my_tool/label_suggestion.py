import io, os
import json
from collections import defaultdict
import requests
from bs4 import BeautifulSoup
import random

from google.cloud import vision
from google.cloud import language

from global_vars import *



dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "reverse_API")
LABEL_SRC = os.path.join(dir_path, "vision_src/class_descriptions.csv")
OBJECT_SRC = os.path.join(dir_path, "vision_src/object_descriptions.csv")
MAP_SRC = os.path.join(dir_path, "vision_src/mid2datawiki.csv")
TEXT_CLASS_SRC = os.path.join(dir_path, "language_src/category_list.txt")



#===========================================
# deal with vision API
#===========================================
def get_image_info(file_name, api):
  image_info = []
  client = vision.ImageAnnotatorClient()
  with io.open(file_name, 'rb') as image_file:
    content = image_file.read()
  try:
    if VISION_V1:
      image = vision.types.Image(content=content)
    else:
      image = vision.Image(content=content)
    if api == "label_detection":
      response = client.label_detection(image=image)
      for label in response.label_annotations:
        info = {"description": label.description, "score": label.score, "mid": label.mid}
        image_info.append(info)
    elif api == "object_localization":
      response = client.object_localization(image=image)
      for object in response.localized_object_annotations:
        info = {"description": object.name, "score": object.score, "mid": object.mid}
        image_info.append(info)
  except:
    pass
  return image_info

def get_label(file_name):
  image_info = {"file":os.path.split(file_name)[-1], "labels":[]}
  client = vision.ImageAnnotatorClient()
  with io.open(file_name, 'rb') as image_file:
    content = image_file.read()
  try:
    if VISION_V1:
      image = vision.types.Image(content=content)
    else:
      image = vision.Image(content=content)
    response = client.label_detection(image=image)
    labels = response.label_annotations
    for label in labels:
      info = {"description": label.description, "score": label.score, "mid": label.mid}
      image_info["labels"].append(info)
  except:
    pass
  return image_info

# turn list to dict
def load_labels(folder, metadata_file):
  with open(metadata_file, 'r', encoding='utf8') as file_obj:
    json_data = file_obj.read()
  metadata = json.loads(json_data)
  metadata2 = {}
  files = []
  for image in metadata:
    filename = os.path.join(folder, image["file"])
    files.append(filename)
    
    # filter
    new_labels = []
    for label in image["labels"]:
      if label["description"]=="Font":
        continue
      if label["description"]=="Rectangle" or label["description"]=="Circle" or label["description"]=="Pattern" or label["description"]=="Event" or label["description"]=="Pink" or label["description"]=="Grey":# test only
        continue
      new_labels.append(label)

    metadata2[filename] = new_labels#image["labels"]
  return metadata2, files

#===========================================
# deal with language API
#===========================================
def get_text_info(text, api):
  text_info = []
  client = language.LanguageServiceClient()
  document = language.types.Document(content=text, type=language.enums.Document.Type.PLAIN_TEXT)
  if api == "classify_text":
    try:
      response = client.classify_text(document)
      for category in response.categories:
        info = {"description": category.name, "score": category.confidence}
        text_info.append(info)
    except:
      pass
  return text_info

#===========================================
# Knowledge graph related
#===========================================

# is_label=True: label detection
# is_label=False: object detection
def get_label_list(is_label=True):
  label_to_mid = {}
  mid_to_label = {}
  if is_label:
    f = open(LABEL_SRC,'r')
  else:
    f = open(OBJECT_SRC,'r')
  for line in f.readlines():
    label = line.replace("\n","").split(",")
    if len(label) == 2:
      label[1] = label[1].lower()
      mid_to_label[label[0]] = label[1]
      label_to_mid[label[1]] = label[0]
  f.close()
  return label_to_mid, mid_to_label

def get_mid2datawiki():
  wiki_to_mid = {}
  mid_to_wiki = {}
  f = open(MAP_SRC,'r')
  for line in f.readlines():
    label = line.replace("\n","").split(",")
    if len(label) == 2:
      mid_to_wiki[label[0]] = label[1]
      wiki_to_mid[label[1]] = label[0]
  f.close()
  return wiki_to_mid, mid_to_wiki

# return wiki data id
def search_wikidata(wiki_id, label_to_mid, mid_to_wiki):
  from wikidata.client import Client
  client = Client()
  entity = client.get(wiki_id, load=True)
  # for key, value in entity.__dict__.items():
  #   print(key, value)
  related_items = set()
  claims = entity.data["claims"]
  for key, value in claims.items():
    for item in value:
      try:
        # print(item ["mainsnak"]["datavalue"])
        item = item["mainsnak"]["datavalue"]["value"]
        if isinstance(item, dict):
          item = item["id"]
          related_items.add(item)
        elif isinstance(item, str):
          item = item.lower()
          if not item in label_to_mid.keys():
            continue
          mid = label_to_mid[item]
          if not mid in mid_to_wiki.keys():
            continue
          related_items.add(mid_to_wiki[mid])
      except:
        pass
  return related_items

# return a wiki id of a string name
# always return the first item on the search list, may not correct
def search_wikidata_id_from_name(item_name):
  url = "https://www.wikidata.org/w/index.php?search="+str(item_name)
  A = ("Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36",
        )
  Agent = A[random.randrange(len(A))]
  headers = {'user-agent': Agent}
  r = requests.get(url, headers=headers)
  soup = BeautifulSoup(r.text, 'lxml')
  for item in soup.find_all("div", class_="mw-search-result-heading"):
    print(item)
    links = item.findAll('a')
    for a in links:
      if a['href'].startswith("/wiki/Q"):
        wiki_id = a['href'][len("/wiki/"):]
        return wiki_id
  return None
    

    # <div class="mw-search-result-heading"><a href="/wiki/Q39908" title="‎trousers‎ | ‎clothing for the legs and lower body‎" data-serp-pos="0"><span class="wb-itemlink"><span class="wb-itemlink-label" lang="en" dir="ltr">trousers</span> <span class="wb-itemlink-id">(Q39908)</span></span></a>   : <span class="wb-itemlink-description"><span class="searchmatch">pants</span></span> </div>
  # return wiki_id

# is_label=True: label detection, False: object detection
def is_in_label_set(keyword, is_label=True):
  label_to_mid, mid_to_label = get_label_list(is_label)
  keyword = keyword.lower()
  return keyword in label_to_mid.keys()

# use knowledge graph to find synonyms
def infer_label_from_synonym(keyword, is_label=True, depth=1):
  label_to_mid, mid_to_label = get_label_list(is_label)
  wiki_to_mid, mid_to_wiki = get_mid2datawiki()

  keyword = keyword.lower()
  wiki_id = None
  if keyword in label_to_mid.keys():
    mid = label_to_mid[keyword]
    if mid in mid_to_wiki.keys():
      wiki_id = mid_to_wiki[mid]
  if wiki_id is None:
    wiki_id = search_wikidata_id_from_name(keyword)
  if wiki_id is None:
    return None

  related_items = search_wikidata(wiki_id, label_to_mid, mid_to_wiki)
  
  tmp_set = related_items
  for i in range(1,depth):
    extra_set = set()
    for item in tmp_set:
      tmp_set2 = search_wikidata(item, label_to_mid, mid_to_wiki)
      for element in tmp_set2:
        if not element in related_items:
          extra_set.add(element)
    related_items.update(extra_set)
    tmp_set = extra_set

  related_items2 = set() # translate to labels
  related_items2.add(keyword)
  for item in related_items:
    if not item in wiki_to_mid.keys():
      continue
    mid = wiki_to_mid[item]
    if not mid in mid_to_label.keys():
      continue
    related_items2.add(mid_to_label[mid])
  if keyword in related_items2:
    related_items2.remove(keyword)
  return list(related_items2)



#===========================================
# deal with label suggestion
#===========================================

# check how many files would be passed with label filter
# metadata: data loads from "metadata.json", containing info of files
# test_files: images to be tested
# filter_labels: a set of labels for filtering images, with OR relationship
# max_label: how many label result from label_detection API are considered
# return: passed files
def passed_files_pos(metadata, test_files, filter_labels, max_label=10):
  passed = []
  for file in test_files:
    for i, label in enumerate(metadata[file]):
      if i >= max_label:
        break
      if label["description"] in filter_labels:
        passed.append(file)
        break
  return passed

# metadata: data loads from "metadata.json", containing info of files
# test_files: images to be tested
# filter_labels_pos: a set of labels for filtering images, with OR relationship
# filter_labels_neg: a set of labels for filtering images, with AND relationship
# max_label: how many label result from label_detection API are considered
# return: passed files
def passed_files(metadata, test_files, filter_labels_pos, filter_labels_neg, max_label):
  for label in filter_labels_pos:
    if label in filter_labels_neg:
      print("[Error] 'passed_files' requires no intersection between filter_labels_pos and filter_labels_neg.")
      return []

  passed = []
  for file in test_files:
    for i, label in enumerate(metadata[file]):
      if i >= max_label:
        break
      if label["description"] in filter_labels_pos:
        passed.append(file)
        break
      if label["description"] in filter_labels_neg:
        break
  return passed

# count occurance of labels
def count_occurance(metadata, files, max_label):
  occurance = defaultdict(int)
  for file in files:
    if not file in metadata.keys():
      # metadata[file] = get_label(image)
      print("[Error] Missing metadata of "+file)
      continue
    for i, label in enumerate(metadata[file]):
      if i >= max_label:
        break
      occurance[label["description"]] += 1
  return occurance


# generate label suggestion based on positive examples
# metadata: data loads from "metadata.json", containing info of pos_files
# pos_files: images that expected to be passed
# min_coverage: at least how many pos_files will be covered
# max_label: how many label result from label_detection API are considered
# return: a set of labels for filtering pos_files, with OR relationship

def label_suggestion_pos(metadata, pos_files, min_coverage=0.9, max_label=10, get_acc=False):
  pos_files = [x for x in pos_files if x in metadata.keys()]
  occurance = count_occurance(metadata, pos_files, max_label)

  sorted_keys = sorted(occurance, key=occurance.get)[::-1]
  suggested_labels = sorted_keys[:1]
  cur_pass = passed_files_pos(metadata, pos_files, suggested_labels, max_label)
  while len(suggested_labels) < len(sorted_keys) and len(cur_pass)<min_coverage*len(pos_files):
    max_increase = 0
    next_key = None
    for key in sorted_keys:
      if key in suggested_labels:
        continue
      tmp_set = suggested_labels.copy()
      tmp_set.append(key)
      new_pass = passed_files_pos(metadata, pos_files, tmp_set, max_label)
      if len(new_pass)-len(cur_pass) > max_increase:
        max_increase = len(new_pass)-len(cur_pass)
        next_key = key
    if max_increase==0:
      break
    suggested_labels.append(next_key)
    cur_pass = passed_files_pos(metadata, pos_files, suggested_labels, max_label)
  if get_acc:
    return suggested_labels, len(cur_pass)/len(pos_files)
  return suggested_labels#, cur_pass



# generate label suggestion based on positive examples and knowledge graph
# the keyword of pos_files
# metadata: data loads from "metadata.json", containing info of pos_files
# pos_files: images that expected to be passed
# min_coverage: at least how many pos_files will be covered
# max_label: how many label result from label_detection API are considered
# return: a set of labels for filtering pos_files, with OR relationship
def label_suggestion_pos_filter(keyword, metadata, pos_files, min_coverage=0.9, max_label=10, search_depth=2, get_acc=False):
  occurance = count_occurance(metadata, pos_files, max_label)
  candidacy = infer_label_from_synonym(keyword, is_label=True, depth=search_depth) # label detection has a wider range
  # print("synonmy:" +str(candidacy))
  if candidacy == None:
    candidacy = []
  else:
    candidacy = [s.capitalize() for s in candidacy]
  sorted_keys = []
  for key in sorted(occurance, key=occurance.get)[::-1]:
    sorted_keys.append(key)

  suggested_labels = [keyword.capitalize()]
  cur_pass = passed_files_pos(metadata, pos_files, suggested_labels, max_label)
  while len(suggested_labels) < len(sorted_keys) and len(cur_pass)<min_coverage*len(pos_files):
    max_increase = 0
    next_key = None
    for key in sorted_keys:
      if key in suggested_labels:
        continue
      if not key in candidacy:
        continue
      tmp_set = suggested_labels.copy()
      tmp_set.append(key)
      new_pass = passed_files_pos(metadata, pos_files, tmp_set, max_label)
      if len(new_pass)-len(cur_pass) > max_increase:
        max_increase = len(new_pass)-len(cur_pass)
        next_key = key
    if max_increase==0:
      break
    suggested_labels.append(next_key)
    cur_pass = passed_files_pos(metadata, pos_files, suggested_labels, max_label)
  
  if get_acc:
    total = max(1, len(pos_files))
    return suggested_labels, len(cur_pass)/total
  return suggested_labels, candidacy



#===========================================
# suggest classify——text API
#===========================================

def classify_text_suggestion(keyword, metadata, pos_files, min_coverage=0.9, max_label=10, get_acc=False):
  pos_files = [x for x in pos_files if x in metadata.keys()]
  occurance = count_occurance(metadata, pos_files, max_label)
  sorted_keys = []
  for key in sorted(occurance, key=occurance.get)[::-1]:
    sorted_keys.append(key)

  suggested_labels = []
  cur_pass = passed_files_pos(metadata, pos_files, suggested_labels, max_label)
  while len(suggested_labels) < len(sorted_keys) and len(cur_pass)<min_coverage*len(pos_files):
    max_increase = 0
    next_key = None
    for key in sorted_keys:
      if key in suggested_labels:
        continue
      tmp_set = suggested_labels.copy()
      tmp_set.append(key)
      new_pass = passed_files_pos(metadata, pos_files, tmp_set, max_label)
      if len(new_pass)-len(cur_pass) > max_increase:
        max_increase = len(new_pass)-len(cur_pass)
        next_key = key
    if max_increase==0:
      break
    suggested_labels.append(next_key)
    cur_pass = passed_files_pos(metadata, pos_files, suggested_labels, max_label)
  
  if get_acc:
    total = max(1, len(pos_files))
    return suggested_labels, len(cur_pass)/total
  return suggested_labels, None


def is_in_text_set(keyword):
  with open(TEXT_CLASS_SRC,'r') as f:
    keyword2 = keyword.strip().lower()
    for line in f.readlines():
      text_class = line.strip().lower()
      if keyword2 in text_class:
        return True
  return False



if __name__ == '__main__':
  pass






