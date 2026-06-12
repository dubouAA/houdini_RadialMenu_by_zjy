from builtins import zip
from builtins import range
from past.builtins import basestring
import hou
import shlex
import toolprompts
import quickplanes
import insertionpointutils as ip
import json
try:
    from ZJYRadialMenu.Zjy_RadialMenu import *
    # import Zjy_radialmenu
except: print('import RadialMenu error')

def safe_reload(module):
    """ Reloads the given module when the HOUDINI_PYTHON_DEVELOPMENT
        environment is set to 1
    """
    import os

    if (os.environ.get("HOUDINI_PYTHON_DEVELOPMENT") == "1"
        # For backward compatibility.
        or os.environ.get("PYPANEL_DEV") == "1"):

        from hutil import py23
        py23.reload(module)

def dataTree(tree_type):
    """ Returns an existing open Data Tree pane if there is one. If a tree
        type is provided, the Data Tree must be set to that tree type to be
        acceptable.
    """
    # Create a list of all data tree panes.
    primarypane = None
    panes = []
    index = 0
    pane = hou.ui.paneTabOfType(hou.paneTabType.DataTree, index)
    while pane is not None:
        panes.append(pane)
        index += 1
        pane = hou.ui.paneTabOfType(hou.paneTabType.DataTree, index)

    # Ideally find a data tree that is the current tab in its pane and is
    # already set to the desired tree type, or has no tree type set.
    if not primarypane:
        for pane in panes:
            if not pane.isCurrentTab():
                continue
            if not tree_type or not pane.treeType() or \
                    tree_type == pane.treeType():
                primarypane = pane
                break

    # Next best is a data tree tab that is current in its pane, but with
    # the wrong tree type.
    if not primarypane:
        for pane in panes:
            if not pane.isCurrentTab():
                continue
            primarypane = pane
            break

    # Next best case is to find a data tree that is not current but is
    # of the right tree type.
    if not primarypane:
        for pane in panes:
            if not tree_type or not pane.treeType() or \
                    tree_type == pane.treeType():
                primarypane = pane
                break

    # Last chance. Just pick any data tree pane.
    if not primarypane and panes:
        primarypane = panes[0]

    # Make the data tree tab current if it isn't current already.
    if primarypane and not primarypane.isCurrentTab():
        primarypane.setIsCurrentTab()
    # Set the data tree type if a specific type was requested.
    if primarypane and tree_type and primarypane.treeType() != tree_type:
        primarypane.setTreeType(tree_type)

    if primarypane is not None:
        return primarypane
    else:
        raise hou.NotAvailable("No data tree is currently open.")

def sceneViewer(can_switch_tabs=True,
                must_be_current=True,
                allow_pinned_to_network=None):
    """
    Returns an existing open Scene Viewer pane if there is one. A
    Context viewer is also acceptable if no dedicated scene viewer
    is found. An existing pane tab will be made current if necessary.

    :param can_switch_tabs: set this to True if you want to switch the current pane tab to the scene viewer,
        if any exists, in case it was not already the active pane
    :type can_switch_tabs: bool
    :param must_be_current: if must_be_current is True, this method will raise hou.NotAvailable if no scene viewer is found that
        is also the current tab; set must_be_current to False if you wish to return a scene viewer if any exists,
        no matter if it a current tab or not
    :type must_be_current: bool
    :param allow_pinned_to_network: if allow_pinned_to_network is not None, this method will raise hou.NotAvailable if no scene viewer is found that
        is pinned to some network other than the one specified.
    :type allow_pinned_to_network: hou.Node
    :return: scene viewer pane tab or raises hou.NotAvailable if no scene viewer is available
        
    :rtype: hou.PaneTab
    """
    # Find the first scene viewer tab which is the current tab in its pane.
    index = 0
    primarypane = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer, index)
    while primarypane is not None and \
            (not primarypane.isCurrentTab() or
             (allow_pinned_to_network is not None and
              primarypane.isPin() and
              primarypane.pwd() != allow_pinned_to_network)):
        index += 1
        primarypane = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer, index)

    # If we don't find a scene viewer that is a current tab, look for a
    # context viewer in a scene viewer context as the current tab.
    if primarypane is None:
        index = 0
        primarypane = hou.ui.paneTabOfType(hou.paneTabType.ContextViewer, index)
        while primarypane is not None and \
                (not primarypane.isCurrentTab() or
                 primarypane.sceneViewer() is None or
                 (allow_pinned_to_network is not None and
                  primarypane.isPin() and
                  primarypane.pwd() != allow_pinned_to_network)):
            index += 1
            primarypane = hou.ui.paneTabOfType(hou.paneTabType.ContextViewer, index)

        if primarypane is not None:
            primarypane = primarypane.sceneViewer()

    # If we don't find a scene viewer in a context viewer that is a current
    # tab, find any scene viewer, and make it the current tab in its pane.
    if primarypane is None and (can_switch_tabs or not must_be_current):
        index = 0
        primarypane = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer, index)
        while primarypane is not None and \
                (allow_pinned_to_network is not None and
                 primarypane.isPin() and
                 primarypane.pwd() != allow_pinned_to_network):
            index += 1
            primarypane = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer, index)
        if can_switch_tabs and primarypane is not None:
            primarypane.setIsCurrentTab()

    # Finally, if we still haven't found a scene viewer, find any scene
    # viewer in a context viewer and make it the current tab in its pane.
    if primarypane is None and (can_switch_tabs or not must_be_current):
        index = 0
        primarypane = hou.ui.paneTabOfType(hou.paneTabType.ContextViewer, index)
        while primarypane is not None and \
                primarypane.sceneViewer() is not None and \
                (allow_pinned_to_network is not None and
                 primarypane.isPin() and
                 primarypane.pwd() != allow_pinned_to_network):
            index += 1
            primarypane = hou.ui.paneTabOfType(hou.paneTabType.ContextViewer, index)
        if primarypane is not None and primarypane.sceneViewer() is not None:
            if can_switch_tabs:
                primarypane.setIsCurrentTab()
            primarypane = primarypane.sceneViewer()

    if primarypane is not None:
        return primarypane
    else:
        raise hou.NotAvailable("No scene viewer is currently open.")

def compositorViewer():
    """ Returns an existing open Compositing Viewer pane if there is one. A
        Context viewer is also acceptable is no dedicated compositing viewer
        is found.
    """
    # Find the first compositor viewer tab which is current tab in its pane.
    index = 0
    primarypane = hou.ui.paneTabOfType(hou.paneTabType.CompositorViewer, index)
    while primarypane is not None and not primarypane.isCurrentTab():
        index += 1
        primarypane = hou.ui.paneTabOfType(
            hou.paneTabType.CompositorViewer, index)

    # If we don't find a compositor viewer that is a current tab, look for a
    # context viewer in a compositor viewer context as the current tab.
    if primarypane is None:
        index = 0
        primarypane = hou.ui.paneTabOfType(hou.paneTabType.ContextViewer, index)
        while primarypane is not None and \
                (not primarypane.isCurrentTab() or \
                 primarypane.compositorViewer() is None):
            index += 1
            primarypane = hou.ui.paneTabOfType(
                hou.paneTabType.CompositorViewer, index)

        if primarypane is not None:
            primarypane = primarypane.compositorViewer()

    # If we don't find a compositor viewer in a context viewer that is a current
    # tab, find any compositor viewer, and make it the current tab in its pane.
    if primarypane is None:
        primarypane = hou.ui.paneTabOfType(hou.paneTabType.CompositorViewer)
        if primarypane is not None:
            primarypane.setIsCurrentTab()

    # Finally, if we still haven't found a compositor viewer, find any
    # compositor viewer in a context viewer and make it the current tab in
    # its pane.
    if primarypane is None:
        primarypane = hou.ui.paneTabOfType(hou.paneTabType.ContextViewer)
        if primarypane is not None and \
                primarypane.compositorViewer() is not None:
            primarypane.setIsCurrentTab()
            primarypane = primarypane.compositorViewer()

    if primarypane is not None:
        return primarypane
    else:
        raise hou.NotAvailable("No compositor viewer is currently open.")

def networkEditor():
    """ Returns an existing open Network Editor pane if there is one.
    """
    # Find the first network editor tab which is the current tab in its pane.
    index = 0
    primarypane = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor, index)
    while primarypane is not None and not primarypane.isCurrentTab():
        index += 1
        primarypane = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor, index)

    # If we don't find a network editor that is a current tab, find any network
    # editor, and make it the current tab in its pane.
    if primarypane is None:
        primarypane = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        if primarypane is not None:
            primarypane.setIsCurrentTab()

    if primarypane is not None:
        return primarypane
    else:
        raise hou.NotAvailable("No network editor is currently open.")

def activePane(scriptargs):
    """ Returns the current active pane. If the current tool was launched
        from a Tab menu, the "pane" scriptarg will be set, and indicates the
        active pane. Otherwise the tool was launched from the shelf and
        we have to look for an open viewer pane of the right type for the
        running tool.
    """
    if "pane" in scriptargs and scriptargs["pane"] is not None:
        pane = scriptargs["pane"]
        if isinstance(pane, hou.ContextViewer):
            if pane.sceneViewer() is not None:
                pane = pane.sceneViewer()
    else:
        runningtool = hou.shelves.runningTool()
        pane = sceneViewer()
    return pane

def activeCompositorPane(scriptargs):
    if "pane" in scriptargs and scriptargs["pane"] is not None:
        pane = scriptargs["pane"]
        if isinstance(pane, hou.ContextViewer) and \
            pane.compositorViewer() is not None:
            pane = pane.compositorViewer()
    else:
        pane = compositorViewer()
    return pane

def homeToSelectionNetworkEditorsFor(node):
    """ Homes to their selection all network editors to that are showing the
    network that contains node. """
    # Find all network editors in that are showing this node.
    index = 0
    editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor, index)
    while editor is not None:
        import nodegraphview

        if node.parent() == editor.pwd():
            picked_items = editor.pwd().selectedItems()
            nodegraphview.ensureItemsAreVisible(editor, picked_items)

        index += 1
        editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor, index)

def homeToItems(items):
    """ Homes to their selection all network editors that are showing the
        network that contains items. Assumes that all items have the same
        parent."""
    if not items:
        return
    # Find all network editors in that are showing this node.
    index = 0
    editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor, index)
    while editor is not None:
        import nodegraphview

        if items[0].parent() == editor.pwd():
            nodegraphview.ensureItemsAreVisible(editor, items, immediate=False)

        index += 1
        editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor, index)

def selectionPrompt(nodetypecategory, multisel = True,
                    whichprompt = 0):
    """ Generates a generic selection prompt string when no specific prompt
        string is available in the toolprompts module.
    """
    # Look for the requested prompt string in the tool prompt dictionary.
    runningtool = hou.shelves.runningTool()
    if runningtool is not None:
        if runningtool.name() in toolprompts.thePrompts:
            prompts = toolprompts.thePrompts[runningtool.name()]
            if len(prompts) > whichprompt:
                return prompts[whichprompt]
    # If we didn't find a specific prompt, generate a generic prompt.
    # First we need to figure out what we are selecting.
    if nodetypecategory is None:
        nodetype = "position"
        adds = multisel
    elif nodetypecategory == hou.objNodeTypeCategory():
        nodetype = "object"
        adds = multisel
    elif nodetypecategory == hou.sopNodeTypeCategory():
        nodetype = "geometry"
        adds = False
    elif nodetypecategory == hou.dopNodeTypeCategory():
        nodetype = "dynamic object"
        adds = multisel
    else:
        nodetype = "component"
        adds = multisel
    if adds:
        nodetype += "s"
    # Assemble the full prompt string
    prompt = "Select " + nodetype
    if runningtool is not None:
        prompt += " for " + runningtool.label()
    prompt += "."
    # For position selection, add the hint to hold Shift to elevate.
    if nodetypecategory is None:
        prompt += " Hold Shift to move off the construction plane."
    # Don't need to hit enter to accept if we are selecting a single position.
    if nodetypecategory is not None or multisel:
        prompt += " Press Enter to accept selection."
    return prompt

