import os
import shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from icrawler.builtin import GoogleImageCrawler, BaiduImageCrawler, BingImageCrawler 
import csv
from time import gmtime, strftime
import urllib.request

from numpy.lib.type_check import imag


# folder locations
TMP_FOLDER = "data/tmp"
dir_path = os.path.dirname(os.path.realpath(__file__))
VISION_SRC = os.path.join(dir_path, "vision_src")
CACHE_FOLDER = os.path.join(VISION_SRC, "_cache")
FACE_SRC = os.path.join(VISION_SRC, "face")
TEXT_SRC = os.path.join(VISION_SRC, "text")
FONT_SRC = os.path.join(VISION_SRC, "fonts")
RECORD_DB_SRC = os.path.join(FACE_SRC, "record_results.csv")

if not os.path.exists(CACHE_FOLDER):
    os.makedirs(CACHE_FOLDER)
if not os.path.exists(TEXT_SRC):
    os.makedirs(TEXT_SRC)


def read_image_array(image_path):
  image = Image.open(image_path)
  image_array = np.asarray(image)
  if image_array.ndim == 2:
    image_array = np.repeat(image_array[:, :, np.newaxis], 3, axis=2)
  return image_array

def image_concat(img_path1, img_path2, output_path):
  image_array1 = read_image_array(img_path1)
  image_array2 = read_image_array(img_path2)
  
  w1,h1,_ = image_array1.shape
  w2,h2,_ = image_array2.shape
  if abs((w1+w2+0.0)/max(h1,h2)-1) <= abs(max(w1,w2)/(h1+h2+0.0)-1):
    concat_image = np.zeros((w1+w2, max(h1,h2), 3))
    concat_image[0:w1,0:h1,:] = image_array1
    concat_image[w1:,0:h2,:] = image_array2
  else:
    concat_image = np.zeros((max(w1,w2), h1+h2, 3))
    concat_image[0:w1,0:h1,:] = image_array1
    concat_image[0:w2,h1:,:] = image_array2

  im = Image.fromarray(concat_image.astype('uint8'))
  im.save(output_path)
  return output_path

# (ad hoc) reduce ambiguity of some labels
def fix_label(label):
  label = label.lower()
  # if "apple" in label:
  #   return label + " fruit"
  label = label.replace("/","-").replace("\\","-")
  return label

# case 1: if there is no label given, just give a white background
def no_label():
  return [os.path.join(VISION_SRC, "255px-White.png")]

# helper func: query the database for desired photo
def query_record(query):
  """ Query our record of database of human faces for the best match
  TODO In temporary implementation, greedily find the best match,
  i.e., whichever has the highest passed-in likelihood value, find the best 
  match according to that. Break ties using descending order in:
  anger, joy, surprise, sorrow
  """
  
  db = open(RECORD_DB_SRC, 'r')
  csv_reader = csv.reader(db, delimiter=',', quotechar='"')
  if query is None:
    # just return the first entry
    # csv_reader is a iterator, use this method to jump to 2nd line
    next(csv_reader)
    row = next(csv_reader)
    db.close()
    print("query_record: passed-in query is None, returning the first entry")
    return row
  elif len(query) != 4:
    print("query_record: passed-in tuple not of size 4, returning None")
    db.close()
    return None
  
  likelihoods = ('UNKNOWN', 'VERY_UNLIKELY', 'UNLIKELY', 'POSSIBLE', 'LIKELY', 'VERY_LIKELY')
  anger_index = likelihoods.index(query[0])
  joy_index = likelihoods.index(query[1])
  surprise_index = likelihoods.index(query[2])
  sorrow_index = likelihoods.index(query[3])
  indexs = (anger_index, joy_index, surprise_index, sorrow_index)
  highest_index = indexs.index(max(indexs))

  # Neglect the first row in csv
  next(csv_reader)

  # Loop over the database once, trying to find the exact match
  for row in csv_reader:
    if likelihoods.index(row[highest_index + 1]) == max(indexs):
      db.close()
      return row

  # If cannot find exact match, TODO find the one with the highest value
  # (we know that this exists in DB)
  db.seek(0)
  next(csv_reader)
  for row in csv_reader:
    if row[highest_index + 1] == 'VERY_LIKELY':
      db.close()
      return row
    # NOTE Somehow I cannot find sorrow pic with VERY_LIKELY output. Using this for now.
    elif highest_index == 3 and row[highest_index + 1] == 'LIKELY':
      db.close()
      return row

  assert False, "query_record: SHOULD NOT REACH THIS LINE"

