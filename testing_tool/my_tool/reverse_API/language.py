import os, sys
import csv
import pandas as pd
import math
import logging
import subprocess

logger = logging.getLogger(__name__)
dir_path = os.path.dirname(os.path.realpath(__file__))
DATA_SRC = os.path.join(dir_path, "language_src/sentiment_data.csv")
SENTIMENT_SRC = os.path.join(dir_path, "language_src/sentiment140.csv")
SENTIMENT_RAW_SRC = os.path.join(dir_path, "language_src/sentiment140/training.csv")
CACHE_SRC = os.path.join(dir_path, "language_src/_cache")
if not os.path.exists(CACHE_SRC):
    os.mkdir(CACHE_SRC)
sys.path.append(os.path.dirname(dir_path))
from global_vars import PYTHON_OHTER


SCORE_LIST_RANGE = 2 # result list contains med+-n scores
MAGNITUDE_LIST_RANGE = 5 # similar as above
MAG_INDEX = .08
NUM = 5 # classify text
CHAR_LIMIT = 50 # classify text

def round_up(n, decimals=0): 
  multiplier = 10 ** decimals 
  return math.ceil(n * multiplier) / multiplier
def round_down(n, decimals=0): 
  multiplier = 10 ** decimals 
  return math.floor(n * multiplier) / multiplier

# bucket score to 0.1 (BITS=1)
# magnitude<0  -> no constraint
def analyze_sentiment(score, magnitude, max_num=5, BITS=1):
  # print(str((score, magnitude)))
  if max_num <= 0:
    max_num = 1
  if score > 1 or score < -1:
    raise ValueError("Score not in range +-1")

  score_l = round_down(score, BITS)
  score_r = round_up(score, BITS)
  if score_l == score_r:
    score_l -= 10**(-BITS) / 2
    score_r += 10**(-BITS) / 2
    score_l = round_down(score_l, BITS+1)
    score_r = round_up(score_r, BITS+1)
  if magnitude >= 0:
    mag_l = round_down(magnitude, BITS)
    mag_r = round_up(magnitude, BITS)
    if mag_l == mag_r:
      mag_l -= 10**(-BITS) / 2
      mag_r += 10**(-BITS) / 2
      mag_l = round_down(mag_l, BITS+1)
      mag_r = round_up(mag_r, BITS+1)
  else: # no constraint
    mag_l = -1
    mag_r = 100
  
  # print(str((score_l, score_r, mag_l, mag_r)))
  return sentiment_within_range(score_l, score_r, mag_l, mag_r, max_num=max_num, BITS=BITS)


def analyze_sentiment_score(score, max_num=5, BITS=1):
  if max_num <= 0:
    max_num = 1
  if score > 1 or score < -1:
    raise ValueError("Score not in range +-1")

  score_l = round_down(score, BITS)
  score_r = round_up(score, BITS)
  if score_l == score_r:
    score_l -= 10**(-BITS) / 2
    score_r += 10**(-BITS) / 2
    score_l = round_down(score_l, BITS+1)
    score_r = round_up(score_r, BITS+1)

  result = []
  max_mag = 3.0
  slice = max_mag/min(max_num,10)
  num_pre = max(1, int(max_num/min(max_num,10)))
  # print(str((max_num, slice, num_pre)))
  mag = 0
  while mag+slice <= max_mag:
    text = sentiment_within_range(score_l, score_r, mag, mag+slice, max_num=num_pre, BITS=BITS)
    result += text
#    result += text1+text2
    mag += slice
    # print(str((score_l, score_r, mag, mag+slice)))
    # print(len(text))
  return list(set(result))

