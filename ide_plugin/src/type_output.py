import json
import argparse
import os

def run(args):
    func_name = args.func_name
    type_inputs = args.type_inputs.replace(" ", "")
    dir = os.path.join(args.curr_dir, ".vscode", "tool_json_files", "user_input.json")
    line_nb = int(args.line_nb)
    code_file = args.code_file
    api_params = args.api_params.replace(" ", "")
    type_list = type_inputs.split(",")
    api_params = api_params.split(",")
    if type_list == ['']:
        type_list = []
    if api_params == ['']:
        api_params = []
    j = {
        "func_name": func_name,
        "code_file": code_file,
        "func_def_line": line_nb,
        "input_types": type_list,
        "API_param": api_params,
        "workspace": args.curr_dir
    }
    with open(dir, "w") as write_file:
        json.dump(j, write_file, indent=2)

def main():
    parser=argparse.ArgumentParser(description="schema")
    parser.add_argument("-f",help="function name", dest="func_name", type=str, required=True)
    parser.add_argument("-t",help="type inputs", dest="type_inputs", type=str, required=True)
    parser.add_argument("-d",help="current directory", dest="curr_dir", type=str, required=True)
    parser.add_argument("-n",help="line number of function number", dest="line_nb", type=str, required=True)
    parser.add_argument("-cf",help="code file", dest="code_file", type=str, required=True)
    parser.add_argument("-p",help="API paramaters", dest="api_params", type=str, required=True)
    parser.set_defaults(func=run)
    args=parser.parse_args()
    args.func(args)

if __name__=="__main__":
	main()