def replaceOutputConnections(olditem, oldoutputindex, newnode, newoutputindex):
    """ Stick the new node between the input node and all nodes it
        is connected to (insert operation).
    """
    for connection in olditem.outputConnections():
        if connection.outputIndex() == oldoutputindex:
            connection.outputItem().setInput(connection.inputIndex(),
                                             newnode, newoutputindex)

def replaceInputConnections(olditem, oldinputindex, newnode, newinputindex):
    """ Stick the new node between the output node and the node it
        is connected to (insert operation). Note there can be only one.
    """
    for connection in olditem.inputConnections():
        if connection.inputIndex() == oldinputindex:
            newnode.setInput(newinputindex, connection.inputItem(),
                             connection.inputItemOutputIndex())

def getBestConnector(innode, outidx, outnode, inidx, defaultidx):
    if isinstance(innode, hou.VopNode) and isinstance(outnode, hou.VopNode):
        if inidx < 0:
            connections = outnode.inputConnections()
            inputs = outnode.inputIndexOrder()
            for testidx in inputs:
                # Skip over any input that is already connected.
                if any([conn.inputIndex() == testidx for conn in connections]):
                    continue
                if outnode.isInputCompatible(testidx, innode, outidx, False):
                    return testidx
            for testidx in inputs:
                # Skip over any input that is already connected.
                if any([conn.inputIndex() == testidx for conn in connections]):
                    continue
                if outnode.isInputCompatible(testidx, innode, outidx, True):
                    return testidx
        elif outidx < 0:
            if innode.type().category() == hou.vopNodeTypeCategory():
                n = len(innode.outputNames())
            else:
                n = innode.type().maxNumOutputs()

            outputs = list(range(0, n))
            for testidx in outputs:
                if outnode.isInputCompatible(inidx, innode, testidx, False):
                    return testidx
            for testidx in outputs:
                if outnode.isInputCompatible(inidx, innode, testidx, True):
                    return testidx

    if isinstance(innode, hou.CopNode) and isinstance(outnode, hou.CopNode):
        if inidx < 0:
            connections = outnode.inputConnections()
            inputs = list(range(0, outnode.type().maxNumInputs()))
            for testidx in inputs:
                # Skip over any input that is already connected.
                if any([conn.inputIndex() == testidx for conn in connections]):
                    continue
                if outnode.isInputCompatible(testidx, innode, outidx, True):
                    return testidx
        elif outidx < 0:
            n = innode.type().maxNumOutputs()

            outputs = list(range(0, n))
            for testidx in outputs:
                if outnode.isInputCompatible(inidx, innode, testidx, True):
                    return testidx

    return defaultidx

def connectMultiInputsAndOutputs(newnode, branch, inputs, outputs):
    """ Wire the network so that new node connects to the provided inputs
        and outputs. This isn't always possible, but get as close as we can.
        If branch is false, all of the inputs outputs will be made
        newnode's outputs. Both inputs and outputs are optional.
    """
    # Hook the new node up to the input item(s).
    if inputs and newnode.type().maxNumInputs() > 0:
        # If we are not branching, and we have a single input, we want to
        # wire all outputs of that input to the output of the new node.
        # This inserts a node between a node and all of its outputs.
        if not branch and not outputs and \
           len(inputs) == 1 and newnode.type().maxNumOutputs() > 0:
            replaceOutputConnections(inputs[0][0], inputs[0][1], newnode, 0)
        # If we have more than one input, plug as many as we can into the
        # new node.
        for i in range(0, min(newnode.type().maxNumInputs(), len(inputs))):
            if len(inputs[i]) > 2:
                idx = inputs[i][2]
            else:
                idx = getBestConnector(inputs[i][0], inputs[i][1],
                                       newnode, -1, i)
            # Avoid plugging in if requested output on input is out
            # of its range.
            if not hasattr(inputs[i][0], 'outputConnectors') or \
               len(inputs[i][0].outputConnectors()) > inputs[i][1]:
                newnode.setInput(idx, inputs[i][0], inputs[i][1])

    # Hook the new node up to the output item(s).
    if outputs and newnode.type().maxNumOutputs() > 0:
        # If we are not branching, and we have a single output, we want to
        # wire the input of that output to the input of the new node.
        # This inserts a node between a node and one of its inputs.
        if not branch and not inputs and \
           len(outputs) == 1 and newnode.type().maxNumInputs() >= 0:
            replaceInputConnections(outputs[0][0], outputs[0][1], newnode,
                outputs[0][2] if len(outputs[0]) > 2 else 0)
        # Wire all our outputs to the output of the new node. There are no
        # limits on the number of outputs from one input.
        for i in range(0, len(outputs)):
            idx = getBestConnector(newnode, -1, outputs[i][0], outputs[i][1],
                outputs[i][2] if len(outputs[i]) > 2 else 0)
            if outputs[i][1] >= 0:
                outputs[i][0].setInput(outputs[i][1], newnode, idx)
            else:
                outputs[i][0].setNextInput(newnode, idx, True)

def connectInputsAndOutputs(newnode, branch,
        inputitem, outputitem,
        inputindex, outputindex):
    """ Simplified version of connectMultiInputsAndOutputs that takes at
        most a single input and output. Provided for backward compatibility
        with code written before the Multi code was written.
    """
    inputs = []
    outputs = []
    if inputitem is not None:
        inputs.append((inputitem, outputindex))
    if outputitem is not None:
        outputs.append((outputitem, inputindex))
    connectMultiInputsAndOutputs(newnode, branch, inputs, outputs)

def nodeTypeNameBase(node):
    """ Returns the node type base name (stripped of namespace or version).
    """
    # nameComponents() returns a tuple (scopeop, namespace, basename, version)
    return node.type().nameComponents()[2] if node is not None else None

def nodeTypeNameVersion(node):
    """ Returns the node type version component.
    """
    # nameComponents() returns a tuple (scopeop, namespace, basename, version)
    return node.type().nameComponents()[3] if node is not None else None

def nodeTypeNameMatches(node, matchtype):
    """ Returns true if the node's type base name matches the given type.
        A matchtype of None is assumed to match any node.
    """
    return matchtype is None or node.type().name() == matchtype

def nodeTypeBaseNameMatches(node, matchtype):
    """ Returns true if the node's type base name matches the given type.
        A matchtype of None is assumed to match any node.
    """
    return matchtype is None or nodeTypeNameBase(node) == matchtype

def nodeTypeNameComponentsMatch(node, matchtype):
    """ Returns true if the node's type name components matches the given type.
        The components present in matchtype are checked against the node's type,
        and this function returns true if they do match.  Eg,
        matchtype 'hda' will match 'hda', 'hda::1.5', 'userX::hda', etc
        matchtype 'userX::hda' will match 'userX::hda', 'userX::hda::1.5', etc
        matchtype 'hda::1.5' will match 'hda::1.5', 'userX::hda::1.5', etc
        matchtype '::hda' will match 'hda' and 'hda::1.5', but not 'userX::hda'
        matchtype 'hda::' will match 'hda' and 'userX::hda' but not 'hda::1.5'
        A matchtype of None is assumed to match any node.
    """
    if matchtype is None:
        return True

    # get the node type component tuples: (scope, namespace, basename, version)
    test   = node.type().nameComponents()
    target = hou.hda.componentsFromFullNodeTypeName(matchtype)

    # check if the the node must be in a global namesapce (eg '::hda')
    if matchtype.startswith('::') and test[1] != '':
        return False
    # check if the the node must versionless (eg 'hda::')
    if matchtype.endswith('::') and test[3] != '':
        return False
    # test each non-empty component of matchtype against the node's counterpart
    for i in range(4):
        if target[i] != '' and target[i] != test[i]:
            return False
    return True

def __nodeMatches(node, matchtype, parmlist, basetypematch=False):
    """ True if node is of type matchtype and the parmlist dictionary
        matches our contents.
        If basetypematch is true, only the node type's base name is checked,
        ie, node type's namespace and version components are ignored
        when testing against the matchtype (eg, matchtype 'hda' will match
        node types 'hda', 'hda::1.5' and 'userx::hda', etc). Otherwise,
        the node type full name must match exactly the matchtype string.
    """

    # Trivial failure for None nodes
    if node is None:
        return False

    # Ensure the type matches (do either partial or exact match).
    if basetypematch and not nodeTypeBaseNameMatches(node, matchtype):
        return False
    if not basetypematch and not nodeTypeNameMatches(node, matchtype):
        return False

    # Validate our chosen node.
    valid = True
    for (parmname, parmvalue) in list(parmlist.items()):
        parm = node.parm(parmname)
        if parm is None:
            # Missing specified parameter
            valid = False
        elif parm.eval() != parmvalue and parm.evalAsString() != parmvalue:
            # Not matching parameter (either as raw or string value)
            valid = False
    return valid

def findConnectionChainToInputNode(startnode, endnode):
    """ Finds a chain of hou.Connections that lead to endnode.

        Returns None if no such chain exists.
    """
    chains = []
    findConnectedNodes(startnode, 'input',
                       match_method=lambda n: n == endnode,
                       connection_chains=chains, all_paths=False)

    if len(chains) == 0:
        return None
    return chains[0]

def findAllConnectionChainsToInputNode(startnode, endnode):
    """ Finds all chains of hou.Connections that lead to endnode.

        Returns an empty list if no such chain exists.
    """
    chains = []
    findConnectedNodes(startnode, 'input',
                       match_method=lambda n: n == endnode,
                       connection_chains=chains, all_paths=True)
    return chains

def findConnectionChainToOutputNode(startnode, endnode):
    """ Finds a chain of hou.Connections that lead to endnode.

        Returns None if no such chain exists.
    """
    chains = []
    findConnectedNodes(startnode, 'output',
                       match_method=lambda n: n == endnode,
                       connection_chains=chains, all_paths=False)

    if len(chains) == 0:
        return None
    return chains[0]

def findAllConnectionChainsToOutputNode(startnode, endnode):
    """ Finds all chains of hou.Connections that lead to endnode.

        Returns an empty list if no such chain exists.
    """
    chains = []
    findConnectedNodes(startnode, 'output',
                       match_method=lambda n: n == endnode,
                       connection_chains=chains, all_paths=True)
    return chains