# this version does not persue exact reverse of API
# instead, it is looking into human understanding of positive or negative
# is_positive: whether we want a positive text or not
def analyze_sentiment_without_hard_limit(is_positive, max_num=5):
  if max_num <= 0:
    max_num = 1
  if not os.path.exists(SENTIMENT_RAW_SRC):
    if is_positive:
      return analyze_sentiment(0.8, -1, max_num=max_num)
    return analyze_sentiment(-0.8, -1, max_num=max_num)
  
  result = []
  df_in = pd.read_csv(SENTIMENT_RAW_SRC, header=None, usecols=[0,5], encoding='latin-1')
  # df_out = pd.DataFrame(columns=["score", "magnitude", "text"])
  record_num = len(df_in)
  max_num = min(max_num, record_num//2)
  if is_positive:
    for index, row in df_in.tail(max_num).iterrows():
      result.append(row[5])
  else:
    for index, row in df_in.head(max_num).iterrows():
      result.append(row[5])

  return result


def sentiment_within_range(score_l, score_r, mag_l, mag_r, max_num, BITS):
  df = pd.read_csv(SENTIMENT_SRC, encoding='latin-1')
  # print((score_l, score_r, mag_l, mag_r))
  # find text with preferred score
  mag_to_text = {}
  for index, row in df.iterrows():
    if row["score"]>=score_l and row["score"]<=score_r:
      mag = round(row["magnitude"], BITS+1)
      # print(row["score"])
      if mag in mag_to_text.keys():
        mag_to_text[mag].append(row["text"])
      else:
        mag_to_text[mag] = [row["text"]]


  # finding suitable text
  possible_mags = list(mag_to_text.keys())
  possible_mags.sort()

  def get_text_from_mag(low, high):
    result = []
    for mag in possible_mags:
      if mag>=low and mag<=high:
        result = result + mag_to_text[mag]
    return result

  target_text = get_text_from_mag(mag_l, mag_r)
  if len(target_text) >= max_num:
    return target_text[:max_num]

  for mag in possible_mags:
    if mag>=mag_l: # already included
      break
    # compose severak text
    text1 = mag_to_text[mag]
    text2 = get_text_from_mag(mag_l-mag, mag_r-mag)
    for t1 in text1:
      for t2 in text2:
        if t1==t2:
          continue
        if t1.strip().endswith(".") or t1.strip().endswith("?") or t1.strip().endswith("!") or t1.strip().endswith(";"):
          target_text.append(t1 + " " + t2)
        else:
          target_text.append(t1 + ". " + t2)
    if len(target_text) >= max_num:
      return target_text[:max_num]

  # if still not sufficient, add multiplier
  for mag in possible_mags:
    if mag >= mag_l:
      break
    mult = 2
    while mag*mult<=mag_r:
      text1 = mag_to_text[mag]
      new_mag = round(mag*mult, BITS+1)
      if new_mag>=mag_l: # do not need extra text
        text2 = [" "]
      else:
        text2 = get_text_from_mag(mag_l-new_mag, mag_r-new_mag)
      for t1 in text1:
        for t2 in text2:
          if t1==t2:
            continue
          if t1.strip().endswith(".") or t1.strip().endswith("?") or t1.strip().endswith("!") or t1.strip().endswith(";"):
            target_text.append(" ".join([t1]*mult) + " " + t2)
          else:
            target_text.append(". ".join([t1]*mult) + ". " + t2)
      mult+=1
      if len(target_text) >= max_num:
        return target_text[:max_num]

  return target_text[:max_num]


# ==================================================================================================
import requests
from bs4 import BeautifulSoup
import random
import re
import time as time
import signal




def search_keyword_1(keyword):
    import requests
    from bs4 import BeautifulSoup
    import random

    url = 'https://google.com/search?q=' + keyword.replace(" ", "+")
    A = ("Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36",
        )
    
    Agent = A[random.randrange(len(A))]
    headers = {'user-agent': Agent}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'lxml')
    text = soup.get_text()
    return [text]


#Close session
def handler(signum, frame):
    raise Exception('Action took too much time')


def select_chunk(lines, num, char_limit):
    # A chunk is defined to be a consecutive num lines that
    # exceed the character limit
    i = 0
    while i < len(lines):
        j = i
        found = True
        while j < i + num:
            if j >= len(lines):
                found = False
                break
            if not len(lines[j].strip()) >= char_limit:
                found = False
                break
            j += 1
        if found:
            # print("executed")
            return [lines[k].strip() for k in range(i, i + num)]
        i += 1
    # print("not found")
    # return [lines[k] for k in range(0, num)]
    return None

def strip_whitelines(lines):
    lines = lines.split("\n")
    non_empty_lines = [line for line in lines if line.strip() != ""]
    return non_empty_lines

def process_lines(lines, num, char_limit):
    lines = strip_whitelines(lines)
    res = select_chunk(lines, num, char_limit)
    if res == None:
        return None
    string_without_empty_lines = ""
    for line in res:
        string_without_empty_lines += line + "\n"
    return string_without_empty_lines

def process_lines_if_failed(lines, num):
    lines = strip_whitelines(lines)
    if num > len(lines):
        # num = len(lines) - 1
        return None
    res = [lines[k] for k in range(0, num)]
    string_without_empty_lines = ""
    for line in res:
        string_without_empty_lines += line + "\n"
    return string_without_empty_lines

