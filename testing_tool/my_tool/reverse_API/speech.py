import os
import hashlib
import pyttsx3


dir_path = os.path.dirname(os.path.realpath(__file__))
SPEECH_SRC = os.path.join(dir_path, "speech_src")
CACHE_FOLDER = os.path.join(SPEECH_SRC, "_cache")

if not os.path.exists(CACHE_FOLDER):
    os.makedirs(CACHE_FOLDER)

def hash_string(text):
  hash_code = hashlib.sha256(text.lower().encode('utf-8')).hexdigest()
  return hash_code

def empty_audio():
  return [os.path.join(SPEECH_SRC,"empty_audio.wav")]

def text_to_wav_pyttsx3(text, filename, sample_rate=16000):
  import pyttsx3
  if os.path.exists(filename):
    return filename
  engine = pyttsx3.init()
  engine.save_to_file(text, filename)
  engine.runAndWait()
  return filename


def speech_to_text(text, max_num=5):
  text = text.strip()
  
  engine = pyttsx3.init()
  voices = engine.getProperty('voices')
  files = []
  for no, voice in enumerate(voices):
      if voice.languages[0] in ['en_US', 'en_BG']:
        engine.setProperty('voice', voice.id)

        filename = str(hash_string(text))+"_"+str(no)+".wav"
        filename = os.path.join(CACHE_FOLDER, filename)        
        engine = pyttsx3.init()
        engine.save_to_file(text, filename)
        engine.runAndWait()
        files.append(filename)
        if len(files)>= max_num:
          break
  return files


if __name__ == '__main__':
  pass
  # print(speech_to_text("test."))