def findConnectedNodes(startnode, connection_type, match_method,
                       find_first=False, seennodes=None, includeme=False,
                       incoming_conn=None, connection_chains=None, all_paths=False,
                       connector_index=None, stop_method=None):
    """ Finds all nodes that are connected to startnode for which match_method
        returns True. Searches either inputs or outputs, depending on the value
        of connection_type (either 'input' or 'output').

        match_method may be a method taking a hou.Node as it's argument.
        In that case only nodes for which it returns True are matched.

        If connection_chains is a list, for each node it'll be populated with
        the hou.NodeConnections by which the node was found. If additionally
        all_paths is True, all paths to the node will be returned, so nodes
        may appear multiple times in the returned list.

        If find_first is True, the method will exit early as soon as a matching
        node is found. Having both find_first and all_paths True will raise
        a hou.Error.

        stop_method may be a method taking a hou.Node and a hou.NodeConnection
        by which that node was reached. If it returns True, the node and
        further connected nodes will be ignored.
    """

    nodes = []

    if all_paths and find_first:
        raise hou.Error("find_first is incompatible with all_paths")

    if all_paths and connection_chains is None:
        raise hou.Error("if all_paths is True, connection_chains must be a list")

    if startnode is None:
        return []

    if includeme and (match_method is None or match_method(startnode)):
        nodes.append(startnode)
        if stop_method is not None and stop_method(startnode, None):
            return nodes
        if connection_chains is not None:
            connection_chains.append([incoming_conn])
        if find_first:
            return nodes

    if seennodes is None:
        seennodes = set()
    elif startnode in seennodes:
        # More than one way to this node, so don't need to search
        # again.
        return []

    # Add to the list of seen nodes
    if not all_paths:
        seennodes.add(startnode)

    connectors = startnode.inputConnectors() \
        if connection_type == 'input' \
        else startnode.outputConnectors()

    for i, connections in enumerate(connectors):
        if connector_index is not None and i != connector_index:
            continue

        for conn in connections:
            connected_node = conn.inputNode() \
                if connection_type == 'input' \
                else conn.outputNode()

            if stop_method is not None \
                    and stop_method(connected_node, conn):
                continue

            # If connection_chains was passed in, we also need to query chains
            # to our recursively connected nodes. So we pass in the sub_chains
            # list to the recursive findConnectedNodes call.
            sub_chains = None if connection_chains is None else []
            sub_nodes = findConnectedNodes(
                connected_node, connection_type, match_method,
                seennodes=seennodes,
                includeme=True, incoming_conn=conn,
                connection_chains=sub_chains,
                all_paths=all_paths,
                stop_method=stop_method)

            if connection_chains is not None:
                # In addition to searching for nodes we look for connection
                # paths to them and add them to connection_chains.
                for j, (sub_node, sub_chain) in enumerate(zip(sub_nodes, sub_chains)):
                    if not all_paths and sub_node in nodes:
                        # We're not looking for all possible paths and we've
                        # already found sub_node, so we don't add it again.
                        continue
                    if incoming_conn is not None:
                        # prepend the connection that led to us to the sub_chain
                        sub_chains[j].insert(0, incoming_conn)
                    nodes.append(sub_node)
                    # Add our chain to the passed in list of chains
                    connection_chains.append(sub_chain)
            else:
                nodes += sub_nodes

            if find_first and len(nodes):
                return nodes

    return nodes

# TODO: implement in terms of findConnectedNodes()
def findAllInputNodesOfTypeWithParms(endnode, nodetype, parmlist,
                                includeme=False, findfirst=False, seennodes=None,
                                basetypematch=False):
    """Finds all nodes that are an ancestor of endnode, match
        nodetype, and have the parameters & value pairs listed in the
        parmlist dictionary.
        If basetypematch is true, only the node type's base name is checked,
        ie, node type's namespace and version components are ignored
        when testing against the matchtype (eg, matchtype 'hda' will match
        node types 'hda', 'hda::1.5' and 'userx::hda', etc). Otherwise,
        the node type name must match exactly the matchtype string.
    """
    result = []

    if endnode is None:
        return []

    if includeme and __nodeMatches(endnode, nodetype, parmlist,
                                   basetypematch):
        result.append(endnode)
        if findfirst:
            return result

    if seennodes is None:
        seennodes = set()
    elif endnode in seennodes:
        # More than one way to this node, so don't need to search
        # again.
        return []

    # Add to the list of seen nodes
    seennodes.add(endnode)

    for inputnode in endnode.inputs():
        nodes = findAllInputNodesOfTypeWithParms(
            inputnode, nodetype, parmlist,
            includeme=True, seennodes=seennodes,
            basetypematch=basetypematch)

        result += nodes

        if findfirst and len(result):
            return result

    return result

def findInputNodeOfTypeWithParms(endnode, nodetype, parmlist,
                                includeme=False, seennodes=None,
                                basetypematch=False):
    """Finds any nodes that are an ancestor of endnode, match
        nodetype, and have the parameters & value pairs listed in the
        parmlist dictionary.
        If basetypematch is true, only the node type's base name is checked,
        ie, node type's namespace and version components are ignored
        when testing against the matchtype (eg, matchtype 'hda' will match
        node types 'hda', 'hda::1.5' and 'userx::hda', etc). Otherwise,
        the node type name must match exactly the matchtype string.
    """

    list = findAllInputNodesOfTypeWithParms(endnode, nodetype, parmlist,
                                            includeme=includeme, findfirst=True,
                                            seennodes=seennodes,
                                            basetypematch=basetypematch)

    if len(list) > 0:
        return list[0]
    return None

def findGreatestCommonDescendent(endnode, searchnodes, seennodes=None):
    """ Starting from end node and heading up the input chain
        locate the first node that doesn't have all of searchnodes
        on the same input wire.
    """

    if endnode is None:
        return None

    if seennodes is None:
        seennodes = set()
    elif endnode in seennodes:
        # More than one way to this node, so don't need to search
        # again.
        return None
    # Add to the list of seen nodes
    seennodes.add(endnode)

    # Search our inputs for any for which all of the searchnodes
    # belong.  That input is a greater common descendant.
    for input in endnode.inputs():
        if input is None:
            continue
        missingnode = False
        for search in searchnodes:
            if not findInputNode(input, search):
                missingnode = True
                break
        if not missingnode:
            # this is a GCD
            return findGreatestCommonDescendent(input, searchnodes, seennodes=seennodes)

    # None of our inputs suffice, implying at least one searchnode can
    # only be reached by another input.  This is then the GCD
    return endnode

def findInputNode(endnode, searchnode, seennodes=None):
    """ This function searches the endnode's hierarchy to find if the
        given search node is connected
    """
    if endnode == searchnode:
        return True
    if searchnode is None:
        return False
    if endnode is None:
        return False

    if seennodes is None:
        seennodes = set()
    elif endnode in seennodes:
        # More than one way to this node, so don't need to search
        # again.
        return False

    # Add to the list of seen nodes
    seennodes.add(endnode)

    for inputnode in endnode.inputs():
        if inputnode == searchnode:
            return True
        else:
            if findInputNode(inputnode, searchnode, seennodes=seennodes):
                return True
    return False

def findInputNodeOfType(endnode, nodetype, includeme=False, seennodes=None,
                        basetypematch=False):
    """ This function does a depth first traversal of the node input hierarchy
        to find the first node of a particular type.
        If basetypematch is true, only the node type's base name is checked,
        ie, node type's namespace and version components are ignored
        when testing against the matchtype (eg, matchtype 'hda' will match
        node types 'hda', 'hda::1.5' and 'userx::hda', etc). Otherwise,
        the node type name must match exactly the matchtype string.
    """

    # We can simply pass down an empty parmlist for comparison.
    parmlist = {}
    return findInputNodeOfTypeWithParms(endnode, nodetype, parmlist,
                            includeme=includeme, seennodes=seennodes,
                            basetypematch=basetypematch)

def findInputNodeOfBaseType(endnode, nodetype, includeme=False, seennodes=None):
    """ This function does a depth first traversal of the node input hierarchy
        to find the first node whose type's base name (ie, type name stripped of
        any namespace or version) matches the given type.
    """
    return findInputNodeOfType(endnode, nodetype, includeme, seennodes,
                              basetypematch = True)

def findOutputNodeOfTypeWithParms(startnode, nodetype, parmlist,
                                includeme=False, seennodes=None,
                                basetypematch=False, returnall=False):
    """ Finds any nodes that are a descendant of startnode, match
        nodetype, and have the parameters & value pairs listed in the
        parmlist dictionary.
        If basetypematch is true, only the node type's base name is checked,
        ie, node type's namespace and version components are ignored
        when testing against the matchtype (eg, matchtype 'hda' will match
        node types 'hda', 'hda::1.5' and 'userx::hda', etc). Otherwise,
        the node type name must match exactly the matchtype string.
        If returnall is true, returns a list of all matches in depth
        first order, or an empty list if no matches are found.
    """

    if startnode is None:
        return None

    if includeme and __nodeMatches(startnode, nodetype, parmlist,
                                   basetypematch):
        return startnode

    if seennodes is None:
        seennodes = set()
    elif startnode in seennodes:
        # More than one way to this node, so don't need to search
        # again.
        return None

    # Add to the list of seen nodes
    seennodes.add(startnode)

    nodes = []

    for outputnode in startnode.outputs():
        match = __nodeMatches(outputnode, nodetype, parmlist, basetypematch)

        if match:
            if returnall:
                nodes.append(outputnode)
            else:
                return outputnode

        if not match or returnall:
            node = findOutputNodeOfTypeWithParms(
                outputnode, nodetype, parmlist,
                includeme=False, seennodes=seennodes,
                basetypematch=basetypematch, returnall=returnall)
            if node:
                if returnall:
                    # node is a list here
                    nodes += node
                else:
                    return node

    if returnall:
        return nodes
    else:
        return None

def findOutputNodeOfType(startnode, nodetype, includeme=False, seennodes=None,
                         basetypematch=False, returnall=False):
    """ This function does a depth first traversal of the node output
        hierarchy to find the first node that matches our search.
        If basetypematch is true, only the node type's base name is checked,
        ie, node type's namespace and version components are ignored
        when testing against the matchtype (eg, matchtype 'hda' will match
        node types 'hda', 'hda::1.5' and 'userx::hda', etc). Otherwise,
        the node type name must match exactly the matchtype string.
        If returnall is true, returns a list of all matches in depth
        first order, or an empty list if no matches are found.
    """

    parmlist = {}
    return findOutputNodeOfTypeWithParms(startnode, nodetype, parmlist,
                        includeme=False, seennodes=seennodes,
                        basetypematch=basetypematch, returnall=returnall)

def findOutputNodeOfBaseType(endnode, nodetype, includeme=False,
                             seennodes=None, returnall=False):
    """ This function does a depth first traversal of the node input hierarchy
        to find the first node whose type's base name (ie, type name stripped of
        any namespace or version) matches the given type.
        If returnall is true, returns a list of all matches in depth
        first order, or an empty list if no matches are found.
    """
    return findOutputNodeOfType(endnode, nodetype, includeme, seennodes,
                                basetypematch = True, returnall=returnall)

def findAllChildNodesOfTypeWithParms(parentnode, nodetype, parmlist,
                                 dorecurse=False, findfirst=False,
                                 basetypematch=False):
    """ Returns a list of all nodes contained in parent that match
        the nodetype & parmlist filters.
    """
    result = []

    for child in parentnode.children():
        if __nodeMatches(child, nodetype, parmlist, basetypematch=basetypematch):
            result.append(child)
            if findfirst:
                return result
        # Recurse if needed
        if dorecurse:
            result += findAllChildNodesOfTypeWithParms(child,
                                                        nodetype, parmlist,
                                                        dorecurse=dorecurse,
                                                        findfirst=findfirst,
                                                        basetypematch = basetypematch)
            if findfirst and len(result):
                return result

    return result