def remove_dup(ls):
    res = []
    for i in ls:
        if i not in res:
            res.append(i)
    return res

def soup_find_all_2(soup):
    return remove_dup(soup.find_all("a",href=re.compile("(?<=/url\?q=)(htt.*://.*)")))
def process_link_fcn_2(link, keyword):
    ls = re.split(":(?=http)",link["href"].replace("/url?q=",""))
    item = ls[0]
    return item
def url_fcn_2(keyword):
    url = 'https://google.com/search?q=' + keyword.replace(" ", "+")
    return url
def find_page_text_2(soup):
    return soup.get_text()

def soup_find_all_3(soup):
    return soup.find_all('a', attrs={'href':True, 'data-serp-pos':True})
def process_link_fcn_3(link, keyword):
    url = url_fcn_3(keyword)
    item = requests.compat.urljoin(url, link['href'])
    return item
def url_fcn_3(keyword):
    url = 'https://en.wikipedia.org/w/index.php?search=' + keyword.replace(" ", "+") + r"&title=Special%3ASearch&fulltext=1&ns0=1"
    return url
def find_page_text_3(soup):
    return soup.get_text()

def soup_find_all_4(soup):
    temp = soup.find('div', attrs={'class':'search-results'})
    return temp.find_all('a')
def process_link_fcn_4(link, keyword):
    url = url_fcn_4(keyword)
    item = requests.compat.urljoin(url, link['href'])
    return item
def url_fcn_4(keyword):
    url = 'https://www.britannica.com/search?query=' + keyword.replace(" ", "+")
    return url
def find_page_text_4(soup):
    ls = map(lambda foo: foo.get_text(), soup.find_all('p', attrs={'class':'topic-paragraph'}))
    res = '\n'.join(ls)
    return res

def find_wikipedia(keyword, max_num=10):
  import wikipedia
  res = []
  wiki_res = wikipedia.search(keyword, results=max_num)
  logger.info(f"classify_text reverse: Wikipedia search returned {wiki_res}")
  for entry in wiki_res:
    try:
      entry = wikipedia.page(entry)
      logger.info(f"classify_text reverse: Getting text from {entry.url}")
      res.append(entry.content)
    except Exception as e:
      logger.exception(f"classify_text reverse: searching with entry {entry} returned {e}, skipping")
  return res


def search_keyword_generic(keyword, soup_find_all, process_link_fcn, url_fcn, find_page_text_fcn, max_num = 1, line_num = NUM, char_limit = CHAR_LIMIT, outfd = None):

    assert(max_num >= 1)
    # assert(outfd != None)
    # url = 'https://google.com/search?q=' + keyword.replace(" ", "+")
    url = url_fcn(keyword)
    A = ("Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36",
        )
    Agent = A[random.randrange(len(A))]
    headers = {'user-agent': Agent}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'lxml')
    links = soup.find_all("a")
    i = 0
    first = None
    res = []
    for link in soup_find_all(soup):
        # ls = re.split(":(?=http)",link["href"].replace("/url?q=",""))
        # item = ls[0]
        item = process_link_fcn(link, keyword)
        # for item in ls:
        item = item.split('&')[0]
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(5) #Set the parameter to the amount of seconds you want to wait
        try:
            r = requests.get(item, headers=headers)
            soup = BeautifulSoup(r.text, 'lxml')
            # text = soup.get_text()
            # REVIEW
            text = find_page_text_fcn(soup)
            # Special processing for wikipedia 
            if not "https://en.wikipedia.org/" in item:
              text = process_lines(text, line_num, char_limit)
              if i == 0:
                  first = item
                  i += 1
              if text != None and len(text.split()) >= 25:
                  # print(item)
                  if outfd != None:
                      outfd.write(item + "\n")
                  # print(text)
                  logger.info(f"classify_text reverse: Getting text from {item}")
                  signal.alarm(0) #Disables the alarm
                  res.append(text)
                  if len(res) == max_num:
                      return res
        except:
            signal.alarm(0) #Disables the alarm
            continue
        signal.alarm(0) #Disables the alarm
    # If all above fails, do this:
    if first == None:
        return None

    r = requests.get(first, headers=headers)
    soup = BeautifulSoup(r.text, 'lxml')
    text = soup.get_text()
    text = process_lines_if_failed(text, line_num)
    if text != None and len(text.split()) >= 25:
        res.append(text)
        # print(first)
        if outfd != None:
            outfd.write(first + "\n")
    return res

