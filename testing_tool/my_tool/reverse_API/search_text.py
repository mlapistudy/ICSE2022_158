import os
import csv
import math
import logging
import wikipedia

logger = logging.getLogger(__name__)
dir_path = os.path.dirname(os.path.realpath(__file__))
DATA_SRC = os.path.join(dir_path, "language_src/sentiment_data.csv")
SENTIMENT_SRC = os.path.join(dir_path, "language_src/sentiment140.csv")
SENTIMENT_RAW_SRC = os.path.join(dir_path, "language_src/sentiment140/training.csv")
CACHE_SRC = os.path.join(dir_path, "language_src/_cache")
if not os.path.exists(CACHE_SRC):
    os.mkdir(CACHE_SRC)


SCORE_LIST_RANGE = 2 # result list contains med+-n scores
MAGNITUDE_LIST_RANGE = 5 # similar as above
MAG_INDEX = .08
NUM = 5 # classify text
CHAR_LIMIT = 50 # classify text


# ==================================================================================================
import requests
from bs4 import BeautifulSoup
import random
import re
import time as time
import signal


def search_keyword_1(keyword):
    import random

    url = 'https://www.bing.com/search?q=' + keyword.replace(" ", "+")
    # url = 'https://google.com/search?q=' + keyword.replace(" ", "+")
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
    # print(soup)
    return soup.find_all("a",href=re.compile("htt.*://*"))
    # return remove_dup(soup.find_all("a",href=re.compile("(?<=/url\?q=)(htt.*://.*)")))
def process_link_fcn_2(link, keyword):
    ls = re.split(":(?=http)",link["href"].replace("/url?q=",""))
    item = ls[0]
    return item
def url_fcn_2(keyword):
    url = 'https://bing.com/search?q=' + keyword.replace(" ", "+")
    # url = 'https://google.com/search?q=' + keyword.replace(" ", "+")
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
  res = []
  wiki_res = wikipedia.search(keyword, results=max_num)
  logger.info(f"classify_text (reverse API) - inside file: Wikipedia search returned {wiki_res}")
  for entry in wiki_res:
    try:
      entry = wikipedia.page(entry)
      logger.info(f"classify_text (reverse API) - inside file: Getting text from {entry.url}")
      res.append(entry.content)
    except Exception as e:
      logger.exception(f"classify_text (reverse API) - inside file: searching with entry {entry} returned {e}, skipping")
  return res


def search_keyword_generic(keyword, soup_find_all, process_link_fcn, url_fcn, find_page_text_fcn, max_num = 1, line_num = NUM, char_limit = CHAR_LIMIT, outfd = None):

    assert(max_num >= 1)
    url = url_fcn(keyword)
    A = ("Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36",
        )
    Agent = A[random.randrange(len(A))]
    headers = {'user-agent': Agent}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'lxml')
    # links = soup.find_all("a")
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
                  logger.info(f"classify_text (reverse API) - inside file: Getting text from {item}")
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
    if len(keyword)==0:
      return ["Non sense text to aviod too few tokens (words) to process. Non sense text to aviod too few tokens (words) to process. Non sense text to aviod too few tokens (words) to process."]
    logger.info(f"classify_text (reverse API) - inside file: getting reverse results for keyword {keyword}")
    keyword = keyword.split("/")[-1]
    filename = os.path.join(CACHE_SRC, keyword)
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf8') as file_obj:
            text = file_obj.read()
        ret = eval(text)
        # if True:
        if len(ret) >= max_num:
            ret = [x[:4000].replace("\n"," ").replace("\r"," ") for x in ret]
            logger.info(f"classify_text (reverse API) - inside file: got reverse result from file {filename}")
            return ret[:max_num]

    max_num_each = max(max_num,1) #max(max_num//3, 1)
    res1 = search_keyword_1(keyword)
    logger.info(f"classify_text (reverse API) - inside file: Bing search the page itself returned {len(res1)} results")
    res2 = search_keyword_generic(keyword, soup_find_all_2, process_link_fcn_2, url_fcn_2, find_page_text_2, max_num=max_num_each, line_num=5, char_limit=50)
    logger.info(f"classify_text (reverse API) - inside file: Bing search going to top {max_num_each} results returned {len(res2)} results")
    res3 = find_wikipedia(keyword, max_num=max_num_each)
    logger.info(f"classify_text (reverse API) - inside file: Wikipedia search with the top {max_num_each} results returned {len(res3)} results")
    res4 = search_keyword_generic(keyword, soup_find_all_4, process_link_fcn_4, url_fcn_4, find_page_text_4, max_num=max_num_each, line_num=5, char_limit=50)
    logger.info(f"classify_text (reverse API) - inside file: Britannica search with the top {max_num_each} results returned {len(res4)} results")

    # In this way, the returned list preserves the order of the individually searched result
    i = 0
    res = []
    max_len = max(len(res1), len(res2), len(res3), len(res4))
    while (i < max_len):
      for list_name in [res1, res2, res3, res4]:
        if i < len(list_name):
          res.append(list_name[i])
      i += 1

    # res = res1 + res2 + res3 + res4
    ret = []
    # Filter out any None items, or too short text
    for i in res:
        if i != None:
            text_instance = i[:4000].replace("\n"," ").replace("\r"," ")
            if not keyword.lower() in text_instance.lower():
              continue
            if len(i)>=50 and i not in ret:
                ret.append(i)
    if len(ret) < max_num:
        ret = []
        for i in res:
            if i != None:
                text_instance = i[:4000].replace("\n"," ").replace("\r"," ")
                if len(i)>=50 and i not in ret:
                    ret.append(i)
    # ret = list(ret)
    with open(filename, 'w', encoding='utf8') as file_obj:
        logger.info(f"classify_text (reverse API) - inside file: wrote results to file {filename}")
        file_obj.write(str(ret))


if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser(description="language")
    logging.basicConfig(level=logging.INFO)
    # arguments for file
    parser.add_argument("--keyword", type=str, required=True)
    parser.add_argument("--max_num", type=int, required=True)

    args=parser.parse_args()
    classify_text(args.keyword, max_num=args.max_num)