def findChildNodeOfTypeWithParms(parentnode, nodetype, parmlist,
                                 dorecurse=False, basetypematch=False):
    """ This function does a search of the node container hierarchy
        (rather than connection hierarchy) searching for a matching
        node type which also has the given parameter list match.
    """
    list = findAllChildNodesOfTypeWithParms(parentnode, nodetype, parmlist,
                                    dorecurse=dorecurse, findfirst=True,
                                    basetypematch=basetypematch)

    if len(list) > 0:
        return list[0]
    return None

def findChildNodeOfType(parentnode, nodetype, dorecurse=False, basetypematch=False):
    """ This function does a search of the node container hierarchy
        (rather than connection hierarchy) searching for a matching
        node type.
    """

    parmlist = {}
    return findChildNodeOfTypeWithParms(parentnode, nodetype, parmlist,
                                    dorecurse=dorecurse, basetypematch=basetypematch)

def findAllChildNodesOfType(parentnode, nodetype, dorecurse=False,
                            findfirst=False, basetypematch=False):
    """ Returns a list of all child nodes that match the given node
        type
    """

    parmlist = {}
    return findAllChildNodesOfTypeWithParms(parentnode, nodetype, parmlist,
                                            dorecurse=dorecurse, findfirst=findfirst,
                                            basetypematch=basetypematch)

def findAncestorOfType(startnode, category, nodetype, basetypematch=False):
    """ Return closest ancestor (or self) of 'startnode' with the specified
        category and type.
    """
    while startnode is not None:
        t = startnode.type()
        if t.category() == category and \
            __nodeMatches(startnode, nodetype, {}, basetypematch):
            return startnode
        startnode = startnode.parent()

def findAncestorOfBaseType(startnode, category, nodetype):
    """ Return closest ancestor (or self) of 'startnode' with the specified
        category and type.
    """
    return findAncestorOfType(startnode, category, nodetype,
                              basetypematch=True)

def chooseNode(possible_nodes, title, message):
    """ Prompts the user to select on of the given nodes. If there is only a
        single node, then that node is automatically returned. The title
        and message parameters determine what will show up in the prompt.
    """
    if len(possible_nodes) > 1:
        chosen_node = _askUserToSelectNode(possible_nodes, title, message)
    else:
        chosen_node = possible_nodes[0]

    return chosen_node

def _askUserToSelectNode(nodes, title, message):
    paths = [single_node.path() for single_node in nodes]

    choice_tuple = hou.ui.selectFromList(paths, exclusive = True,
                                            message = message,
                                            title = title)

    if choice_tuple:
        assert len(choice_tuple) <= 1
        choice = choice_tuple[0]
        return nodes[choice]
    else:
        return None


# Class to collect the orientation information for a node type, consisting of
# the name of the parameter that controls orientation as well as the global
# orientation expected by a default instance of the node type.
class OrientInfo(object):
    def __init__(self, parmname, defaultup=hou.orientUpAxis.Y):
        self.parmname = parmname
        self.defaultup = defaultup

def setUpOrientation(node, parmname, defaultup=hou.orientUpAxis.Y):
    """ Assumes that the default value of the specified parameter in the given
        node corresponds to the orientation specified in defaultup and applies
        the necessary change to convert the node to the current orientation
        mode.
    """
    if not node.type().hasPermanentUserDefaults() and \
                            hou.ui.orientationUpAxis() != defaultup:
        # First handle 'X|Y|Z axis and XY|YZ|ZX plane ordinal menus.
        parm = node.parm(parmname)
        if parm is not None:
            if parm.parmTemplate().type() == hou.parmTemplateType.Menu:
                # A temporary default set by the user must override any auto
                # correction we can do here.
                if parm.hasTemporaryDefaults():
                    return
                mitems = parm.menuItems()
                if 'y' in mitems and 'z' in mitems:
                    # 'y' -> 'z' and 'z' -> 'y'
                    val = parm.evalAsString()
                    if val == 'y':
                        parm.set('z')
                    elif val == 'z':
                        parm.set('y')
                elif 'xy' in mitems and 'zx' in mitems:
                    # 'zx' -> 'xy' and 'xy' -> 'zx'
                    val = parm.evalAsString()
                    if val == 'zx':
                        parm.set('xy')
                    elif val == 'xy':
                        parm.set('zx')
                else:
                    raise hou.Error("Unsupported parameter")
            else:
                raise hou.Error("Unsupported parameter")
        else:
            ptuple = node.parmTuple(parmname)
            if ptuple is not None:
                if len(ptuple) == 3 and \
                     ptuple.parmTemplate().type() == hou.parmTemplateType.Float:
                    # A temporary default set by the user must override any auto
                    # correction we can do here.
                    if ptuple[0].hasTemporaryDefaults() or \
                       ptuple[1].hasTemporaryDefaults() or \
                       ptuple[2].hasTemporaryDefaults():
                        return

                    if ptuple.description() == "Rotate":
                        if hou.ui.orientationUpAxis() == hou.orientUpAxis.Y:
                            # Z Up -> Y Up: Rotate -90 degrees about the x axis.
                            ptuple[0].set(ptuple[0].evalAsFloat() - 90)
                        elif hou.ui.orientationUpAxis() == hou.orientUpAxis.Z:
                            # Y Up -> Z Up: Rotate 90 degrees about the x axis.
                            ptuple[0].set(ptuple[0].evalAsFloat() + 90)
                    else:
                        vals = ptuple.evalAsFloats()
                        if hou.ui.orientationUpAxis() == hou.orientUpAxis.Y:
                            # Z Up -> Y Up: Rotate -90 degrees about the x axis.
                            ptuple.set([vals[0], vals[2], -vals[1]])
                        elif hou.ui.orientationUpAxis() == hou.orientUpAxis.Z:
                            # Y Up -> Z Up: Rotate 90 degrees about the x axis.
                            ptuple.set([vals[0], -vals[2], vals[1]])
                else:
                    raise hou.Error("Unsupported parameter")
            else:
                raise hou.Error("Missing parameter")

def baseUpOrientation():
    """This function returns the base orientation (rotation) matrix that aligns
       the standard world axes to those of the global orientation preference.
    """
    if hou.ui.orientationUpAxis() == hou.orientUpAxis.Y:
        return hou.Matrix3(((0, 0, 1), (1, 0, 0), (0, 1, 0)))
    elif hou.ui.orientationUpAxis() == hou.orientUpAxis.Z:
        return hou.Matrix3(((1, 0, 0), (0, 1, 0), (0, 0, 1)))
    else:
        return hou.Matrix3(((1, 0, 0), (0, 1, 0), (0, 0, 1)))

def ocioColorSpaceMenuList(include_roles=True, extra_choices=[]):
    choices = extra_choices[:]
    if include_roles:
        for role in hou.Color.ocio_roles():
            choices.append(role)
            choices.append('Role: ' + role.title().replace('_', ' '))
        choices += ["_separator_", "_separator"]
    spaces = sorted(set(hou.Color.ocio_spaces()), key=lambda s: s.lower())
    for s in spaces:
        choices.append(s)
        choices.append(s)
    return choices

def ocioColorSpaceMenu(include_roles=True, extra_choices=[]):
    choices = ocioColorSpaceMenuList(include_roles, extra_choices)
    return "'%s'" % (' '.join(['"%s"' % x for x in choices]))

def ocioViewMenuList(display = hou.Color.ocio_defaultDisplay(), extra_choices=None):
    choices = []
    if extra_choices:
        choices = extra_choices[:]
    spaces = sorted(set(hou.Color.ocio_views(display)), key=lambda s: s.lower())
    for s in spaces:
        choices.append(s)
        choices.append(s)
    return choices

def ocioViewMenu(display = hou.Color.ocio_defaultDisplay(), extra_choices=None):
    choices = ocioViewMenuList(display=display, extra_choices=extra_choices)
    return "'%s'" % (' '.join(['"%s"' % x for x in choices]))

def ocioDisplayMenuList(extra_choices=None):
    choices = []
    if extra_choices:
        choices = extra_choices[:]
    spaces = sorted(set(hou.Color.ocio_activeDisplays()), key=lambda s: s.lower())
    for s in spaces:
        choices.append(s)
        choices.append(s)
    return choices

def ocioDisplayMenu(extra_choices=None):
    choices = ocioDisplayMenuList(extra_choices=extra_choices)
    return "'%s'" % (' '.join(['"%s"' % x for x in choices]))

def ocioLookMenuList(extra_choices=None):
    choices = []
    looks = sorted(set(hou.Color.ocio_looks()), key=lambda s: s.lower())
    if extra_choices:
        choices = extra_choices[:]
    for look in looks:
        choices.append(look)
        choices.append(look)
    return choices

def ocioLookMenu(extra_choices=None):
    choices = ocioLookMenuList(extra_choices=extra_choices)
    return "'%s'" % (' '.join(['"%s"' % x for x in choices]))

def parseDialogScriptMenu(filename, defchoices=[], forhscript=True):
    """This function parses a disk file specified by the filename.
       The file is parsed such that comments ('#') are stripped and
       lines containing exactly 2 arguments are printed out.  Quotes
       are handled.

       The function can be used by dialog script menus which want to
       generate dynamic menus based on disk files.

       The dynamic menu should have the script:
            echo `pythonexprs("__import__('toolutils').parseDialogScriptMenu(filename, [('token1', 'label1'), ('token2', 'label2'), ...])")`
       the diskfile will be searched in the Houdini path.  If the disk
       file isn't found, the default choices will be used instead.

       If the menu uses python script instead, set forhscript to False and it
       will return list of choices without surrounding them in quotes.
    """
    try:
        path = hou.findFile(filename)
    except hou.OperationFailed:
        path = filename
    try:
        fp = open(path, 'r')
    except:
        fp = None
    choices = []
    if fp:
        for l in fp.readlines():
            args = shlex.split(l, comments=True)
            if len(args) == 2:
                choices.append((args[0], args[1]))
        fp.close()
    if not len(choices):
        choices = defchoices

    def quoteString(s):
        # Put string in single quotes to prevent expansion by hscript
        return ''.join(["'", s.replace("'", "\\'"), "'"])
    strs = []
    if forhscript:
        for c in choices:
            if len(c) == 2:
                strs.append(quoteString(c[0]))
                strs.append(quoteString(c[1]))
        return quoteString(' '.join(strs))  # Return a string of the menu choices
    else:
        for c in choices:
            if len(c) == 2:
                strs.append(c[0])
                strs.append(c[1])
        return strs