def classify_text(keyword, max_num=3):

  logging.info(f"classify_text (reverse API): getting reverse results for keyword {keyword}")
  if len(keyword)==0:
    logging.info(f"classify_text (reverse API): returnning non-sense words")
    return ["Non sense text to aviod too few tokens (words) to process. Non sense text to aviod too few tokens (words) to process. Non sense text to aviod too few tokens (words) to process."]


  def run_command(command):
    print(command)
    proc = subprocess.Popen(command, shell=True)
    proc.wait()

  # Invoking this in a seperate script because running this in the
  # solve_multi.py environment would produce some unexpected error with the wikipedia package
  # So, invoke the script to produce the desired cache file, from which to read the result
  file_name = os.path.dirname(os.path.realpath(__file__))
  if not PYTHON_OHTER:
    command = f"cd {file_name}; python3.8 search_text.py --keyword='{keyword}' --max_num={max_num}"
  else:
    command = f"cd {file_name}; python3.6 search_text.py --keyword='{keyword}' --max_num={max_num}"

  logging.info(f"classify_text (reverse API): issuing the following command {command}")
  run_command(command)

  keyword = keyword.split("/")[-1]
  filename = os.path.join(CACHE_SRC, keyword)
  if os.path.exists(filename):
      with open(filename, 'r', encoding='utf8') as file_obj:
          text = file_obj.read()
      ret = eval(text)
      if True:
      # if len(ret) >= max_num: # test only
          ret = [x[:4000].replace("\n"," ").replace("\r"," ") for x in ret]
          logging.info(f"classify_text (reverse API): got reverse result from file {filename}")
          return ret[:max_num]
  
  logging.error(f"classify_text (reverse API): the cache file at {filename} should have been created, but it has not")
  exit(-1)

    # max_num_each = max(max_num,1) #max(max_num//3, 1)
    # res1 = search_keyword_1(keyword)
    # logging.info(f"classify_text (reverse API): Google search the page itself returned {len(res1)} results")
    # res2 = search_keyword_generic(keyword, soup_find_all_2, process_link_fcn_2, url_fcn_2, find_page_text_2, max_num=max_num_each, line_num=5, char_limit=50)
    # logging.info(f"classify_text (reverse API): Google search going to top {max_num_each} results returned {len(res2)} results")
    # # res3 = search_keyword_generic(keyword, soup_find_all_3, process_link_fcn_3, url_fcn_3, find_page_text_3, max_num=max_num_each, line_num=5, char_limit=50)
    # res3 = find_wikipedia(keyword, max_num=max_num_each)
    # logging.info(f"classify_text (reverse API): Wikipedia search with the top {max_num_each} results returned {len(res3)} results")
    # res4 = search_keyword_generic(keyword, soup_find_all_4, process_link_fcn_4, url_fcn_4, find_page_text_4, max_num=max_num_each, line_num=5, char_limit=50)
    # logging.info(f"classify_text (reverse API): Britannica search with the top {max_num_each} results returned {len(res4)} results")

    # # In this way, the returned list preserves the order of the individually searched result
    # i = 0
    # res = []
    # max_len = max(len(res1), len(res2), len(res3), len(res4))
    # while (i < max_len):
    #   for list_name in [res1, res2, res3, res4]:
    #     if i < len(list_name):
    #       res.append(list_name[i])
    #   i += 1

    # # res = res1 + res2 + res3 + res4
    # ret = set()
    # # Filter out any None items, or too short text
    # for i in res:
    #     if i != None:
    #         text_instance = i[:4000].replace("\n"," ").replace("\r"," ")
    #         if not keyword in text_instance.lower():
    #           continue
    #         if len(i)>=50:
    #             ret.add(text_instance)
    # ret = list(ret)
    # with open(filename, 'w', encoding='utf8') as file_obj:
    #     file_obj.write(str(ret))
    # if len(ret) >= max_num:
    #   return ret[:max_num]
    # return ret

