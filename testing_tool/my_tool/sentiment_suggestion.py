import os
import csv
import pandas as pd
import math
import numpy as np
from collections import defaultdict
from google.cloud import language_v1
from google.cloud.language_v1 import enums
from sklearn.linear_model import LogisticRegression


dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "reverse_API")
DATA_SRC = os.path.join(dir_path, "language_src/sentiment_data.csv")
SENTIMENT_SRC = os.path.join(dir_path, "language_src/sentiment140.csv")
SENTIMENT_RAW_SRC = os.path.join(dir_path, "language_src/sentiment140/training.csv")


class Sentence(object):
  def __init__(self, score, magnitude, text):
    self.text = text
    self.score = score
    self.magnitude = magnitude

  def print_info(self):
    print("score: %.2f  magnitude: %.2f" % (self.score, self.magnitude))

  def get_value(self):
    return [self.score, self.magnitude]


def classifier_logic(pos, neg):
  label = [True]*len(pos)+[False]*len(neg)
  label = np.array(label)
  data = []
  for sentence in pos:
    data.append(sentence.get_value())
  for sentence in neg:
    data.append(sentence.get_value())
  data = np.array(data)
  reg = LogisticRegression(solver='lbfgs').fit(data, label)
  coef = reg.coef_[0]
  classifier = "Positive (Negative) text: score*(%0.3f) + magnitude*(%0.3f) >= (<) 0"%(coef[0],coef[1])
  accuracy = reg.score(data, label)
  return classifier, accuracy

def sentiment_classifier(pos_text, neg_text):
  def turn_class(text):
    client = language_v1.LanguageServiceClient()
    document = language_v1.types.Document(content=text, type=enums.Document.Type.PLAIN_TEXT)
    response = client.analyze_sentiment(document=document).document_sentiment
    score, magnitude = response.score, response.magnitude
    return Sentence(score, magnitude, text)
  
  pos_sentences = [turn_class(x) for x in pos_text]
  neg_sentences = [turn_class(x) for x in neg_text]
  rule, accuracy = classifier_logic(pos_sentences, neg_sentences)
  return rule, accuracy

if __name__ == "__main__":
  pass