def updatePlaneType(planeindex, variable):
    """This function is intended to update deep raster plane parameters
       based on the newly set plane variable name.  Use this in a callback
       script as follows:

       callback "`pythonexprs(\"__import__('toolutils').updatePlaneType($script_multiparm_index, \'$script_value\')\")`"
    """
    # These map all the types as defined in $HH/MantraPlanes (plus some extras)
    #
    # For planes that need to specify additional parameters or that
    # should get a quickplane toggle, please add to the quickplanes.py module.
    vextypes = {
        "Cf"                    : "vector",
        "Of"                    : "vector",
        "Af"                    : "float",
        "direct_shadow"         : "vector",
        "direct_reflectivity"   : "vector",
        "indirect_emission"     : "vector",
        "indirect_noshadow"     : "vector",
        "indirect_shadow"       : "vector",
        "all"                   : "vector",
        "direct"                : "vector",
        "indirect"              : "vector",
        "level"                 : "float",
        "diffuselevel"          : "float",
        "specularlevel"         : "float",
        "volumelevel"           : "float",
        "Shading_Samples"       : "float",
        "Opacity_Samples"       : "float",
        "Pixel_Samples"         : "float",
        "ray:nts"               : "float",
        "ray:nets"              : "float",
        "ray:neets"             : "float",
        "ray:nobjs"             : "float",
        "ray:nprims"            : "float",
        "ray:ncontinued"        : "float",
    }

    ropnode = hou.node(".")
    vextype = vextypes.get(variable, None)
    channel = ''
    percomp = False
    quantize = 'half'
    sfilter = 'alpha'
    pfilter = ''

    if vextype is None:
        # variables not found in vextypes, try quickplanes
        quickplane = quickplanes.getPlaneDict().get(variable, None)

        if quickplane is None:
            # also no quickplane, do nothing
            return

        channel = quickplane.channel
        vextype = quickplane.vextype
        if quickplane.quantize == 'float':
            quantize = 'float'
        elif quickplane.quantize == 'float16':
            quantize = 'half'

        # The values below are stored in the QuickPlane's ray property dict

        sfilter = quickplane.opts.get('sfilter', ['alpha'])[0]
        pfilter = quickplane.opts.get('pfilter', [''])[0]
        percomp = quickplane.percomp

    ropnode.parm("vm_vextype_plane%d" % planeindex).set(vextype)
    ropnode.parm("vm_channel_plane%d" % planeindex).set(channel)
    ropnode.parm("vm_componentexport%d" % planeindex).set(percomp)
    ropnode.parm("vm_quantize_plane%d" % planeindex).set(quantize)
    ropnode.parm("vm_sfilter_plane%d" % planeindex).set(sfilter)
    ropnode.parm("vm_pfilter_plane%d" % planeindex).set(pfilter)
    ropnode.parm("vm_lightexport%d" % planeindex).set(variable in ['all'])

def updateBakeExtractImageFormat():
    ''' Obsolete as of H16.0 - but is required for old hip files'''
    ropnode = hou.node(".")
    format = ropnode.parm('uvextractimageformat').eval()
    if format == 'None':
        ropnode.parm('vm_extractimageplanes').set(False)
    else:
        ropnode.parm('vm_extractimageplanes').set(True)
        ropnode.parm('vm_extractimageplanesformat').set(format)

def updateBakePlanes(parm):
    ''' Obsolete as of H16.0 - but is required for old hip files'''
    ropnode = hou.node(".")
    value = ropnode.parm(parm).eval()

    if parm == 'vm_uvoutputs_all' or parm == 'vm_uvoutputs_material':
        ropnode.parm('vm_quickplane_diff_clr').set(value)
        ropnode.parm('vm_quickplane_emit_clr').set(value)
        ropnode.parm('vm_quickplane_sss_clr').set(value)
        ropnode.parm('vm_quickplane_spec_clr').set(value)
        ropnode.parm('vm_quickplane_spec_rough').set(value)
    if parm == 'vm_uvoutputs_all' or parm == 'vm_uvoutputs_tangentnormals':
        ropnode.parm('vm_quickplane_Nt').set(value)
    if parm == 'vm_uvoutputs_all' or parm == 'vm_uvoutputs_occlusion':
        ropnode.parm('vm_quickplane_Oc').set(value)
    if parm == 'vm_uvoutputs_all' or parm == 'vm_uvoutputs_displacement':
        ropnode.parm('vm_quickplane_Ds').set(value)
    if parm == 'vm_uvoutputs_all' or parm == 'vm_uvoutputs_vdisplacement':
        ropnode.parm('vm_quickplane_Vd').set(value)
    if parm == 'vm_uvoutputs_all' or parm == 'vm_uvoutputs_thickness':
        ropnode.parm('vm_quickplane_Th').set(value)
    if parm == 'vm_uvoutputs_all' or parm == 'vm_uvoutputs_cavity':
        ropnode.parm('vm_quickplane_Cv').set(value)
    if parm == 'vm_uvoutputs_all' or parm == 'vm_uvoutputs_curvature':
        ropnode.parm('vm_quickplane_Cu').set(value)

def mapTypeCategoriesToSubnetName(nodetypecategory, acceptedtypecategory):
    """This function returns a name of the subnet that accepts nodetypecategory
       as child type and can be created in a container whose child type is
       acceptedtypecategory.
       Returns None if these two categories are the same (ie, no need for
       a subnet to accommodate nodetypecategory). Also returns None if
       the mapping has not been defined yet.
    """
    # cannot map with nil category and no need to create intermediate node
    # if categories already match
    if nodetypecategory is None or acceptedtypecategory == nodetypecategory:
        return None

    # map the SOP requested type: use Geometry in OBJ and Sopnet elsewhere
    if nodetypecategory == hou.sopNodeTypeCategory():
        if acceptedtypecategory == hou.objNodeTypeCategory():
            return "geo"
        if acceptedtypecategory == hou.lopNodeTypeCategory():
            return "sopcreate"
        return "sopnet"

    # map the OBJ requested type: use Object Network everywhere
    if nodetypecategory == hou.objNodeTypeCategory():
        return "objnet"

    # unhandled category types
    return None

def _mapSubnetToNode(subnet, nodetypecategory, acceptedtypecategory):
    """Returns the target node new nodes can be created under
    """
    # Find the subnet node to create the new nodes under
    if nodetypecategory == hou.sopNodeTypeCategory() and acceptedtypecategory == hou.lopNodeTypeCategory():
        return subnet.node("sopnet/create")
    return subnet

def removeDefaultGeometryObjectContents(objectnode):
    """ Destroy the File SOP that gets created inside a default Geometry
        Object.
    """
    file_node = objectnode.node("file1")
    if file_node is not None:
        file_node.destroy()

def createNodeInContainer(container, nodetypecategory, nodetypename, nodename,
                          exact_node_type):
    """This function attempts to create a node of a given type category and
       type name in a given container. If the container does not allow a given
       type category, this funciton creates a network of a correct type first,
       and then creates the required node within that network.
       If exact_node_type is true, it attempts to create a node of the exact
       nodetypename; otherwise, the nodtypename may be resolved to the
       preferred namespace or version of that typename.
       It retuns a pair of nodes, the fist being the node created in the
       container and the second being the node of a required operator type
       (which in most cases will be the same nodes).
    """
    # If we have a node type category, we can pre-verify that container will
    # accept creation of the requested node type. If container does not accept
    # it we will try create an intermediate network node first.
    #
    # Don't run init scripts on container's child, because we want to do that
    # after the inputs have been connected in the caller.
    subnettypename = mapTypeCategoriesToSubnetName(
        nodetypecategory, container.childTypeCategory())
    if subnettypename is None:
        parent  = container
        do_init = False
    else:
        if nodename:
            container_name = nodename
        else:
            # The node type name might have a namespace, so use the core part
            # of the type name for naming the parent container.
            nodetype = hou.nodeType(nodetypecategory, nodetypename)
            if nodetype:
                _, _, container_name, _ = nodetype.nameComponents()
            else:
                container_name = nodetypename

            container_name += '1'

        parent  = container.createNode(subnettypename, container_name,
                    run_init_scripts = False )
        do_init = True

    # create the requested node
    try:
        newnode = _mapSubnetToNode(parent, nodetypecategory, container.childTypeCategory()).createNode(nodetypename, nodename,
                                    run_init_scripts = do_init,
                                    exact_type_name = exact_node_type)
    except hou.MatchDefinitionError as e:
        children = parent.children()
        newnode  = children[len(children)-1]
        hou.ui.displayMessage("There were errors while matching the new\n" +
                              "node to its definition.",
                              severity = hou.severityType.Error,
                              title = "Error Creating Node",
                              details = e.instanceMessage())

    # package the nodes in a tuple and return them
    container_child = newnode if parent == container else parent

    return (container_child, newnode)