def analyze_entities(type, name=None, force_new=False, max_num=1):
  """ Given either type or name of a detected entity, generate a sentence
      that contains that entity

  arguments:
  type - type of entity
  name - name of entity, if name is specified, generate text using name
  force_new - whether to generate and rewrite cached results
  max_num - max number of texts to return
  """

  if max_num < 1:
    max_num = 1

  res_list = []
  if name != None:
    for i in range(max_num):
      filename = os.path.join(CACHE_SRC, "analyze_entities_" + name + "_{}.txt".format(i))
      # Checking cache folder first
      if force_new == False:
        if os.path.exists(filename):
          with open(filename, "r", encoding='utf8') as fd:
            res_list.append(fd.read())
          continue

      res = generate_text(name, num_outputs=max_num - i)
      for each_res in res:
        filename = os.path.join(CACHE_SRC, "analyze_entities_" + name + "_{}.txt".format(i))
        with open(filename, "w", encoding='utf8') as fd:
          fd.write(each_res)
        i += 1
      res_list += res
      break
    return res_list

  special_line = None
  for i in range(max_num):
    filename = os.path.join(CACHE_SRC, "analyze_entities_" + type + "_{}.txt".format(i))
    # Checking cache folder first
    if force_new == False:
      if os.path.exists(filename):
        with open(filename, "r", encoding='utf8') as fd:
          res_list.append(fd.read())
        continue
    
    if special_line == None:
      file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "language_src", "entity_type.csv")
      with open(file_path, "r") as fd:
        for line in fd.readlines():
          line = line.strip("\n")
          if line.split(",")[0] == type:
            special_line = line
            break
      if special_line == None:
        raise ValueError("analyze_entities: cannot find matching type {} in entity_type.csv".format(type))
    
    # Found special line
    # NOTE: now only uses the first entity because that is guarateened to succeed
    res = generate_text(special_line.split(",")[1], num_outputs=max_num - i)
    for each_res in res:
      # print(len(res))
      filename = os.path.join(CACHE_SRC, "analyze_entities_" + type + "_{}.txt".format(i))
      with open(filename, "w", encoding='utf8') as fd:
        fd.write(each_res)
      i += 1
    res_list += res
    break

  return res_list


# def analyze_syntax_test(tag, force_new=False, max_num=1):
#   file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "language_src", "syntax_type.csv")
#   with open(file_path, "r") as fd:
#     for line in fd.readlines():
#       line = line.strip("\n")
#       if line.split(",")[0] == tag:
#         special_line = line
#         return [special_line.split(",")[1]]
#   return [""]
  
    


def analyze_syntax(tag, force_new=False, max_num=1):
  if max_num < 1:
    max_num = 1

  res_list = []

  special_line = None
  for i in range(max_num):
    filename = os.path.join(CACHE_SRC, "analyze_syntax_" + tag + "_{}.txt".format(i))
    # Checking cache folder first
    if force_new == False:
      if os.path.exists(filename):
        with open(filename, "r", encoding='utf8') as fd:
          res_list.append(fd.read())
        continue
    
    if special_line == None:
      file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "language_src", "syntax_type.csv")
      with open(file_path, "r") as fd:
        for line in fd.readlines():
          line = line.strip("\n")
          if line.split(",")[0] == tag:
            special_line = line
            break
      if special_line == None:
        raise ValueError("analyze_entities: cannot find matching tag {} in entity_type.csv".format(tag))
    
    # Found special line
    # NOTE: now only uses the first entity because that is guarateened to succeed
    res = generate_text(special_line.split(",")[1], num_outputs=max_num - i)
    for each_res in res:
      # print(len(res))
      filename = os.path.join(CACHE_SRC, "analyze_syntax_" + tag + "_{}.txt".format(i))
      with open(filename, "w", encoding='utf8') as fd:
        fd.write(each_res)
      i += 1
    res_list += res
    break

  return res_list


def generate_text(text, min_length = 30, max_length = 50, num_outputs = 1):
  import transformers
  import tensorflow as tf
  import sys

  GPT2Tokenizer = transformers.GPT2Tokenizer
  TFGPT2LMHeadModel = transformers.TFGPT2LMHeadModel

  tokenizer = GPT2Tokenizer.from_pretrained("gpt2")

  # add the EOS token as PAD token to avoid warnings
  model = TFGPT2LMHeadModel.from_pretrained("gpt2", pad_token_id=tokenizer.eos_token_id)

  # set seed to reproduce results. Feel free to change the seed though to get different results
  # tf.random.set_seed(0)

  # encode context the generation is conditioned on
  input_ids = tokenizer.encode(text, return_tensors='tf')

  # deactivate top_k sampling and sample only from 92% most likely words
  sample_outputs = model.generate(
      input_ids,
      do_sample=True,
      min_length=min_length,
      max_length=max_length,
      num_return_sequences=num_outputs,
      top_p=0.92, 
      top_k=0
  )

  res = []
  for i, sample_output in enumerate(sample_outputs):
    res.append(tokenizer.decode(sample_output, skip_special_tokens=True))

  return res

if __name__ == "__main__":
  pass
  logging.basicConfig(level=logging.INFO)
  
