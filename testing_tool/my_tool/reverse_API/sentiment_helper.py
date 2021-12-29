import io
import os
import csv
import sys
import subprocess

from google.cloud import language_v1
from google.cloud.language_v1 import enums
import language as mylang
import pandas as pd

def get_sentiment(text):
  client = language_v1.LanguageServiceClient()
  document = language_v1.types.Document(content=text, type=enums.Document.Type.PLAIN_TEXT)
  response = client.analyze_sentiment(document=document)
  return response

def quick_test():
  text = "I can’t believe it. Is all good? See you next time."
  response = get_sentiment(text)
  result = mylang.analyze_sentiment(response, None, None)
  print(result)

def run_command(command):
  proc = subprocess.Popen(command, shell=True)
  proc.wait()

# more description in https://www.tensorflow.org/datasets/catalog/sentiment140
# data sample: "0","1467810369","Mon Apr 06 22:19:45 PDT 2009","NO_QUERY","_TheSpecialOne_","@switchfoot http://twitpic.com/2y1zl - Awww, that's a bummer.  You shoulda got David Carr of Third Day to do it. ;D"
def download_sentiment140():
  folder_path = "language_src/sentiment140/"
  data_url = "http://cs.stanford.edu/people/alecmgo/trainingandtestdata.zip"

  if os.path.isdir(path):
    return
  os.makedirs(path)
  run_command("wget "+data_url+" -P "+folder_path)
  run_command("unzip " + os.path.join(folder_path, "trainingandtestdata.zip") + " -d " + folder_path)

def process_sentiment140(input_file, output_file, record_num):
  def call_API(text):
    response = get_sentiment(text)
    return response.document_sentiment.score, response.document_sentiment.magnitude
  
  neg_num = record_num//5 * 2
  nueral_num = record_num//5 # seems no nueral ones
  pos_num = record_num//5 * 2
  remain = record_num
  df_in = pd.read_csv(input_file, header=None, usecols=[0,5], encoding='latin-1')

  df_out = pd.DataFrame(columns=["score", "magnitude", "text"])

  record_num = len(df_in)
  # row = df_in.iloc[record_id]
  
  for index, row in df_in.head(neg_num).iterrows():
    if index % 100 == 0:
      print("Remaining " + str(pos_num+neg_num-index) + "...")
    try:
      score, magnitude = call_API(row[5])
      df_out = df_out.append(dict(
            score=score,
            magnitude=magnitude,
            text=row[5]
          ), ignore_index=True)
    except Exception as e:
      print("Error on row "+str(index))
  for index, row in df_in.tail(pos_num).iterrows():
    if (record_num-index) % 100 == 0:
      print("Remaining " + str(record_num-index) + "...")
    try:
      score, magnitude = call_API(row[5])
      df_out = df_out.append(dict(
            score=score,
            magnitude=magnitude,
            text=row[5]
          ), ignore_index=True)
    except Exception as e:
      print("Error on row "+str(index))

  df_out.to_csv(output_file, index= False)

def read_csv(input_file):
  df = pd.read_csv(input_file, encoding='latin-1')
  print(df.head(5))
  print(df.tail(5))


if __name__ == "__main__":
  # download_sentiment140()
  process_sentiment140("language_src/sentiment140/training.csv", "language_src/sentiment140.csv", 5000)
  # csv("language_src/sentiment140.csv")
  