def reformatPermissionErrors(function):
    """This function decorator will trap any permission error exceptions and
       raise a different exception with a nicer message."""
    def new_func(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except hou.PermissionError:
            raise hou.Error(
                "Failed to modify node or parameter because of a permission "
                "error.  Possible causes include locked assets, takes, "
                "product permissions or user-specified permissions.")
    new_func.__name__ = function.__name__
    new_func.__doc__ = function.__doc__
    new_func.__dict__.update(function.__dict__)
    return new_func
'''
def zjy_create_generictool_json(toolname,pane,inputs=None,outputs=None):
    # print(inputs)
    # print(outputs)
    file_path = "E:/test_save/" 
    pwd = pane.pwd()
    if len(inputs) != 0 and len(outputs) == 0:
        download_input_json_path = file_path+'zjy_inputjson.json'
        inputjsondata_key = str((pwd.node(inputs[0][0]).type().name(),inputs[0][1]))
        try:
            inputjsondata=json.load(open(download_input_json_path))
        except:
            inputjsondata={}
        if inputjsondata_key in inputjsondata.keys():
            inputjsondatavalue = inputjsondata[inputjsondata_key]
        else:
            inputjsondatavalue = {}
        # inputnodename = inputs[0][0]
        # inputnodeindex = inputs[0][1]
        if toolname in inputjsondatavalue.keys():
            inputjsondatavalue[toolname]+=1
        else:
            inputjsondatavalue[toolname] = 1
        inputjsondata[inputjsondata_key] = inputjsondatavalue
        json.dump(inputjsondata, open(download_input_json_path, 'w', encoding='utf-8'))

    if len(inputs) == 0 and len(outputs) != 0:
        download_input_json_path = file_path+'zjy_outputjson.json'
        inputjsondata_key = str((pwd.node(outputs[0][0]).type().name(),outputs[0][1]))
        try:
            inputjsondata=json.load(open(download_input_json_path))
        except:
            inputjsondata={}
        if inputjsondata_key in inputjsondata.keys():
            inputjsondatavalue = inputjsondata[inputjsondata_key]
        else:
            inputjsondatavalue = {}
        # inputnodename = inputs[0][0]
        # inputnodeindex = inputs[0][1]
        if toolname in inputjsondatavalue.keys():
            inputjsondatavalue[toolname]+=1
        else:
            inputjsondatavalue[toolname] = 1
        inputjsondata[inputjsondata_key] = inputjsondatavalue
        json.dump(inputjsondata, open(download_input_json_path, 'w', encoding='utf-8'))

    if len(inputs) != 0 and len(outputs) != 0:
        download_input_json_path = file_path+'zjy_input_outputjson.json'
        inputjsondata_key = str((pwd.node(inputs[0][0]).type().name(),inputs[0][1],pwd.node(outputs[0][0]).type().name(),outputs[0][1]))
        try:
            inputjsondata=json.load(open(download_input_json_path))
        except:
            inputjsondata={}
        if inputjsondata_key in inputjsondata.keys():
            inputjsondatavalue = inputjsondata[inputjsondata_key]
        else:
            inputjsondatavalue = {}
        # inputnodename = inputs[0][0]
        # inputnodeindex = inputs[0][1]
        if toolname in inputjsondatavalue.keys():
            inputjsondatavalue[toolname]+=1
        else:
            inputjsondatavalue[toolname] = 1
        inputjsondata[inputjsondata_key] = inputjsondatavalue
        json.dump(inputjsondata, open(download_input_json_path, 'w', encoding='utf-8'))
'''
@reformatPermissionErrors
def genericTool(scriptargs, nodetypename, nodename=None, nodetypecategory=None,
                exact_node_type=True):
    """ Handles the creation of any node in a Network Editor pane.

        This function is intended to instantiate a node of a given type from
        shelf tools, and thus, if exact_node_type argument is True, it creates
        the node of the exact type specified by nodetypename.
        However, if exact_node_type argument is False, then the base type may
        get resolved to another namespace or another version, and
        the created node may be of that resolved type (eg 'hda' may resolve to
        'mynamespace::hda::2.0').
        D:dobe\houdini\Houdini 20.5.571\houdini\python3.11libs oolutils.py:genericTool:
        scriptargs =  {
        'toolname': 'sop_null', 'panename': 'copy_of_panetab12_2', 
        'altclick': False, 'ctrlclick': False, 'shiftclick': False, 'cmdclick': False, 
        'pane': <hou.NetworkEditor copy_of_panetab12_2>, 'viewport': None, 
        'inputnodename': '', 'outputindex': -1, 'inputs': [], 'outputnodename': 'null1', 'inputindex': 0, 'outputs': [('null1', 0)], 
        'branch': True, 'autoplace': False, 'requestnew': False, 
        'nodepositionx': '-6.540054', 'nodepositiony': '3.002555'
        }
         nodetypename =  null nodename =  None nodetypecategory =  <hou.OpNodeTypeCategory for Sop>    exact_node_type =  True

    """

    # zjy_create_generictool_json(scriptargs['toolname'],scriptargs['pane'],scriptargs['inputs'],scriptargs['outputs'])
    zjy_create_generictool_json(scriptargs['toolname'],scriptargs['pane'],scriptargs['inputs'],scriptargs['outputs'])

    pane = activePane(scriptargs)
    if isinstance(pane, hou.PathBasedPaneTab):
        # Our defaults that we modify according to options.
        movedisplay = False
        autoscroll = True
        autoplace = False
        branch = False

        # Get information about the input and output nodes we'll want
        # to connect to our new node.
        container = pane.pwd()
        inputs = []
        outputs = []
        if "inputs" in scriptargs:
            inputs = [(container.item(it[0]), it[1])
                      for it in scriptargs["inputs"]]
        if "outputs" in scriptargs:
            outputs = [(container.item(it[0]), it[1], 0)
                       for it in scriptargs["outputs"]]

        if "branch" in scriptargs:
            branch = scriptargs["branch"]

        if "autoplace" in scriptargs:
            autoplace = scriptargs["autoplace"]

        # If shift-clicked we want to auto append to the current
        # node
        if "shiftclick" in scriptargs and scriptargs["shiftclick"]:
            autoplace = True
            movedisplay = True
            if not inputs:
                initem = pane.currentNode()
                # If the "current node" is the container, the network either
                # is empty or got its current node cleared (which can happen).
                # Look for a few special cases to replace the current node as
                # the automatic input.
                if initem == container:
                    if isinstance(container, hou.SopNode) or \
                       isinstance(container, hou.ObjNode) or \
                       isinstance(container, hou.DopNode) or \
                       isinstance(container, hou.CopNode) or \
                       isinstance(container, hou.LopNetwork) or \
                       isinstance(container, hou.LopNode):
                        initem = container.displayNode()
                # If the "current node" is still the container, the network
                # must be empty, so don't attempt to connect anything, unless
                # the container is a subnet, in which case we can connect to
                # the first subnet input.
                if initem == container:
                    if container.isSubNetwork() and \
                       not container.type().isManager(True) and \
                       container.indirectInputs():
                        initem = container.indirectInputs()[0]
                    else:
                        initem = None
                if initem is not None:
                    inputs = [(initem, 0)]

        if "nodepositionx" in scriptargs and \
           "nodepositiony" in scriptargs:
            try:
                pos = [ float( scriptargs["nodepositionx"] ),
                        float( scriptargs["nodepositiony"] )]
            except:
                pos = None
        else:
            pos = None

        # If we're in a network editor, get the user to pick a position,
        # unless auto-place is turned on.
        if isinstance(pane, hou.NetworkEditor):
            context_data = {
                    'inputs' : inputs,
                    'outputs' : outputs,
                    'branch' : branch,
                    'nodetypename' : nodetypename,
                    'ghostnodes': scriptargs.get('ghostnodes', []),
                    'ghostconnections': scriptargs.get('ghostconnections', [])
            }
            if not autoplace and pos is None and not pane.listMode():
                pane.pushEventContext('nodegraphselectpos', context_data)
                if 'pos' not in context_data:
                    raise hou.OperationInterrupted("Node creation cancelled")
                pos = context_data['pos']
            else:
                import nodegraphselectpos
                nodetypefunc = nodegraphselectpos.getNodeTypeContextDataFunc(
                    pane, nodetypename)
                nodegraphselectpos.setEventContextData(pane, context_data,
                    None, None, None, nodetypefunc)

            # The input and output items may have been changed by the state.
            inputs = context_data['inputs']
            outputs = context_data['outputs']
            branch = context_data['branch']

        # Create the new node of that exact nodetypename.
        (child, newnode) = createNodeInContainer(container, nodetypecategory,
                                                 nodetypename, nodename,
                                                 exact_node_type)

        # Connect inputs and outputs, if any.
        connectMultiInputsAndOutputs(child, branch, inputs, outputs)

        # Run the init scripts after connecting the inputs to the node.
        child.runInitScripts()

        # Creation scripts may have added extra contents to an intermediate
        # node, so remove it here, if necessary.
        # Since we've cleaned the creation code, this is no longer required.
        # if child != newnode and nodetypecategory == hou.sopNodeTypeCategory():
        #    removeDefaultGeometryObjectContents(child)

        # Set the node position to the selected position for a network
        # editor pane, otherwise automatically pick a good spot.
        orig_x = 0
        orig_y = 0
        if isinstance(pane, hou.NetworkEditor):
            if pos is not None:
                import nodegraphutils

                # Nudge our outputs to make room for the new node.
                child.setPosition(pos)
                nodegraphutils.moveNodesToAvoidOverlap(pane, [child])
                mousepos = pane.posToScreen(hou.Vector2(pos))
                netbox = nodegraphutils.getNetworkBoxUnderMouse(pane, mousepos)
                if netbox is not None:
                    netbox.addItem(child)

            else:
                import nodegraphutils

                # Put the new node in our input's netbox.
                netbox = None
                if inputs:
                    netbox = inputs[0][0].parentNetworkBox()
                if netbox is None and outputs:
                    netbox = outputs[0][0].parentNetworkBox()
                if netbox:
                    netbox.addItem(child)
                # Nudge our outputs to make room for the new node.
                child.moveToGoodPosition(True, False, False, False)
                nodegraphutils.moveNodesToAvoidOverlap(pane, [child])

        else:
            child.moveToGoodPosition(True, False, False, False)

        # Select the node AFTER removing default geo and AFTER placing it
        # in the right spot in the network. Otherwise viewport
        # redraws and temporarily displays a selected default geo or
        # the node appears temporarily before placing itself.
        if 'do_not_jump_to_child' not in scriptargs:
            child.setCurrent(1, 1)

        # Set any custom parameters that are given before setting the 
        # current node in the pane which updates the viewport and can 
        # cause temporal aliasing if parameters are set afterwards.  
        
        # In most cases, newnode == child, but not always so for consistency
        # any given parms are applied to newnode
        if 'parms' in scriptargs:
            for parm_name, parm_value in scriptargs['parms'].items():
                newnode.parm(parm_name).set(parm_value)

        # pane.setCurrentNode(child) will synchronously update the UI
        # which may be necessary for user scripts to function properly.  
        pane.setCurrentNode(child)

        # If we are putting down a SOP, and we have an input node,
        # decide if we should move the display/render flags.
        if movedisplay and \
           isinstance(child, hou.SopNode) and  \
           len(child.inputs()):
            # Move display/render flags
            if any([(input and input.isDisplayFlagSet()) for input in child.inputs()]):
                child.setDisplayFlag(True)
            if any([(input and input.isRenderFlagSet()) for input in child.inputs()]):
                child.setRenderFlag(True)
        elif movedisplay and \
             isinstance(child, hou.ChopNode):
            # Move audio (output) flag
            if any([(input and input.isAudioFlagSet()) for input in child.inputs()]):
                child.setAudioFlag(True)
        elif movedisplay and \
             isinstance(child, hou.LopNode):
            # Move display flag
            if any([(input and input.isDisplayFlagSet()) for input in child.inputs()]):
                child.setDisplayFlag(True)
        elif movedisplay and \
             isinstance(child, hou.CopNode) and \
             len(child.inputs()):
            # Move display flag
            if any([(input and input.isDisplayFlagSet()) for input in child.inputs()]):
                child.setDisplayFlag(True)

        # If we've autoplaced this node, we want to re-center the network
        # editor(s) on it.
        if pos is None and autoscroll:
            homeToSelectionNetworkEditorsFor(child)

        return newnode
    else:
        raise hou.Error("Can't run the tool in the selected pane.")

def _getBranchMode(scriptargs):
    """Utility function to convert the "branch" key in scriptargs into a
       hou.stateGenerateMode enum.
    """
    if "branch" in scriptargs and scriptargs["branch"]:
        return hou.stateGenerateMode.Branch
    else:
        return hou.stateGenerateMode.Insert

def _getRequestNew(scriptargs):
    """Utility function to convert the "requestnew" key in scriptargs into a
       boolean.
    """
    return "requestnew" in scriptargs and scriptargs["requestnew"]

def genericStateTool(scriptargs, statename):
    """ Runs a specific state in an open viewer pane. """
    pane = activePane(scriptargs)
    if isinstance(pane, (hou.SceneViewer)):
        pane.setCurrentState(statename, generate=_getBranchMode(scriptargs),
                             request_new_on_generate=_getRequestNew(scriptargs))
    elif isinstance(pane, hou.PathBasedPaneTab) and \
         pane.pwd().childTypeCategory().nodeType(statename) is not None:
        genericTool(scriptargs, statename)
    else:
        raise hou.Error("Can't run the tool in the selected pane.")

def moveNodesToGoodPosition(movenodes):
    """ Moves a list of nodes to good positions. """
    for movenode in movenodes:
        movenode.moveToGoodPosition(False, False, False, False)

def generateToolScriptForNode(nodepath_or_list, \
                              input_nodepath = None, output_nodepath = None):

    if isinstance(nodepath_or_list, basestring):
        nodepath_list = [nodepath_or_list]
    else:
        nodepath_list = nodepath_or_list

    if input_nodepath is None:
        input_nodepath = nodepath_list[0]
    if output_nodepath is None:
        output_nodepath = nodepath_list[-1]

    nodepath = nodepath_list[-1]    # use last selected as the primary
    operator_name = hou.node(nodepath).type().name()
    opscript_cmd = 'opscript -r -b -m ' + input_nodepath + ' ' \
                                        + output_nodepath
    for nodepath in nodepath_list:
        opscript_cmd += ' ' + nodepath

    # TODO: should the opscript_preamble be part of the opscript output?
    # the opscript does not protect from arg2 and arg3 not being set.
    hscript_argtest = """
if ($argc < 2 || "$arg2" == "") then
   set arg2 = 0
endif
if ($argc < 3 || "$arg3" == "") then
   set arg3 = 0
endif
"""
    hscript_cmd = hou.hscript( opscript_cmd )
    python_cmd = """
import sys
import toolutils

outputitem = None
inputindex = -1
inputitem = None
outputindex = -1

num_args = 1
h_extra_args = ''
pane = toolutils.activePane(kwargs)
if not isinstance(pane, hou.NetworkEditor):
    pane = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
    if pane is None:
       hou.ui.displayMessage(
               'Cannot create node: cannot find any network pane')
       sys.exit(0)
else: # We're creating this tool from the TAB menu inside a network editor
    pane_node = pane.pwd()
    if "outputnodename" in kwargs and "inputindex" in kwargs:
        outputitem = pane_node.item(kwargs["outputnodename"])
        inputindex = kwargs["inputindex"]
        h_extra_args += 'set arg4 = \"' + kwargs["outputnodename"] + '\"\\n'
        h_extra_args += 'set arg5 = \"' + str(inputindex) + '\"\\n'
        num_args = 6
    if "inputnodename" in kwargs and "outputindex" in kwargs:
        inputitem = pane_node.item(kwargs["inputnodename"])
        outputindex = kwargs["outputindex"]
        h_extra_args += 'set arg6 = \"' + kwargs["inputnodename"] + '\"\\n'
        h_extra_args += 'set arg9 = \"' + str(outputindex) + '\"\\n'
        num_args = 9
    if "autoplace" in kwargs:
        autoplace = kwargs["autoplace"]
    else:
        autoplace = False
    # If shift-clicked we want to auto append to the current
    # node
    if "shiftclick" in kwargs and kwargs["shiftclick"]:
        if inputitem is None:
            inputitem = pane.currentNode()
            outputindex = 0
    if "nodepositionx" in kwargs and \
            "nodepositiony" in kwargs:
        try:
            pos = [ float( kwargs["nodepositionx"] ),
                    float( kwargs["nodepositiony"] )]
        except:
            pos = None
    else:
        pos = None

    if not autoplace and not pane.listMode():
        if pos is not None:
            pass
        elif outputitem is None:
            pos = pane.selectPosition(inputitem, outputindex, None, -1)
        else:
            pos = pane.selectPosition(inputitem, outputindex,
                                      outputitem, inputindex)

    if pos is not None:
        if "node_bbox" in kwargs:
            size = kwargs["node_bbox"]
            pos[0] -= size[0] / 2
            pos[1] -= size[1] / 2
        else:
            pos[0] -= 0.573625
            pos[1] -= 0.220625
        h_extra_args += 'set arg2 = \"' + str(pos[0]) + '\"\\n'
        h_extra_args += 'set arg3 = \"' + str(pos[1]) + '\"\\n'
h_extra_args += 'set argc = \"' + str(num_args) + '\"\\n'

pane_node = pane.pwd()
child_type = pane_node.childTypeCategory().nodeTypes()

if '""" + operator_name + """' not in child_type:
   hou.ui.displayMessage(
           'Cannot create node: incompatible pane network type')
   sys.exit(0)

# First clear the node selection
pane_node.setSelected(False, True)

h_path = pane_node.path()
h_preamble = 'set arg1 = \"' + h_path + '\"\\n'
h_cmd = r'''""" + hscript_argtest + hscript_cmd[0] + """'''
hou.hscript(h_preamble + h_extra_args + h_cmd)
"""
    return python_cmd

def _createModule(module_name, source):
    """Create and return a module-like object with the given name from the
       given source code.  This module will not appear in sys.modules.  If
       the source code has a syntax error, an exception will be raised.
    """
    # Compile the code and create the module's dictionary.  Put
    # __builtins__ in it manually so it doesn't copy the contents
    # of the current globals() dict.
    code = compile(source, module_name, 'exec')
    module_dict = {'__builtins__': __builtins__}
    eval(code, module_dict)

    # Create a module-like object object and return it.
    class ModuleWrapper(object):
        pass
    module = ModuleWrapper()
    module.__dict__ = module_dict
    return module

def createModuleFromSection(module_name, node_type, section_name):
    """Create and return a module-like object with the given name from the
       contents of a section in an HDA.  This module will not appear in
       sys.modules.  If the source code has a syntax error, an exception will
       be raised.  Use this function to create submodules in the PythonModule
       section of an HDA.  For example:
           submod = toolutils.createModuleFromSection(
                'submod', kwargs['type'], 'PythonSubmod')
    """
    return _createModule(module_name,
        node_type.definition().sections()[section_name].contents())

def nodeNameFromTypeName(nodetypename):
    """Given an operator node type name, return a valid node name
       corresponding to that type. For example, if the type name contains
       any namespace or version components, they are stripped off.
       The returned node name contains only characters that are allowed
       to appear in the node names.
    """
    # compoenents consist of (scope_op, namespace, core_name, version)
    # and we want to use the type's core name as the node name, so access
    # the third element in the tuple (ie, index=2)
    components = hou.hda.componentsFromFullNodeTypeName(nodetypename)
    return components[2]

def placeToolImmediately(kwargs):
    """ Returns true if the provided kwargs has a modifier key suggesting
        the tool be placed right away.  This is a ctrl click or a cmd click
        depending on the platform.
    """
    # The keys may not be present, but in those cases we default to false.
    if kwargs.get("ctrlclick", False) or kwargs.get("cmdclick", False):
        return True
    return False

def getImmediatePlacementPosition(scene_viewer):
    """ Returns the world space position to use for immediate placement of a
        new tool given a scene viewer.
    """
    viewport = scene_viewer.curViewport()
    cplane = scene_viewer.constructionPlane()

    if viewport is not None and \
        viewport.usesConstructionPlane() and \
        cplane.isVisible():
        return hou.Vector3(0.0, 0.0, 0.0) * cplane.transform()
    else:
        return hou.Vector3(0.0, 0.0, 0.0)

def getImmediatePlacementOrientedPosition(scene_viewer, base_orientation=None):
    """ Returns the world space position and world space orientation to use for
        immediate placement of a new tool given a scene viewer.
    """
    viewport = scene_viewer.curViewport()
    cplane = scene_viewer.constructionPlane()

    if base_orientation is None:
        base_orientation = baseUpOrientation()

    if viewport is not None and \
        viewport.usesConstructionPlane() and \
        cplane.isVisible():
        return (hou.Vector3(0.0, 0.0, 0.0) * cplane.transform(),
                base_orientation.transposed() *
                    cplane.transform().extractRotationMatrix3())
    else:
        return (hou.Vector3(0.0, 0.0, 0.0), None)


def getSubnetOutputNodes(subnet):
    """ Returns a list of output nodes. The position of a node within the list
        corresponds to it's output index.

        Intermediate entries that don't have an output equal None.
    """
    outputnodes = []
    for outnode in findAllChildNodesOfType(subnet, 'output'):
        outputidx = outnode.parm('outputidx').eval()
        for i in range(len(outputnodes), outputidx+1):
            outputnodes.append(None)
        outputnodes[outputidx] = outnode

    return outputnodes

class ToolboxTemplateGroup(object):
    """Generates a UI code block and a template group for toolbox hou.SceneViewer.selectObjects"""
    def __init__(self):
        self._templates = []
        self._templategroup = None
        self._ui_decl = ""
        self._ui_gad = ""
        self._ui = ""

    def buildHelpStr(self, h):
        if h=="":
            return ""

        return "HELP(\"%s\")" % h

    def addMenu(self, name, label, values, default_value, helpstr=""):
        """Adds a menu select control with a label to the toolbox"""
        tokens = [""]*len(values)
        items = ""
        for i in range(len(values)):
            tokens[i] = str(i)
            items += "    \"%s\"\n" % values[i]
        self._ui_decl += "%s.val = SELECT_MENU\n{\n%s}\n" % (name,items)

        if label != "":
            self._ui_gad += \
            "    LABEL \"%s\";\n" % label

        self._ui_gad += \
        "    SELECT_MENU_BUTTON MENU(%s.val) %s;\n" % (name, self.buildHelpStr(helpstr) )

        self._templates.append( hou.MenuParmTemplate(name=name, label=label, menu_items=tokens, menu_labels=values, default_value=default_value) )

    def addToggle(self, name, label, default_value, helpstr=""):
        """Adds a toggle control with a label to the toolbox"""

        self._ui_gad += \
        "    TOGGLE_BUTTON \"%s\" VALUE(%s.val) %s;\n" % (label, name, self.buildHelpStr(helpstr) )

        self._templates.append( hou.ToggleParmTemplate(name=name, label=label, default_value=default_value) )

    def addFloatField(self, name, label, default_value, num_components=1, helpstr=""):
        """Adds a float field control with a label to the toolbox"""

        self._ui_gad += \
        "    FLOAT_FIELD \"%s\" VALUE(%s.val) %s;\n" % (label,name, self.buildHelpStr(helpstr) )

        self._templates.append( hou.FloatParmTemplate(name=name,label=label, default_value=default_value, num_components=num_components) )

    def addStringField(self, name, label, default_value, num_components=1, helpstr=""):
        """Adds a string field control with a label to the toolbox"""

        self._ui_gad += \
        "    STRING_FIELD \"%s\" VALUE(%s.val) %s;\n" % (label,name, self.buildHelpStr(helpstr) )

        self._templates.append( hou.StringParmTemplate(name=name,label=label, default_value=default_value, num_components=num_components) )

    def addIntField(self, name, label, default_value, num_components=1, helpstr=""):
        """Adds an integer field control with a label to the toolbox"""

        self._ui_gad += \
        "    INT_FIELD \"%s\" VALUE(%s.val) %s;\n" % (label,name, self.buildHelpStr(helpstr) )

        self._templates.append( hou.IntParmTemplate(name=name,label=label, default_value=default_value, num_components=num_components) )


    def addToggleList(self, name, labels, default_value, helpstr=""):
        """Adds a TRS mask control with a label to the toolbox"""

        menulabels = ""
        for label in labels:
            menulabels += "    \"%s\"\n" % label

        self._ui_decl += \
        "%s.strip = SELECT_MENU\n" % name +\
        "{\n" +\
        "%s" % menulabels +\
        "}\n"

        self._ui_gad += \
        "    TOGGLE_LIST (%s.strip) VALUE(%s.val);\n" % (name,name)

        self._templates.append( hou.IntParmTemplate(name=name,label="", default_value=default_value, num_components=1) )

    def getValue(self, name):
        """Returns a UI Toolbox value"""
        if self._templategroup:
            t = self._templategroup.find(name)
            if t:
                return t.defaultValue() # the value is stored on the default value of the parmtemplate
        return None

    def update(self, layout_opt = "JUSTIFY(center,center)" ):
        """Updates UI code block and TemplateGroup."""
        # Update the ui code
        self._ui = \
        self._ui_decl + \
        "custom_toolbox.gad = \n" +\
        "{\n" +\
        "    LAYOUT(horizontal) %s\n" % layout_opt +\
        "\n" +\
        self._ui_gad + \
        "}\n" +\
        ""

        # Add a string parm to the group to define the uicode
        self._templates.append( hou.StringParmTemplate( name="ui",label="ui", num_components=1, default_value=[self._ui]) )

        # Recreate the template group
        self._templategroup = hou.ParmTemplateGroup( self._templates )

    def ui(self):
        """Returns the UI code block"""
        return self._ui

    def templategroup(self):
        """Returns the TemplateGroup"""
        return self._templategroup


def testTool(tool, debug=False, kwargs=None, pane=None, ctrlclick=False,
             altclick=False, shiftclick=None):
    """ executes a shelf tool.

        If debug is True, the tool will be executed within pdb.run()

        If 'kwargs' is not None, it is passed to the tool script as is and the
        remaining parameters are ignored, along with everything described
        below.

        If 'pane' is None, hou.ui.paneTabOfType(hou.paneTabType.SceneViewer) is
        passed to the tool instead.
    """

    if kwargs is None:
        if pane is None:
            pane = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)

        kwargs = dict()
        kwargs['pane'] = pane
        kwargs['shiftclick'] = shiftclick
        kwargs['ctrlclick'] = ctrlclick
        kwargs['altclick'] = altclick

    script = tool.script()

    if debug:
        import pdb
        pdb.run(tool.script(), globals(), locals())
    else:
        exec(tool.script(), globals(), locals())

