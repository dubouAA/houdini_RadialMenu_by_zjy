try:import hou
except:pass
def zjy_create_node_from_shelfs_tool(kwargs,tool_name):
    kwargs = kwargs
    exec(hou.shelves.tool(tool_name).script())
