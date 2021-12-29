from glob import glob
from typing import List, Union
import logging

from .analyzer import CallGraphVisitor


def pyan_trace_functions(
    filenames: Union[List[str], str] = "**/*.py",
    root: str = None,
    function: Union[str, None] = None,
    namespace: Union[str, None] = None,
    max_iter: int = 1000,
):
    """
    create callgraph based on static code analysis

    Args:
        filenames: glob pattern or list of glob patterns
            to identify filenames to parse (`**` for multiple directories)
            example: **/*.py for all python files
        root: path to known root directory at which package root sits. Defaults to None, i.e. it will be inferred.
        function: if defined, function name to filter for, e.g. "my_module.my_function"
            to only include calls that are related to `my_function`
        namespace: if defined, namespace to filter for, e.g. "my_module", it is highly
            recommended to define this filter
        max_iter: maximum number of iterations for filtering. Defaults to 1000.

    Returns:
        A list of lists consisting of traced function name, filename, and line number
    """
    if isinstance(filenames, str):
        filenames = [filenames]
    filenames = [fn2 for fn in filenames for fn2 in glob(fn, recursive=True)]
    logger = logging.getLogger(__name__)
    # logging.basicConfig(level=logging.DEBUG)
    logger.info(f"filenames computed to be {filenames}")


    v = CallGraphVisitor(filenames, root=root)
    # print(f"uses_edges traced {v.uses_edges}")
    if function or namespace:
        if function:
            function_name = function.split(".")[-1]
            function_namespace = ".".join(function.split(".")[:-1])
            node = v.get_node(function_namespace, function_name)
        else:
            node = None
        v.filter(node=node, namespace=namespace, max_iter=max_iter)

    logger.info(f"uses_edges traced {v.uses_edges}")

    # Turn the dictionary (representing a graph) to a list of relevant functions

    traced_nodes = []
    for from_node in v.uses_edges:
        for to_node in v.uses_edges[from_node]:
            if to_node not in traced_nodes:
                traced_nodes.append(to_node)
        if from_node not in traced_nodes:
            traced_nodes.append(from_node)

    # Return the following desired information: (1) function name;
    # (2) function definition file; (3) function definition line
    res = []
    for node in traced_nodes:
        res.append([node.name, node.filename, node.ast_node.lineno])

    return res