def recursiveShowPane(p):
    """ Maximize all the parent Pane splits and make the given panel visible."""
    p.setIsSplitMaximized(True)
    pp = p.getSplitParent()
    if pp:
        recursiveShowPane( pp )

def findPythonPanel(pypanel_interface_name):
    if pypanel_interface_name not in hou.pypanel.interfaces():
        return None

    pytype = hou.pypanel.interfaces()[pypanel_interface_name]
    tabs = hou.ui.paneTabs()

    for t in tabs:
        if t.type() == hou.paneTabType.PythonPanel:
            if t.activeInterface() == pytype:
                return t

def createOrShowPythonPanel(kwargs, pypanel_interface_name, floating_panel_label, split_type ):
    """ creates a new float panel from a pypanel interface name or
        make existing ones visible.

        split_type of 0, always creates a floating panel
        split_type of 1, adds a tab on the current panel
        split_type of 2, splits vertically and creates a new tab
        split_type of 3, splits horizontally and creates a new tab
        split_type of 4, splits vertically but only on viewports and creates a new tab
        Returns the python panels tab found
    """

    pytype = hou.pypanel.interfaces()[pypanel_interface_name]
    tabs = hou.ui.paneTabs()

    ret = []
    create_new = True
    for t in tabs:
        if t.type() == hou.paneTabType.PythonPanel:
            if t.activeInterface() == pytype:
                create_new = False


                if t.pane():
                    # When holding CTRL, toggle the minimized state of the panel
                    #if placeToolImmediately(kwargs):
                    if t.pane().isSplitMinimized() or t.isCurrentTab()==False:
                        recursiveShowPane( t.pane() )
                    else:
                        t.pane().setIsSplitMaximized(False)
                    #else:
                        #recursiveShowPane( t.pane() )
                t.setIsCurrentTab()
                ret.append(t)

    if create_new:
        pane = kwargs['pane']

        # Split Vertically on SceneViewer or add tabe otehrwise
        if split_type == 4 and pane:
            if pane.type() == hou.paneTabType.SceneViewer:
                split_type = 3
            else:
                split_type = 1

        if pane is None or split_type==0:
            pypanel = hou.ui.curDesktop().createFloatingPaneTab(hou.paneTabType.PythonPanel)
            pypanel.setActiveInterface(pytype)
            if floating_panel_label:
                pypanel.floatingPanel().setName(floating_panel_label)
            ret.append(pypanel)
        elif split_type==1:
            pypanel = pane.pane().createTab(hou.paneTabType.PythonPanel)
            pypanel.setActiveInterface(pytype)
            ret.append(pypanel)
        elif split_type==2:
            pypanel = pane.pane().createTab(hou.paneTabType.PythonPanel)
            pypanel.setIsCurrentTab()
            newpanel = pypanel.pane().splitVertically()
            pypanel = newpanel.currentTab()
            pypanel.setActiveInterface(pytype)
            pane.setIsCurrentTab()
            ret.append(pypanel)
        elif split_type==3:
            pypanel = pane.pane().createTab(hou.paneTabType.PythonPanel)
            pypanel.setIsCurrentTab()
            newpanel = pypanel.pane().splitHorizontally()
            pypanel = newpanel.currentTab()
            pypanel.setActiveInterface(pytype)
            pane.setIsCurrentTab()
            ret.append(pypanel)

    return ret