# helper func: turn a string into the desired format
def string2tuplels(face_bounds):
  count = 0
  parsed_list = []
  for i in face_bounds.split(","):
    if count % 2 == 0:
      j = i
    else:
      parsed_list.append((int(j.strip('(')), int(i.strip(')'))))
    count += 1
  # print(parsed_list)
  return parsed_list

# helper func: get the cornor positions from an input face_bounds
# return format: (lower-x, lower-y, upper-x, upper-y)
# parameter: a string in this format
# NOTE: however, PIL encodes image such that first dimension of the 3-d array
# is the y dimension, and the second dimension is x dimension. Be careful!
def get_cornor_pos(face_bounds):
  lx, ly = face_bounds[0]
  ux, uy = face_bounds[0]
  for i in face_bounds:
    if i[0] > ux:
      ux = i[0]
    if i[1] > uy:
      uy = i[1]
  return (lx, ly, ux, uy)

# case 3: feed human faces given output face_bounds\
# note this only takes care of rectangle case, non-rectangle
# non-rectangle cases are probably not so common/significant
def face_bounds2pic(face_bounds, query):
  # determine if it is a rectangle case:
  face_bounds = string2tuplels(face_bounds)
  if len(face_bounds) != 4:
    return None
  for i in face_bounds:
    x_coord_ok = False
    y_coord_ok = False
    for j in face_bounds:
      if i == j:
        continue
      if i[0] == j[0]:
        x_coord_ok = True
      elif i[1] == j[1]:
        y_coord_ok = True
    if not (x_coord_ok and y_coord_ok):
      return None

  # this is a pretty naive implementation, just put all black
  # except where the face is located. Should work fine tho
  query_res = query_record(query)
  db_face_bounds = string2tuplels(query_res[4])
  db_filename = query_res[0]
  pos = get_cornor_pos(face_bounds)
  db_pos = get_cornor_pos(db_face_bounds)
  db_pos_x_len = db_pos[2] - db_pos[0]
  db_pos_y_len = db_pos[3] - db_pos[1]

  # Always return the image at the bottom-right cornor
  ret = np.zeros((pos[3], pos[2], 3))
  db_array = read_image_array(os.path.join(FACE_SRC, db_filename))

  # NOTE: If the requested size is smaller than database size, just return database image
  # because we cannot fit the database image into the return array
  if (pos[2] < db_pos_x_len or pos[3] < db_pos[3] - db_pos[1]):
    return os.path.join(FACE_SRC, db_filename)
  # The bottom-right cornor of the database image fits with 
  # the bottom-right cornor of the requested image
  else:
    ret[pos[3] - db_pos_y_len:pos[3], pos[2] - db_pos_x_len:pos[2], :] = db_array[db_pos[1]:db_pos[3], db_pos[0]:db_pos[2], :]
    im = Image.fromarray(ret.astype('uint8'))
    filename = os.path.join(FACE_SRC, strftime("%Y-%m-%d-%H-%M-%S.png", gmtime()))
    im.save(filename)
    print("face_bounds2pic: creating pic {}".format(filename))
    return filename


def face_detection_with_predefine(likelihood_tuple, face_bound = None):
  """ Given output of face_detection, find the desired photo in our database

  arguments:
  likelihood_tuple -- all parameters within one of the following:
      ('UNKNOWN', 'VERY_UNLIKELY', 'UNLIKELY', 'POSSIBLE', 'LIKELY', 'VERY_LIKELY')
      must NOT be set to None, instead set to UNKNOWN if needed
  FACE_BOUND -- default to None, must be a string in the following format:
      (78,7),(183,7),(183,127),(78,127)

  return: path to the desired photo
  """
  # if anger is None and joy is None and surprise is None and face_bound is None:
  #   print("face_detection: all input passed in are None, returning default photo in DB")
  #   return query_record(None)[0]
  # elif anger is None and joy is None and surprise is None:
  #   print("face_detection: all likelihood input passed in are None, returning default photo in DB")
  #   return face_bounds2pic(face_bound, None)
  
  likelihoods = ('UNKNOWN', 'VERY_UNLIKELY', 'UNLIKELY', 'POSSIBLE', 'LIKELY', 'VERY_LIKELY')
  if likelihood_tuple != None:
    for i in likelihood_tuple:
      if i not in likelihoods:
        print("face_detection: the passed in likelihood parameters not in fixed set, returning None")
        return None
  
  if face_bound == None:
    return query_record(likelihood_tuple)[0]
  else:
    return face_bounds2pic(face_bound, likelihood_tuple)




