import os, sys
import io
import logging
import argparse
import json
from pathlib import Path

from analyzer import CallGraphVisitor
from visgraph import VisualGraph
from glob import glob
# import pyan
from writers import DotWriter, HTMLWriter, SVGWriter
from node import Flavor
from anytree import AnyNode, RenderTree, PreOrderIter
from anytree.exporter import JsonExporter

from api_namespace import All_API_Names

class Function_Tracer():
    def __init__(self, workspace: str):
        self.workspace = workspace
        self.logger = logging.getLogger(__name__)

        # Comment out if do not want detailed logging info
        logging.basicConfig(level=logging.DEBUG)
        
        self.logger.info("workspace is set to {}".format(self.workspace))

        # Options needed for the pyan visulization
        nested_groups: bool = True
        draw_defines: bool = True
        draw_uses: bool = True
        colored: bool = True
        grouped_alt: bool = False
        annotated: bool = False
        grouped: bool = True
        max_iter: int = 1000
        rankdir = "LR"

        self.graph_options = {
            "draw_defines": draw_defines,
            "draw_uses": draw_uses,
            "colored": colored,
            "grouped_alt": grouped_alt,
            "grouped": grouped,
            "nested_groups": nested_groups,
            "annotated": annotated,
        }

        # TODO: check if these are the sufficient/necessary flavors
        self.legal_flavors = [Flavor.CLASSMETHOD, Flavor.FUNCTION, Flavor.METHOD, Flavor.ATTRIBUTE, Flavor.STATICMETHOD]
        # STUB: gather all ML API namespace information
        # self.legal_API_namespace = ["google.cloud.language_v1.LanguageServiceClient.analyze_sentiment"]
        self.legal_API_namespace = All_API_Names
        #print(All_API_Names)

        self.result_json = None

    def run(self):
        # This syntax matches any .py files in any sub-folders, an example is:
        # filenames = "/Users/../Mind_Reading_Journal/**/*.py"
        filenames = os.path.join(self.workspace, "**/*.py")
        if isinstance(filenames, str):
            filenames = [filenames]
        filenames = [fn2 for fn in filenames for fn2 in glob(fn, recursive=True)]

        self.logger.info(f"Relevant files include {filenames}")

        # TODO figure out why root cannot have the last backslash
        # If we use root="/Users/../Mind_Reading_Journal/" then we get into an infinite loop
        # So we must use "/Users/../Mind_Reading_Journal" without the last backslash
        if self.workspace[-1] == '/':
            root_str = self.workspace[:-1]
        else:
            root_str = self.workspace
        v = CallGraphVisitor(filenames, root=root_str)

        self.logger.info("Here are the defines_edges traced:")
        self.logger.info(v.defines_edges)
        self.logger.info("Here are the uses_edges traced")
        self.logger.info(v.uses_edges)

        # 1. Get all the functions traceable from the ML APIs in the uses_edges
        next_neighbours = []
        next_neighbours_cache = []
        traced_nodes = []
        for from_node in v.uses_edges:
            for to_node in v.uses_edges[from_node]:
                # STUB: gather all ML API namespace information
                if to_node.get_name() in self.legal_API_namespace:
                    if from_node.flavor in self.legal_flavors:
                        next_neighbours.append(from_node)
                        traced_nodes.append(from_node)

        # BFS iterations
        while (next_neighbours != []):
            for from_node in v.uses_edges:
                for to_node in v.uses_edges[from_node]:
                    if to_node in next_neighbours:
                        if from_node.flavor in self.legal_flavors:
                            next_neighbours_cache.append(from_node)
                            traced_nodes.append(from_node)
            next_neighbours = next_neighbours_cache
            next_neighbours_cache = []

        self.logger.info("The traced, relevant nodes include:")
        self.logger.info(traced_nodes)

        # 2. Get the structure of these functions (which classes/files they are in)
        #    in the defines_edges
        new_defines_edges = {}
        next_neighbours = traced_nodes
        next_neighbours_cache = []

        while (next_neighbours != []):
            for from_node in v.defines_edges:
                for to_node in v.defines_edges[from_node]:
                    if to_node in next_neighbours:
                        if from_node not in new_defines_edges:
                            new_defines_edges[from_node] = set()
                            new_defines_edges[from_node].add(to_node)
                        else:
                            new_defines_edges[from_node].add(to_node)
                        next_neighbours_cache.append(from_node)
            next_neighbours = next_neighbours_cache
            next_neighbours_cache = []

        self.logger.info("The relationship between function nodes and their definition (defines_edges) include:")           
        self.logger.info(new_defines_edges)

        defines_edges_list = []

        # Change everything in the dictionary to anytree AnyNode type
        for key, value in new_defines_edges.items():
            entry = self.convert_node(key)
            for to_node in value:
                to_node_Anynoe = self.convert_node(to_node)
                to_node_Anynoe.parent = entry
            defines_edges_list.append(entry)

        # 3. Iterate through each Node in the list
        #    In each iteration, iterate through the rest of the list
        #    Connect any parent and child that appear
        #    Record the index of entries that are connected
        i = 0
        del_index = []
        for entry in defines_edges_list:
            for other_entry in defines_edges_list:
                if other_entry == entry:
                    continue
                for node in PreOrderIter(other_entry):
                    if node.name == entry.name:
                        for child in entry.children:
                            # This methods allows such that if a further connection
                            # is made between child and some other node,
                            # then the connection is directly retained to this other_entry
                            child.parent = node
                        
                        # It could be possible that entry has already been connected
                        # to some other other_entry.node
                        # Thus we need to check if i is already in the del_index
                        if i not in del_index:
                            del_index.append(i)
            i += 1

        self.logger.debug("defines_edges_list is now {}".format(defines_edges_list))
        self.logger.debug("del_index list is now {}".format(del_index))

        # Sort the indices first in decreasing order so that pop works correctly
        del_index = sorted(del_index, reverse=True)
        for index in del_index:
            if index >= len(defines_edges_list):
                self.logger.critical(f"index {index} is greater than the length of defines_edges_list of length {len(defines_edges_list)}")
            defines_edges_list.pop(index)

        exporter = JsonExporter(indent=2)
        for entry in defines_edges_list:
            self.logger.info(exporter.export(entry))

        # 4. By this point, everything except directory structure has been taken care of
        #    Take care of the directory sturcture
        root = AnyNode()
        for entry in defines_edges_list:
            file_path = entry.code_file
            head = file_path
            tail = None
            # Get all the sub_directories between `workspace` and current `entry.code_file`
            sub_dir = []
            while not os.path.samefile(head, self.workspace):
                head, tail = os.path.split(head)

                # If it is the last bit (the *.py part), then neglect
                if ".py" in tail:
                    continue

                self.logger.debug(f"appending {tail} to the sub_dir list")
                sub_dir.append(tail)

            sub_dir.reverse()
            current_node = root
            for each_dir in sub_dir:
                child_exists = False
                for child in current_node.children:
                    if hasattr(child, 'directory') and child.directory == each_dir:
                        child_exists = True
                        break
                
                # If we found a child with the same (sub)-directory info
                # continue searching by inspecting its children
                if child_exists:
                    current_node = child
                    continue

                # Else, we need to create a new directory node to attach to `current_node`
                each_dir_node = AnyNode(directory=each_dir, parent=current_node)
                current_node = each_dir_node

            # After we finish constructing all intermediate (sub)-directory nodes,
            # attach our main node to the last (sub)-directory node
            entry.parent = current_node

        # A final processing:
        # Traverse the tree, for any "FUNCTION"-natured node,
        # see if any parent is a "CLASS",
        # If so, delete any arguments named "self" in it
        for node in PreOrderIter(root):
            if hasattr(node, "nature") and node.nature == "FUNCTION":
                found = False
                inter_parent = node
                while inter_parent != root:
                    if hasattr(inter_parent, "nature") and inter_parent.nature == "CLASS":
                        found = True
                        break
                    inter_parent = inter_parent.parent
                if found:
                    if "self" in node.args:
                        # new_args = node.args
                        # new_args.remove("self")
                        # node.args = new_args
                        node.args.remove("self")

        self.result_json = exporter.export(root)
        self.logger.info(self.result_json)
        return self.result_json

    def convert_node(self, node):
        if node.flavor == Flavor.CLASS:        
            entry = AnyNode(nature="CLASS", code_file=node.filename, name=node.name, line_nb=node.ast_node.lineno)
            return entry
        # TODO: check if these are the sufficient/necessary flavors
        # Process all functions
        elif node.flavor in [Flavor.FUNCTION, Flavor.METHOD, Flavor.CLASSMETHOD, Flavor.STATICMETHOD]:
            # NOTE: if the AST node is not FunctionDef, then need to figure out how to retrieve argument name
            #       for now, assume the AST node is FunctionDef
            # self.logger.debug(f"the AST node for function is {node.ast_node}")
            arguments = node.ast_node.args
            # NOTE: we ignore `posonlyargs` for now
            anynode_args = []
            for arg in arguments.posonlyargs + arguments.args:
                anynode_args.append(arg.arg)

            # Append all the argument names so that they can be used in pop-up windows
            entry = AnyNode(nature="FUNCTION", code_file=node.filename, name=node.name, line_nb=node.ast_node.lineno, args=anynode_args)
            return entry
        elif node.flavor == Flavor.MODULE:
            entry = AnyNode(nature="MODULE", code_file=node.filename, name=node.filename.split("/")[-1])
            return entry
        else:
            # TODO finish this error & handling
            raise TypeError("node.flavor beyond those that can be processed. The ones that can be processed include:")

# input for function_trace.py
def run(args): 
    workspace = args.workspace
    dir_name = os.path.join(workspace, ".vscode", "tool_json_files")
    json_file_path = os.path.join(workspace, ".vscode", "tool_json_files", "testable_functions.json")
    ft = Function_Tracer(workspace)
    ft.run()
    Path(dir_name).mkdir(parents=True, exist_ok=True)
    with open(json_file_path, "w") as write_file:
        write_file.write(ft.result_json)

def main():
    parser=argparse.ArgumentParser(description="schema")
    # arguments for file
    parser.add_argument("-w",help="workspace" ,dest="workspace", type=str, required=True)
    parser.set_defaults(func=run)
    args=parser.parse_args()
    args.func(args)

if __name__=="__main__":
	main()