def minimizePythonPanel(kwargs, pypanel_interface_name ):
    """ minimize pypanel interfaces."""

    pytype = hou.pypanel.interfaces()[pypanel_interface_name]
    tabs = hou.ui.paneTabs()

    ret = []
    for t in tabs:
        if t.type() == hou.paneTabType.PythonPanel:
            if t.activeInterface() == pytype:
                t.pane().setIsSplitMaximized(False)
                ret.append(t)


    return ret

def outputConnectionsAtIndex(node, index):
    """ Returns the output connection of a node at a specified index."""

    connections = []

    for connection in node.outputConnections():
        if connection.outputIndex() == index:
            connections.append(connection)

    return tuple(connections)

def inputConnectionsAtIndex(node, index):
    """ Returns the input connection of a node at a specified index."""

    connections = []

    for connection in node.inputConnections():
        if connection.inputIndex() == index:
            connections.append(connection)

    return tuple(connections)

def insertNodeAbove(node, newnode, nodeinputindex=0, newinputindex=0, newoutputindex=0, connectall=True):
    """ Inserts a new node (newnode) between the given node (node) and the given
        node's input node.

        :param node: the new node will be inserted above this node.
        :param newnode: the new node to insert above.
        :param nodeinputindex: the input index of node. This input index will be
            connected to the new node's output.
        :param newinputindex: the input index of new node. This input index will
            be connected to existing nodes above.
        :param newoutputindex: the output index of new node. This output index
            will be connected with node's input index.
        :param connectall: When the given node's input node has multiple outputs
            make sure all the connections are adjusted.

    """
    outputnode = None
    base_connection = None
    outputindex = None

    connections_to_change = []

    # Find the connection that connects 'node' and the 'node above node' with index.
    for outputconnection in node.inputConnections():
        if outputconnection.inputIndex() == nodeinputindex:
            base_connection = outputconnection
            break

    if base_connection is None: # we do not have input connection
        node.setInput(nodeinputindex,
                      newnode, newoutputindex)

        return newnode

    if base_connection.inputItem() == newnode:
        return newnode

    all_connections = []
    all_connections.append(base_connection)

    if connectall:
        all_connections = outputConnectionsAtIndex(base_connection.inputItem(),base_connection.outputIndex())

    for connection in all_connections:
        connection.outputItem().setInput(connection.inputIndex(),
                                         newnode, newoutputindex)

    ''' TO DO:
        This will fail when the "input node" of "node" is a "dot" AND the dot's input is connected to a second output.
    '''
    newnode.setInput(newinputindex,
                     base_connection.inputItem(),base_connection.outputIndex())

    return newnode

def branchNodeAbove(node, newnode, inputindex = 0):

    """ Inserts a new node (newnode) between the given node (node) and the given
    node's input node.

    :param node: the new node will be inserted above this node.
    :param newnode: the new node to insert above.
    :param inputindex: the input index of new node. This input index will join with the output of the node which is the input of node.

    """

    base_connection = None

    # Find the connection that connects 'node' and the 'node above node' with index.
    for outputconnection in node.inputConnections():
        if outputconnection.inputIndex() == 0:
            base_connection = outputconnection
            break

    if base_connection is None: # we do not have input connection
        base_pos = node.position()
        node.setPosition(base_pos + hou.Vector2(2,0))
        return newnode

    newnode.setInput(inputindex,
                     base_connection.inputItem(), base_connection.outputIndex())

    newnode.setPosition(base_connection.inputItem().position() + hou.Vector2(2,-1))

    return newnode

def findLopInsertionNode(cwd, respect_insertion_point = True):
    """
        Returns a node to insert a new node above or below, if such a node
        exists.

        :param cwd: A LopNode or LopNetwork.
    """
    ins_node = None
    if respect_insertion_point:
        ins_node = ip.getInsertionPointNode(cwd)

    # If no insertion point is found, check if the direct parent has a display
    # flag set. If not, find the first Output Node, and treat that output node
    # as an insertion point for this operation.
    if ins_node is None:
        if not cwd.isNetwork():
            cwd = cwd.parent()
        # At the LOP Network level (not inside a subnet) we always want to
        # return None here so nodes get inserted after the node with the
        # display flag (which we know will always exist, unlike in subnets).
        if isinstance(cwd, hou.LopNetwork):
            return None
        output_nodes = cwd.subnetOutputs()
        display_node = cwd.displayNode()
        if display_node is None:
            if output_nodes and output_nodes[0].isEditable():
                return output_nodes[0]
        if display_node in output_nodes:
            return display_node
        return None

    # Check if the current insertion point is even editable.
    if ins_node.isEditable():
        return ins_node

    # If the insertion point is not editable, and is inside a locked HDA we have two cases:
    # 1. In the locked HDA, there is an editable subnet above the insertion point. Insert the
    #    node into that subnet above the output node, after the display node, or wired to the
    #    first input (in that order of priority).
    # 2. There is no editable subnet above the insertion point or there is no editable subnet.
    #    In this case look at parent network until either we find an editable subnet (then apply case 1)
    #    or the parent network itself is editable. In the latter then just use the parent network as an
    #    insertion point.

    def caseOne(node):
        for ancestor in node.inputAncestors():
            if ancestor.parent() != node.parent() or not ancestor.isEditableInsideLockedHDA():
                continue
            if ancestor.isNetwork():
                # We found an editable subnetwork above our insertion point. The only appropriate node
                # to use as an insertion point is an output node for the ancestor editable subnet. Otherwise
                # append to display node and make new display node. If there is no output node and no
                # display node the subnet is essentially bypassed, skip the subnet and return None.
                if ancestor.displayNode() is None:
                    output_nodes = ancestor.subnetOutputs()
                    if output_nodes:
                        return (output_nodes[0], True)
                    return (None, True)
                return (None, True)
        return (None, False)

    while ins_node.isInsideLockedHDA():
        res, done = caseOne(ins_node)
        if done:
            return res
        ins_node = ins_node.parent()

    return ins_node

def buildRelOrAbsPath(srcnode, dstnode):
    ''' Builds either a relative or absolute path from scrnode to
        dstnode.  This will be relative unless we go through the root,
        in which case well just use an absolute path of dstnode.
    '''
    if dstnode is None:
        return ''

    dstpath = dstnode.path()
    if srcnode is None:
        return dstpath

    srcpath = srcnode.path()
    # if the paths diverge at root, we don't want a relative
    # path.  We have hard coded roots, so only have to test the first letter.
    if len(srcpath) > 2 and len(dstpath) > 2 and srcpath[1] != dstpath[1]:
        return dstpath
    return srcnode.relativePathTo(dstnode)

def getChildrenBoundingRect(node):
    ''' Calculates the bounding rectangle of all children of a node.
    '''

    brect = hou.BoundingRect(0,0,0,0)
    idx = 0
    for child in node.children():
        if (child.networkItemType() != hou.networkItemType.Connection or
           child.networkItemType() != hou.networkItemType.SubnetIndirectInput):
            if (idx == 0):
                pos = child.position()
                brect = hou.BoundingRect(pos,pos)
            else:
                brect.enlargeToContain(child.position()) 
    return brect