def face_detection(likelihood_tuple, max_num=2):  
  likelihoods = ('UNKNOWN', 'VERY_UNLIKELY', 'UNLIKELY', 'POSSIBLE', 'LIKELY', 'VERY_LIKELY')
  
  if len(likelihood_tuple)!=4:
    return no_label()

  anger_index = likelihoods.index(likelihood_tuple[0])
  joy_index = likelihoods.index(likelihood_tuple[1])
  surprise_index = likelihoods.index(likelihood_tuple[2])
  sorrow_index = likelihoods.index(likelihood_tuple[3])
  
  if anger_index<=2 and joy_index<=2 and surprise_index<=2 and sorrow_index<=2:
    return image_classification("serious human face", max_num)

  indexs = (anger_index, joy_index, surprise_index, sorrow_index)
  high_index = max(indexs)

  count = 0
  if indexs[0] == high_index:
    count += 1
  if indexs[1] == high_index:
    count += 1
  if indexs[2] == high_index:
    count += 1
  if indexs[3] == high_index:
    count += 1

  max_num = max(1, max_num//count)
  files = []

  if indexs[0] == high_index:
    files += image_classification("angry human face", max_num)
  if indexs[1] == high_index:
    files += image_classification("joyful human face", max_num)
  if indexs[2] == high_index:
    files += image_classification("surprise human face", max_num)
  if indexs[3] == high_index:
    files += image_classification("sad human face", max_num)
  
  return files

def face_detection_face_type(likelihood_tuple):  
  likelihoods = ('UNKNOWN', 'VERY_UNLIKELY', 'UNLIKELY', 'POSSIBLE', 'LIKELY', 'VERY_LIKELY')
  
  if len(likelihood_tuple)!=4:
    return "unknown type of face"

  anger_index = likelihoods.index(likelihood_tuple[0])
  joy_index = likelihoods.index(likelihood_tuple[1])
  surprise_index = likelihoods.index(likelihood_tuple[2])
  sorrow_index = likelihoods.index(likelihood_tuple[3])
  
  if anger_index<=2 and joy_index<=2 and surprise_index<=2 and sorrow_index<=2:
    return "serious human face"

  indexs = (anger_index, joy_index, surprise_index, sorrow_index)
  high_index = max(indexs)

  if indexs[0] == high_index:
    return "angry human face"
  if indexs[1] == high_index:
    return "joyful human face"
  if indexs[2] == high_index:
    return "surprise human face"
  if indexs[3] == high_index:
    return "sad human face"
  
  return "unknown type of face"

def face_detection_assume_one_max(likelihood_tuple, max_num=2):  
  likelihoods = ('UNKNOWN', 'VERY_UNLIKELY', 'UNLIKELY', 'POSSIBLE', 'LIKELY', 'VERY_LIKELY')
  
  if len(likelihood_tuple)!=4:
    return no_label()

  anger_index = likelihoods.index(likelihood_tuple[0])
  joy_index = likelihoods.index(likelihood_tuple[1])
  surprise_index = likelihoods.index(likelihood_tuple[2])
  sorrow_index = likelihoods.index(likelihood_tuple[3])
  
  if anger_index<=2 and joy_index<=2 and surprise_index<=2 and sorrow_index<=2:
    return image_classification("serious human face", max_num)

  indexs = (anger_index, joy_index, surprise_index, sorrow_index)
  highest_index = indexs.index(max(indexs))

  if highest_index == 0:
    return image_classification("angry human face", max_num)
  elif highest_index == 1:
    return image_classification("joyful human face", max_num)
  elif highest_index == 2:
    return image_classification("surprise human face", max_num)
  else:
    return image_classification("sad human face", max_num)


# given a label, find images
# it will delete all contents in output_dir
# def image_classification(label, output_dir, max_num=2):
def image_classification(label, max_num=2):
  if label == "":
    random_img = get_random_image(max_num=max_num*2)[:max_num] # in case not enough
    return random_img+no_label()
  label = label.lower()
  label = fix_label(label)
  file_names = []
  # cache feature implemented
  label_dir = os.path.join(CACHE_FOLDER, label.replace(" ", "_"))
  if os.path.exists(label_dir):
    # If this directory is non-empty, just return the results in it
    if len(os.listdir(label_dir)) != 0:
      print("image_classification: found folder {} exists and non-empty, returning entries in it".format(label_dir))
      for file in os.listdir(label_dir):
        if len(file_names) < max_num:
          file_names.append(os.path.join(label_dir, file))
        else:
          return file_names
  else:
    print("image_classification: creating folder {}".format(label_dir))
    os.mkdir(label_dir)

  
  print("image_classification: searching images with keyword {}".format(label))
  # NOTE The min_size field is added because otherwise the crawler might return some
  # non-openable images
  # crawler = GoogleImageCrawler(storage={'root_dir': TMP_FOLDER})
  # crawler = BaiduImageCrawler(storage={'root_dir': label_dir})
  crawler = BingImageCrawler(storage={'root_dir': label_dir})
  crawler.crawl(keyword="%2b"+label, max_num=max_num, min_size=(200,200)) # force no typo fix
  
  file_names = []
  for file in os.listdir(label_dir):
    if file.startswith("."):
      continue
    file_names.append(os.path.join(label_dir, file))
    if len(file_names) >= max_num:
      break
  print("image_classification: found the following photos: {}".format(os.listdir(label_dir)))
  return file_names

# get a random image from https://picsum.photos
def get_random_image(hsize=15, vsize=15, max_num=3):
  img_hsize = int(hsize * 640 / 15)
  img_vsize = int(vsize * 480 / 15)
  image_list = []
  for no in range(max_num):
    file_name = os.path.join(TEXT_SRC, "background"+strftime("-%Y-%m-%d-%H-%M-%S.png", gmtime()))
    url = "https://picsum.photos/%d/%d?random=%d" % (img_hsize, img_vsize, no)
    try:
      urllib.request.urlretrieve(url, file_name)
      image_list.append(file_name)
    except:
      pass
  if len(image_list) == 0:
    image_list = no_label()
  return image_list

# white or black based on the image
def decide_font_color(image_path, pos=(1,1)):
  with Image.open(image_path) as im:
    rgb_im = im.convert('RGB')
    r, g, b = rgb_im.getpixel(pos)
    luminance = (0.299*r + 0.587*g + 0.114*b)/255;
    if (luminance > 0.5):
       return (0,0,0) # bright colors - black font
    else:
       return (255,255,255) # dark colors - white font

# do not specify a background, use a blank image and random iamges
def text_detection(text, hsize = 15, vsize = 10, max_num = 3):
  """ Given a string TEXT, generate a picture with text in it

  arguments:
  TEXT  -- a string to be displayed
  HSIZE -- maximum number of characters in one line
  VSIZE -- maximum number of lines
  MAX_NUM -- maximum of generated files
  TODO Maybe we should calculate these inside this function, if this works well

  return: path to the desired photos
  """
  import textwrap

  # img_hsize = int(hsize * 200 / 15)
  # img_vsize = int(vsize * 450 / 15)
  img_hsize = int(hsize * 640 / 15)
  img_vsize = int(vsize * 480 / 15)
  text_for_filename = text.replace(" ","-").replace("\n","-n-").replace("\t","-t-").replace("\r","-r-").replace("\'","-1-").replace("\"","-2-")
  

  # The default setting: blank image + printed text
  img = Image.new('RGB', (img_hsize, img_vsize), color = "white")
  fnt = ImageFont.truetype(os.path.join(FONT_SRC, "Times_CE_Regular.ttf"), 20)
  d = ImageDraw.Draw(img)
  para = textwrap.wrap(text, width=3*hsize)
  d.multiline_text((30, 30), '\n'.join(para), fill=(0,0,0), font=fnt)
  filename = os.path.join(TEXT_SRC, text_for_filename+strftime("-%Y-%m-%d-%H-%M-%S.png", gmtime()))
  img.save(filename)
  results = [filename]
  # if len(text.strip()) == 0:
  #   return results

  # then go the remaining
  background_images = get_random_image(hsize=hsize,vsize=vsize,max_num=max_num)
  ttfs = os.listdir(FONT_SRC)
  ttfs.sort()
  for i, ttf in enumerate(ttfs):
    if not (ttf.endswith(".ttf") or ttf.endswith(".TTF")):
      continue
    img = Image.open(background_images[i%len(background_images)])
    img = img.resize((img_hsize, img_vsize))

    color = decide_font_color(background_images[i%len(background_images)], pos=(30,30))
    fnt = ImageFont.truetype(os.path.join(FONT_SRC, ttf), 30)
    d = ImageDraw.Draw(img)
    para = textwrap.wrap(text, width=3*hsize)
    try:
      d.multiline_text((30, 30), '\n'.join(para), fill=color, font=fnt)
    except:
      # in case it is gray image
      d.multiline_text((30, 30), '\n'.join(para), fill=(0), font=fnt)
    
    filename = os.path.join(TEXT_SRC.replace(" ","-"), text_for_filename+"-"+str(i)+strftime("-%Y-%m-%d-%H-%M-%S.png", gmtime()))
    img.save(filename)
    results.append(filename)
    if len(results) >= max_num:
      break
  return results

# specify a background
def text_detection_background(text, background=None, hsize=15, vsize=15):
  """ Given a string TEXT, generate a picture with text in it

  arguments:
  TEXT  -- a string to be displayed
  HSIZE -- maximum number of characters in one line
  VSIZE -- maximum number of lines
  background  -- a file for background. If None, then use white

  return: path to the desired photo, only one photo
  """

  import textwrap
  
  img_hsize = int(hsize * 640 / 15)
  img_vsize = int(vsize * 480 / 15)
  if not background:
    img = Image.new('RGB', (img_hsize, img_vsize), color = "white")
    color = (0,0,0)
  else:
    img = Image.open(background)
    # width, height = img.size
    # left, top, right, bottom = (0, 0, min(width, img_hsize), min(height, img_vsize))
    # img = img.crop((left, top, right, bottom))
    img = img.resize((img_hsize, img_vsize))
    color = decide_font_color(background, pos=(30,30))

  # Uses this font, can change to others if needed
  fnt = ImageFont.truetype(os.path.join(FONT_SRC, "Times_CE_Regular.ttf"), 30)

  d = ImageDraw.Draw(img)
  para = textwrap.wrap(text, width=3*hsize)
  if len(para)<=0:
    para = [""]
  try:
    d.multiline_text((30, 30), '\n'.join(para), fill=color, font=fnt)
  except:
    d.multiline_text((30, 30), '\n'.join(para), fill=(0), font=fnt)
  # d.text((30,30), text, font=fnt, fill=(0,0,0))
 
  filename = os.path.join(TEXT_SRC, text+strftime("-%Y-%m-%d-%H-%M-%S.png", gmtime()))
  img.save(filename)
  return [filename]




def object_detection(objects, output_dir):
  """ Given a list of OBJECTS, call image_classification repeatedly to generate
  a picture with multiple objects/labels on it

  arguments:
  OBJECTS     -- a list of objects/labels on one photo
  OUTPUT_DIR  -- path to output photos

  return: path to the desired photo
  """

  i = 0
  for label in objects:
    img_new = image_classification(label, 1)
    if len(img_new) < 1:
      print("object_detection: call to image_classification returned less than 1 element, returning None")
      return None
    img_new = img_new[0]
    if i == 0:
      img_prev = img_new
    else:
      print("object_detection: iteration {}: concating images at {} and {}".format(i, img_prev, img_new))
      img_prev = image_concat(img_prev, img_new, os.path.join(output_dir, "{}.png".format(i)))
    i += 1
  return img_prev


if __name__ == '__main__':
  pass