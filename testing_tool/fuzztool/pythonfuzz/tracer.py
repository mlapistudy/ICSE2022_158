import collections
import sys

prev_line = 0
prev_filename = ''
# orginal design, (prev_line, cur_line)
data = collections.defaultdict(set)
# new design, only care about one file
data2 = collections.defaultdict(set)

def trace(frame, event, arg):
    if event != 'line':
        return trace

    global prev_line
    global prev_filename

    func_filename = frame.f_code.co_filename
    func_line_no = frame.f_lineno

    if func_filename != prev_filename:
        # We need a way to keep track of inter-files transferts,
        # and since we don't really care about the details of the coverage,
        # concatenating the two filenames in enough.
        data[func_filename + prev_filename].add((prev_line, func_line_no))
    else:
        data[func_filename].add((prev_line, func_line_no))

    data2[func_filename].add(func_line_no)

    prev_line = func_line_no
    prev_filename = func_filename

    return trace


def get_coverage():
    return sum(map(len, data.values()))

# only cares about one file
def get_cov_of_file(file_name):
    total = 0
    if not file_name:
        return 0
    for key in data.keys():
        if (file_name in key) and ('fuzztool/pythonfuzz' not in key) and ('multiprocessing/connection.py' not in key):
            total += len(data[key])
            # print(str((key, data[key])))
    # print("=====")
    return total


def get_loc(file_name):
    if not file_name in data.keys():
        return 0
    # print("=====")
    # print(data2[file_name])
    return len(data2[file_name])

def get_lines(file_name):
    if not file_name in data.keys():
        return ""
    return str(data2[file_name])
