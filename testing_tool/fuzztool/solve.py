# Copyright: see copyright.txt

import os
import sys
from optparse import OptionParser
import subprocess

import sys, io
sys.path.append('../')
import API_wrapper.buffer_map as buffer_map

OUTPUT_PRE_SOLUTION = 50

def run_command(command):
  proc = subprocess.Popen(command, shell=True)
  proc.wait()

if __name__ == '__main__':
  # print("PyExZ3 (Python Exploration with Z3)")

  sys.path = [os.path.abspath(os.path.join(os.path.dirname(__file__)))] + sys.path

  usage = "usage: %prog [options] <path to a *.py file>"
  parser = OptionParser(usage=usage)
  parser.add_option("-o", "--output-file", dest="output_file", type="string", help="Place where save generated files", default=0)
  parser.add_option("-t", "--test-file", dest="test_file", type="string", help="File for running python fuzz", default=0)

  (options, args) = parser.parse_args()

  all_inputs = []
  files = set()
  for i in range(OUTPUT_PRE_SOLUTION):
    buf = os.urandom(4)
    file = buffer_map.get_imagenet_image(buf)
    files.add(file)
  all_inputs.append('\n'.join(files))

  files = set()
  for i in range(OUTPUT_PRE_SOLUTION//10):
    buf = os.urandom(4)
    file = buffer_map.get_random_image(buf)
    files.add(file)
  all_inputs.append('\n'.join(files))

  # print(all_inputs)

  if options.output_file and options.test_file:
    output_file = os.path.abspath(options.output_file)
    print("Output file: " + output_file)
    f = open(output_file, 'w')
    for item in all_inputs:
      print("Working ... ")
      for generated_file in item.split('\n'):
        f.write(generated_file+"\n")
        test_file = os.path.abspath(options.test_file)
        cur_dir = os.path.dirname(os.path.realpath(__file__))
        run_command("cp "+generated_file+" ../my_tool/reverse_API/vision_src/_cache/test.jpg")
        run_command("python3.8 "+ test_file +" --rss-limit-mb=20480 --timeout=60 --runs=1 --loc_file="+ test_file +" > "+cur_dir+"/tmp")
        # run_command("(cat tmp|tail -2|head -1) >> "+output_file)
        f2 = open(cur_dir+"/tmp", 'r')
        lines = f2.readlines()
        f2.close()
        for line in reversed(lines):
          if line.strip().startswith(">>"):
            if not line.endswith("\n"):
              line = line + "\n"
            f.write(line)
            break
          run_command("rm tmp")
      f.write("\n=======================\n")
    f.close()
    run_command("rm crash-*")


    

