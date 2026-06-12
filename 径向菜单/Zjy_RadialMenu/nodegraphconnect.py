import hou
import nodegraphbase as base
import nodegraphpopupmenus as popupmenus
import nodegraphautoscroll as autoscroll
import nodegraphdisplay as display
import nodegraphradialmenu as radialmenu
import nodegraphstates as states
import nodegraphutils as utils
import nodegraphview as view
from canvaseventtypes import *
import collections

try:
    from ZJYRadialMenu.Zjy_RadialMenu import *
    # import Zjy_radialmenu
except: print('import RadialMenu error')

theInputConnectorNames = (
    'input', 'multiinput', 'inputgroup', 'dotinput'
)
theOutputConnectorNames = (
    'output', 'indirectinput', 'indirectinputoutput', 'dotoutput'
)
theNodeBodyNames = (
    'node', 'connectorarea', 'preview', 'footer'
)
theMergeNodeTypes = {
    hou.sopNodeTypeCategory() : 'merge',
    hou.chopNodeTypeCategory() : 'merge',
    hou.cop2NodeTypeCategory() : 'merge',
    hou.objNodeTypeCategory() : 'blend',
    hou.dopNodeTypeCategory() : 'merge',
    hou.ropNodeTypeCategory() : 'merge',
    hou.lopNodeTypeCategory() : 'merge',
    hou.topNodeTypeCategory() : 'merge'
}
ConnectorEndInfo = collections.namedtuple('ConnectorInfo',
                [ 'item',
                  'index',
                  'conn' ])

def makeCI(item, index, conn = None):
    return ConnectorEndInfo(item, index, conn)

class PendingTabMenuAction(base.PendingAction):
    def __init__(self, editor_updates):
        base.PendingAction.__init__(self)
        self.editor_updates = editor_updates

    def completeAction(self, uievent):
        if isinstance(uievent, ModalUIEvent):
            if uievent.eventtype == 'endmodalui':
                if uievent.interfacename == 'TabMenu':
                    return True

        return False

def makeConnection(innode, inidx, outitem, outidx,
                   connect_next_unordered):
    conn = None
    if inidx >= 0:
        if isinstance(outitem, hou.Node) or \
           isinstance(outitem, hou.IndirectInput):
            innode.setInput(inidx, outitem, outidx)
            conn = utils.getConnection(innode, inidx)
        elif outitem is None:
            innode.setInput(inidx, None)

    elif utils.isCableInput(innode, inidx):
        innode.setInput(inidx, outitem, outidx)

    else:
        # Connect to the next input on innode.
        if isinstance(outitem, hou.Node) or \
           isinstance(outitem, hou.IndirectInput):
            innode.setNextInput(outitem, outidx, connect_next_unordered)
            inconns = innode.inputConnections()
            if inconns:
                conn = inconns[-1]
        elif outitem is None:
            # Asked to connect to None, so disconnect the last input.
            conns = innode.inputConnections()
            if conns and conns[-1].inputIndex() >= innode.numOrderedInputs():
                innode.setInput(conns[-1].inputIndex(), None)

    return conn

def makeTopMapperConnection(innode, inidx, outitem, outidx,
                      connect_next_unordered):
    conns = []
    parent = outitem.parent()
    new_mapper = parent.createNode('gatherbyindex')
    conns.append(makeConnection(innode, inidx,
                    new_mapper, 0, connect_next_unordered))
    conns.append(makeConnection(new_mapper, 0,
                    outitem, outidx, connect_next_unordered))
    # position between nodes and set colour and shape
    new_position = innode.position() + outitem.position()
    new_position = new_position * 0.5
    new_mapper.setPosition(new_position)
    return conns

def shouldMakeTopMapperConnection(ctrl, item, other_item):
    return ctrl and \
        isinstance(other_item, hou.TopNode) and \
        not other_item.isMapper() and \
        isinstance(item, hou.TopNode) and \
        not item.isMapper()

def inputOutOfRange(item, inidx):
    if isinstance(item, hou.VopNode):
        if inidx >= len(item.inputNames()):
            return True

    elif isinstance(item, hou.Node):
        if isinstance(item, hou.ApexNode):
            max = len(item.inputConnectors()) 
        else:
            max = item.type().maxNumInputs()

        if inidx >= max:
            return True
        elif inidx < 0 and not utils.isCableInput(item, inidx):
            if max <= utils.getNextInputIndex(item):
                return True

    elif isinstance(item, hou.NetworkDot):
        # Dots have only a single input.
        if inidx > 0:
            return True

    return False

def outputOutOfRange(item, outidx):
    if isinstance(item, hou.VopNode):
        if outidx >= len(item.outputNames()):
            return True

    elif isinstance(item, hou.Node):
        if isinstance(item, hou.ApexNode):
            max = len(item.outputConnectors()) 
        else:
            max = item.type().maxNumOutputs()

        if outidx >= max:
            return True
        elif outidx < 0:
            if max <= utils.getNextOutputIndex(item):
                return True

    elif isinstance(item, hou.NetworkDot):
        # Dots have only a single input.
        if outidx > 0:
            return True

    return False

def getNextAvailableInput(innode, inidx):
    # Advance to the next unconnected input.
    if inidx >= 0:
        inidx += 1
        inputs = innode.inputConnections()
        while [conn for conn in inputs if conn.inputIndex() == inidx]:
            inidx += 1

    return inidx

def getRootInputs(inputs):
    # For an output, only the root of chains (leaves) will be used.

    if len(inputs) < 2:
        return inputs

    visited = set()

    for input in inputs:
        # Immediate upstream nodes will be marked and removed later
        item = input[0]
        for c in item.outputConnections():
            visited.add(c.outputItem())

    return [
        o for o in inputs
        if o[0] not in visited
    ]


def getEndOutputs(outputs):
    # For multiple inputs, only the ends of chains (leaves) will be used.

    if len(outputs) < 2:
        return outputs

    visited = set()

    for output in outputs:
        # Immediate upstream nodes will be marked and removed later
        item = output[0]
        for c in item.inputConnections():
            visited.add(c.inputItem())

    return [
        o for o in outputs
        if o[0] not in visited
    ]


class BaseConnectHandler(base.ItemEventHandler):
    def __init__(self, uievent):
        base.ItemEventHandler.__init__(self, uievent)
        self.inputs = []
        self.outputs = []
        self.picked_output = None
        self.wires = []
        self.createddot = None
        self.seenmousedown = False
        if isinstance(uievent, MouseEvent):
            self.useconnectorsnapradius = False
            self.startmousepos = uievent.mousepos
        else:
            self.useconnectorsnapradius = True
            self.startmousepos = None
        self.subhandler = None
        self.selectnewconnections = False
        self.allowdisconnection = False
        self.startmultiinput = False
        self.destroyconnections = []
        self.isapex = uievent.editor.type() == hou.paneTabType.ApexEditor

    def sendEventToSubHandler(self, uievent, pending_actions):
        result = self.subhandler.handleEvent(uievent, pending_actions)
        if not isinstance(result, base.EventHandler):
            result = None
        self.subhandler = result
        self.buildPreviewWires(uievent)
        return self

    def handleTabMenuRequest(self, uievent, pending_actions):
        node_pos = uievent.editor.posFromScreen(uievent.mousepos)
        node_pos -= utils.getNewNodeHalfSize()
        if isinstance(uievent, KeyboardEvent):
            tabkey = uievent.key
        else:
            tabkey = 'Tab'
        pending_actions.append(PendingTabMenuAction(self.editor_updates))
        uievent.editor.openTabMenu(key = tabkey,
            branch = True,
            src_items = [it.item for it in self.outputs],
            src_connector_indexes = [it.index for it in self.outputs],
            dest_items = [it.item for it in self.inputs],
            dest_connector_indexes = [it.index for it in self.inputs],
            node_position = node_pos)

    def handleRadialMenuRequest(self, uievent, pending_actions):
        node_pos = uievent.editor.posFromScreen(uievent.mousepos)
        node_pos -= utils.getNewNodeHalfSize()

        pending_actions.append(PendingTabMenuAction(self.editor_updates))

        radialmenu.openRadialMenu(
            uievent,
            modal = True,
            branch = True,
            src_items = [it.item for it in self.outputs],
            src_connector_indexes = [it.index for it in self.outputs],
            dest_items = [it.item for it in self.inputs],
            dest_connector_indexes = [it.index for it in self.inputs],
            node_position = node_pos)

    def buildPendingItemsFromConnections(self):
        for conn in self.wires:
            if not self.iscopy:
                # Record the dot after the picked segment.
                self.destroyconnections.append(conn)
                self.inputs.append(makeCI(conn.outputItem(),
                                          conn.inputIndex(),
                                          conn))

        for conn in self.wires:
            # Record the dot before the picked segment.
            self.outputs.append(makeCI(conn.inputItem(),
                                       conn.inputItemOutputIndex(),
                                       conn))

        if len(self.wires) != 1 or \
           self.wires[0] != self.item:
            self.selectnewconnections = True

    def getDropTarget(self, uievent):
        if self.useconnectorsnapradius:
            radius = utils.getConnectorSnapRadius(uievent.editor)
        else:
            radius = 1
        items = utils.getPossibleDropTargets(uievent, radius)
        drop_target = NetworkComponent(None, '', 0)

        # If the user is holding down shift over an input (when we have inputs)
        # or an output (when we have outputs), then a click will add this new
        # input/output to our list. Don't try to treat this as completing the
        # connection.
        located = uievent.located
        if uievent.modifierstate.shift and not self.wires and \
           ((self.inputs and located.name in theInputConnectorNames) or \
            (self.outputs and located.name in theOutputConnectorNames)):
            return drop_target

        # Look for the closest connector that would complete our pending
        # connection operation. Dots are also valid drop targets that act
        # as proxies for the inputs/outputs of the wires that pass through
        # them.
        decorated_item = uievent.editor.decoratedItem()
        for item in items:
            # If the closest thing is an undecorated dot, accept the dot as a
            # drop target just to set it as the decorated item so we can then
            # snap to the dot input or output.
            if isinstance(item.item, hou.NetworkDot) and \
               decorated_item != item.item and \
               item.item != self.item:
                drop_target = item
                break

            # If the closest thing is a connector for a node, dot, or subnet
            # input, accept this drop target as long as it wouldn't result
            # in a connection loop from an item back to itself.
            if (isinstance(item.item, hou.Node) or \
                isinstance(item.item, hou.IndirectInput)) and \
                ((self.outputs and \
                  not [i for i in self.outputs if i.item == item.item] and \
                  item.name in theInputConnectorNames) or \
                 (self.inputs and \
                  not [i for i in self.inputs if i.item == item.item] and \
                  item.name in theOutputConnectorNames)):
                drop_target = item
                break

            # If we are dragging a single wire or the connectors are too small
            # to be drawn, we want to snap to node bodies, as long as the node
            # is not at either end of the wire being dragged, or matches the
            # item at the source of the input/output pending connection.
            if isinstance(item.item, hou.Node) and \
                item.name in theNodeBodyNames and \
                (not uievent.editor.isShowingConnectors() or \
                 (len(self.wires) == 1 and \
                  self.wires[0].inputNode() != item.item and \
                  self.wires[0].outputItem() != item.item)) and \
                ((self.outputs and \
                  not [i for i in self.outputs if i.item==item.item] and \
                  not inputOutOfRange(item.item, 0)) or \
                 (self.inputs and \
                  not [i for i in self.inputs if i.item==item.item] and \
                  not outputOutOfRange(item.item, 0))):
                # If we are dragging a single wire while zoomed out such that
                # connectors are not visible, fake the drop target based on
                # whether the mouse is above or below the actual node bounds
                # to connect to the input or output rather than through.
                if not uievent.editor.isShowingConnectors() and \
                   len(self.wires) == 1:
                    horizontal = utils.isNetworkHorizontal(uievent.editor.pwd())
                    rect = uievent.editor.itemRect(item.item)
                    pos = uievent.editor.posFromScreen(uievent.mousepos)
                    if ((horizontal and pos.x() > rect.max().x()) or \
                        (not horizontal and pos.y() < rect.min().y())) and \
                       not outputOutOfRange(item.item, 0):
                        drop_target = NetworkComponent(item.item, 'output', 0)
                    elif ((horizontal and pos.x() < rect.min().x()) or \
                          (not horizontal and pos.y() > rect.max().y())) and \
                         not inputOutOfRange(item.item, 0):
                        drop_target = NetworkComponent(item.item, 'input', 0)
                    else:
                        drop_target = item
                else:
                    drop_target = item
                break

        # If the user is holding down the alt key, clicking on any part of a
        # node should bring up a menu of choices, just like starting a new
        # connection operation. So just change the drop target.
        if uievent.modifierstate.alt and \
           isinstance(drop_target.item, hou.Node):
            drop_target = NetworkComponent(drop_target.item, 'node', 0)

        # If there is no drop target, but we have a decorated network dot,
        # check if the mouse is over the network dot's "expanded" area, in
        # which case return the dot's input or output as appropriate. This
        # way even with a very small snap radius, we can connect to a dot
        # without worrying about the decoration disappearing.
        if drop_target.item is None and \
           isinstance(decorated_item, hou.NetworkDot):
            pos = uievent.mousepos
            items = uievent.editor.networkItemsInBox(pos, pos, for_select=True)
            for item in items:
                item = NetworkComponent(*item)
                if item.item == decorated_item:
                    if self.inputs:
                        target_name = 'dotoutput'
                    else:
                        target_name = 'dotinput'
                    drop_target = NetworkComponent(item.item, target_name, 0)
                    break

        return drop_target

    def handleEvent(self, uievent, pending_actions):

        try:
            #获取上下文点击节点的 input output或wave
            if uievent.selected.item != None:
                global context_wave_connect
                context_wave_connect = uievent.selected
        except:
            pass
        '''
        MouseEvent(
        editor=<hou.NetworkEditor copy_of_panetab12_2>, eventtype='mouseup', 
        selected=NetworkComponent(item=<hou.ObjNode of type null at /obj/null1>, name='output', index=0), 
        located=NetworkComponent(item=<hou.ObjNode of type null at /obj/null1>,name='output', index=0), 
        mousepos=<hou.Vector2 [1097, 257]>, mousestartpos=<hou.Vector2 [1097, 257]>, 
        mousestate=MouseState(lmb=0, mmb=0, rmb=0), dragging=0, wheelvalue=100,
        modifierstate=ModifierState(alt=0, ctrl=0, shift=0), time=25715.796

        MouseEvent(editor=<hou.NetworkEditor copy_of_panetab12_2>, eventtype='mousedrag',
        selected=NetworkComponent(item=<hou.OpNodeConnection from null1 output 0 to null2 input 0>, name='wire', index=0),
        located=NetworkComponent(item=<hou.OpNodeConnection from null1 output 0 to null2 input 0>, name='wire', index=0),
        mousepos=<hou.Vector2 [1019, 389]>, mousestartpos=<hou.Vector2 [1019, 383]>,
        mousestate=MouseState(lmb=1, mmb=0, rmb=0), dragging=1, wheelvalue=100, 
        modifierstate=ModifierState(alt=0, ctrl=0, shift=0), time=36488.5)
        TimerEvent(editor=<hou.NetworkEditor copy_of_panetab12_2>, eventtype='timer', timerid=56)
        )

        '''

        # Check if the user wants to enter the scroll state.
        if states.isScrollStateEvent(uievent):
            return states.ScrollStateHandler(uievent, self)

        editor = uievent.editor

        # If we have established a subhandler, let it handle the events
        # until it declares itself done.
        if self.subhandler is not None:
            return self.sendEventToSubHandler(uievent, pending_actions)

        # The tab menu can be opened while wiring to place a new node.
        if isinstance(uievent, KeyboardEvent) and \
                uievent.eventtype.endswith('keyhit'):

           if display.setKeyPrompt(editor, uievent,
                                   'h.pane.wsheet.add_op'):
                self.handleTabMenuRequest(uievent, pending_actions)

           elif display.setKeyPrompt(editor, uievent,
                                     'h.pane.wsheet.radial:network-default'):
                self.handleRadialMenuRequest(uievent, pending_actions)

           return None

        if isinstance(uievent, KeyboardEvent) and \
           uievent.eventtype == 'keydown' and \
           hou.ui.isKeyMatch(uievent.key, 'h.pane.wsheet.view_mode'):
            self.subhandler = states.ViewStateHandler(uievent)
            return self.sendEventToSubHandler(uievent, pending_actions)

        if uievent.eventtype == 'gesture':
            view.scaleWithPinch(uievent)
            self.buildPreviewWires(uievent)
            return self

        # Ignore anything else that isn't a mouse event.
        if not isinstance(uievent, MouseEvent):
            return self

        if uievent.eventtype == 'mousewheel':
            if uievent.wheelstate:
                view.panWithMouseWheel(uievent)
            else:
                view.scaleWithMouseWheel(uievent)

            self.buildPreviewWires(uievent)
            return self

        # If our index is None, we haven't been through here before.
        # Figure out which input/output index the user wants to connect to.
        first_event = False
        if not self.inputs and not self.outputs:
            first_event = True
            if not self.initializePendingConnections(
                uievent.selected, uievent.eventtype,
                uievent.modifierstate):
                return None

        # Watch how far the mouse moves from its original position. Only after
        # it has moved some distance do we want to start using the large
        # connector snap radius value (to prevent an accidental double click
        # ona connector from creating a wire to a nearby node).
        if not self.useconnectorsnapradius:
            dist = self.startmousepos.distanceTo(uievent.mousepos)
            if dist > utils.getConnectorDistanceBeforeSnapping():
                self.useconnectorsnapradius = True

        if uievent.eventtype == 'mousedown':
            # This is no longer a click-drag-release operation.
            self.seenmousedown = True
            # Check for navigation mouse events (overview, pan, or zoom).
            if uievent.selected.name.startswith('overview'):
                self.subhandler = base.OverviewMouseHandler(uievent)
                return self.sendEventToSubHandler(uievent, pending_actions)

            elif base.isPanEvent(uievent):
                self.subhandler = base.ViewPanHandler(uievent)
                return self.sendEventToSubHandler(uievent, pending_actions)

            elif base.isScaleEvent(uievent):
                self.subhandler = base.ViewScaleHandler(uievent)
                return self.sendEventToSubHandler(uievent, pending_actions)

            elif uievent.mousestate.lmb and \
                 uievent.modifierstate.shift and \
                 not self.wires:
                # Shift click an input when we already have inputs (or an
                # output when we already have outputs) adds the clicked item
                # to our list of inputs (or outputs). Clear self.seenmousedown
                # since we want to allow click-drag connetions from this late
                # addition to our connection request.
                if self.inputs and \
                   uievent.selected.name in theInputConnectorNames:
                    newin = makeCI(uievent.located.item, uievent.located.index)
                    if newin in self.inputs:
                        self.inputs.remove(newin)
                        if not self.inputs:
                            return None
                    else:
                        self.inputs.append(newin)
                    self.seenmousedown = False

                elif self.outputs and \
                     uievent.selected.name in theOutputConnectorNames:
                    newout = makeCI(uievent.located.item, uievent.located.index)
                    if newout in self.outputs:
                        self.outputs.remove(newout)
                        if not self.outputs:
                            return None
                    else:
                        self.outputs.append(newout)
                    self.seenmousedown = False

        # Start auto-scrolling if we are near the edge.
        if uievent.eventtype == 'mousedrag':
            autoscroll.startAutoScroll(self, uievent, pending_actions)

        # Snap to the nearest connector.
        if first_event or \
           uievent.eventtype == 'mousedrag' or \
           uievent.eventtype == 'mousemove':
            self.destination = self.getDropTarget(uievent)
            # Network dots bring up their decorations so we can choose to
            # feed the wire into the input or output of the dot.
            if isinstance(self.destination.item, hou.NetworkDot):
                # We only accept dot body drop targets that don't match the
                # current decorated item. So use this as our cue to set or
                # change the current decorated item.
                if self.destination.name == 'dot':
                    display.setDecoratedItem(uievent.editor,
                            self.destination.item,
                            pending_actions,
                            True, False)
                    self.destination = NetworkComponent(None, '', 0)
            else:
                display.setDecoratedItem(uievent.editor, None,
                        pending_actions, False, False)
            editor.setDropTargetItem(*self.destination)
            self.buildPreviewWires(uievent)

        elif uievent.eventtype == 'mouseup':
            # print('mouseup', self.destination)
            if self.destination.item is not None:
                # Clear the decorated item in case we had it set on a dot.
                display.setDecoratedItem(uievent.editor, None,
                        pending_actions, False, False)
                dest = self.destination
                # Clicked on something. Make the requested connection.
                self.connect(uievent, dest.item, dest.index, dest.name)
                return None

            elif uievent.modifierstate.alt and \
                 (self.inputs or len(self.outputs) == 1) and \
                 not self.wires and \
                 utils.supportsNetworkDots(editor.pwd()):
                # Alt-clicked in empty space for a new wire(s). Create a
                # dot at this location.
                pos = uievent.editor.posFromScreen(uievent.mousepos)
                with hou.undos.group('Create Network Dot', uievent.editor):
                    dot = editor.pwd().createNetworkDot()
                    dot.setPosition(pos)
                    dot.setPinned(True)
                    if len(self.outputs) == 1:
                        self.connect(uievent, dot, 0, 'dotinput')
                        self.item = dot
                        self.initializePendingConnections(
                            NetworkComponent(dot, 'dotoutput', 0),
                            uievent.eventtype,
                            uievent.modifierstate)

                    elif self.inputs:
                        self.connect(uievent, dot, 0, 'dotoutput')
                        self.item = dot
                        self.initializePendingConnections(
                            NetworkComponent(dot, 'dotinput', 0),
                            uievent.eventtype,
                            uievent.modifierstate)
                    self.createddot = dot

            elif uievent.modifierstate.alt and \
                 not self.inputs and not self.wires and self.outputs:
                # Alt-clicked in empty space for a new set of input wires.
                # Create a merge node at this location, and resume the wiring
                # operation with the output of that merge.
                pwd = uievent.editor.pwd()
                mergetype = theMergeNodeTypes.get(pwd.childTypeCategory(), None)
                if mergetype is not None:
                    with hou.undos.group('Create Merge Node', uievent.editor):
                        setdisplayflag = False
                        setrenderflag = False
                        merge = pwd.createNode(mergetype)
                        # Connect the nodes to the merge input.
                        for output in self.outputs:
                            merge.setNextInput(output.item, output.index)
                            # If any inputs have the display flag set, move the
                            # display flag to the merge node.
                            if isinstance(output.item, hou.SopNode) and \
                               output.item.isDisplayFlagSet():
                                setdisplayflag = True
                                setrenderflag = output.item.isRenderFlagSet()
                        if setdisplayflag:
                            merge.setDisplayFlag(True)
                        if setrenderflag:
                            merge.setRenderFlag(True)

                        # Get size of the new node
                        uievent.editor._requestGraphUpdate()
                        mergerect = uievent.editor.itemRect(merge, False)
                        pos = uievent.editor.posFromScreen(uievent.mousepos)
                        pos -= mergerect.size() * 0.5
                        merge.setPosition(pos)
                    self.outputs = [makeCI(merge, 0)]
                    self.picked_output = makeCI(merge, 0)

            elif uievent.modifierstate.alt and self.wires and \
                 utils.supportsNetworkDots(editor.pwd()):
                # Alt-clicked while dragging existing wires around. We can
                # only handle this if all inputs are the same. Otherwise we
                # ignore the click.
                for i in range(1, len(self.inputs)):
                    if self.inputs[i].conn.inputItem() != \
                            self.inputs[0].conn.inputItem() or \
                       self.inputs[i].conn.inputItemOutputIndex() != \
                            self.inputs[0].conn.inputItemOutputIndex():
                        return self

                pos = uievent.editor.posFromScreen(uievent.mousepos)
                with hou.undos.group('Create Network Dot', uievent.editor):
                    dot = editor.pwd().createNetworkDot()
                    dot.setPosition(pos)
                    dot.setPinned(True)
                    dot.setInput(self.inputs[0].conn.inputItem(),
                        self.inputs[0].conn.inputItemOutputIndex())
                    # Rearrange the connections to move everything from the
                    # original input item to the new dot.
                    self.connect(uievent, dot, 0, 'dotoutput')
                    # Reset this operation as if we had clicked on the wires
                    # being output from the new dot.
                    self.inputs = []
                    self.outputs = []
                    self.item = dot.outputConnections()[0]
                    self.initializePendingConnections(
                        NetworkComponent(dot, 'dotinput', 0),
                        uievent.eventtype,
                        uievent.modifierstate)
                    self.createddot = dot

            elif uievent.modifierstate.ctrl:
                # Ctrl-clicked in empty space. Bring up the tab menu.
                self.handleTabMenuRequest(uievent, pending_actions)
                return None

            elif uievent.modifierstate.shift and \
                 not uievent.located.item:
                #shift拖线松手 触发RadialMenu
                # print('shift拖线松手 触发RadialMenu')
                # print( out_or_in , node , index)
                # print(uievent.mousepos)
                # pane = uievent.editor

                global menu
                zjyitem = Zjy_create_radialmenu_dict(uievent,context_wave_connect)
                # hou_Radialmenu_dict = zjyitem.get_hou_radialmenu_item()
                zjy_Radialmenu_dict = zjyitem.get_zjyRadialmenu_dict()
                # print(zjyitem.get_item())  
                menu = Zjy_radialmenu( uievent ,context_wave_connect,zjy_Radialmenu_dict)
                # menu.itemClicked.connect(self.menuItemClicked)
                menu.show()
             

                # self.handleRadialMenuRequest(uievent, pending_actions)
                return None

            elif not uievent.modifierstate.alt and \
                 not uievent.modifierstate.shift and \
                 self.seenmousedown:
                # Finished a click on nothing that this handler saw the
                # start of. Perform a disconnection from an input if allowed.
                # The test for seeing the mouse down is so that dragging and
                # releasing from an input connector won't do a disconnect.
                # If a modifier key is down, this is probably an accidental
                # click or missed click, so don't cancel everything.
                if self.allowdisconnection:
                    if self.inputs:
                        self.connect(uievent, None, 0, None)
                return None

        return self

    def buildPreviewWires(self, uievent):
        if isinstance(uievent, MouseEvent):
            connections = []
            dest_in_inputs = False
            dest_in_outputs = False
            if self.destination.name in theNodeBodyNames:
                if [i for i in self.inputs if i.item == self.destination.item]:
                    dest_in_inputs = True
                if [i for i in self.outputs if i.item == self.destination.item]:
                    dest_in_outputs = True

            wires = []
            wires.extend(self.buildPreviewWiresToInputs(uievent,
                dest_in_inputs, dest_in_outputs))
            wires.extend(self.buildPreviewWiresToOutputs(uievent,
                dest_in_inputs, dest_in_outputs))

            self.editor_updates.setOverlayShapes(wires)

    def buildPreviewExistingPath(self, conn, spos, sdir, epos, edir):
        wires = []
        zero = hou.Vector2(0.0, 0.0)
        clr = hou.ui.colorFromName('GraphPreSelection')
        # Draw from the start pos to teh end pos.
        wire = hou.NetworkShapeConnection(
                        spos, sdir, epos, edir,
                        clr, 1.0)
        wires.append(wire)

        return wires

    def buildPreviewWiresToInputs(self, uievent,
                                  dest_in_inputs, dest_in_outputs):
        wires = []
        dest_is_input = self.destination.name in theInputConnectorNames
        dest_is_node = self.destination.name in theNodeBodyNames
        dest_is_dot = self.destination.name == 'dotoutput'
        dest_is_none = self.destination.item is None
        for (item, idx, conn) in self.inputs:
            if idx < 0 and not utils.isCableInput(item, idx):
                idx = utils.getNextInputIndex(item)
            pos = uievent.editor.itemInputPos(item, idx)
            indir = uievent.editor.itemInputDir(item, idx)
            outdir = -indir

            # Figure out the location of the output (source) end of the
            # preview wire.
            if dest_is_dot:
                # Wires go right to the center of dots at any angle.
                dtpos = self.destination.item.position()
                childcategory = uievent.editor.pwd().childTypeCategory()
                if childcategory == hou.vopNodeTypeCategory():
                    outdir = hou.Vector2(1.0, 0.0)
                else:
                    outdir = hou.Vector2(0.0, -1.0)
            elif not dest_is_none and dest_is_node and \
                not dest_in_inputs and \
                len(self.destination.item.outputConnectors()) > 0:
                dtrect = uievent.editor.itemRect(self.destination.item)
                dtpos = dtrect.center()
            elif not dest_is_none and \
                not dest_is_input and \
                not dest_is_node:
                dtpos = uievent.editor.itemOutputPos(
                        self.destination.item,
                        self.destination.index)
            elif dest_is_none:
                # Wires go right to the mouse when it is near nothing.
                dtpos = uievent.mousepos
                dtpos = uievent.editor.posFromScreen(dtpos)
                outdir = hou.Vector2(0.0, 0.0)
            else:
                continue

            # Build a preview wire from the source to the dest, following the
            # existing wire path if there is one.
            wires.extend(self.buildPreviewExistingPath(
                conn, dtpos, outdir, pos, indir))

        return wires

    def buildPreviewWiresToOutputs(self, uievent,
                                   dest_in_inputs, dest_in_outputs):
        wires = []
        dest_is_input = self.destination.name in theInputConnectorNames
        dest_is_node = self.destination.name in theNodeBodyNames
        dest_is_dot = self.destination.name == 'dotinput'
        dest_is_none = self.destination.item is None
        for (item, idx, conn) in self.outputs:
            pos = uievent.editor.itemOutputPos(item, idx)
            outdir = uievent.editor.itemOutputDir(item, idx)
            indir = -outdir

            # Figure out the location of the input (destination) end of the
            # preview wire.
            if dest_is_dot:
                # Wires go right to the center of dots at any angle.
                dtpos = self.destination.item.position()
                childcategory = uievent.editor.pwd().childTypeCategory()
                if childcategory == hou.vopNodeTypeCategory():
                    indir = hou.Vector2(-1.0, 0.0)
                else:
                    indir = hou.Vector2(0.0, 1.0)
            elif not dest_is_none and dest_is_node and \
                not dest_in_outputs and \
                len(self.destination.item.inputConnectors()) > 0:
                dtrect = uievent.editor.itemRect(self.destination.item)
                dtpos = dtrect.center()
            elif not dest_is_none and \
                dest_is_input and \
                not dest_is_node:
                if self.destination.name == 'inputgroup':
                    groups = self.destination.item.inputGroupNames()
                    group = groups[self.destination.index]
                    inputs = self.destination.item.inputsInGroup(group)
                    input_index = inputs[0]
                else:
                    input_index = self.destination.index
                dtpos = uievent.editor.itemInputPos(
                        self.destination.item,
                        input_index)
            elif dest_is_none:
                # Wires go right to the mouse when it is near nothing.
                dtpos = uievent.mousepos
                dtpos = uievent.editor.posFromScreen(dtpos)
                indir = hou.Vector2(0.0, 0.0)
            else:
                continue

            # Build a preview wire from the source to the dest, following the
            # existing wire path if there is one.
            wires.extend(self.buildPreviewExistingPath(
                conn, pos, outdir, dtpos, indir))

        return wires

    def connect(self, uievent, other_item, other_index, other_name = None):
        # Extract useful information from the passed in uievent.
        ctrl = uievent.modifierstate.ctrl
        editor = uievent.editor

        if other_name == 'multiinput':
            connect_next_unordered = True
        elif self.startmultiinput:
            connect_next_unordered = True
        else:
            connect_next_unordered = False

        if isinstance(other_item, hou.NetworkDot):
            other_dot = other_item
        else:
            other_dot = None

        if other_name == 'inputgroup':
            other_is_group = True
        else:
            other_is_group = False

        if other_name in theInputConnectorNames:
            other_is_input = True
        else:
            other_is_input = False

        showed_menu = False
        if other_name in theNodeBodyNames:
            other_index = None
            # We have been asked to connect to a node, but with a connection
            # index of 'None'. Where -1 indicates 'next input', None
            # indicates we have no way of knowing which connection, probably
            # because the user clicked on a node instead of a connector.
            if len(self.wires) == 1:
                utils.insertItemsIntoWire(self.wires[0],
                    [other_item], [other_item],
                    remove_existing_connections=False,
                    editor=uievent.editor)
                return

            elif self.inputs and self.outputs:
                other_in_inputs = False
                other_in_outputs = False
                if [i for i in self.inputs if i.item == other_item]:
                    other_in_inputs = True
                if [i for i in self.outputs if i.item == other_item]:
                    other_in_outputs = True

                if not other_in_inputs and not other_in_outputs:
                    result = utils.getPopupMenuResult(
                        popupmenus.AllInputsAndOutputsMenu(self, other_item))
                    if result is not None:

                        conntype, name = result.split(':')
                        if conntype == 'input':
                            other_is_input = True
                        else:
                            other_is_input = False
                        result = name

                elif not other_in_inputs:
                    result = utils.getPopupMenuResult(
                        popupmenus.AllOutputsMenu(self, other_item))
                    other_is_input = False

                elif not other_in_outputs:
                    result = utils.getPopupMenuResult(
                        popupmenus.AllInputsMenu(self, other_item))
                    other_is_input = True
                showed_menu = True

            elif self.inputs:
                result = utils.getPopupMenuResult(
                    popupmenus.AllOutputsMenu(self, other_item))
                other_is_input = False
                showed_menu = True

            else:
                result = utils.getPopupMenuResult(
                    popupmenus.AllInputsMenu(self, other_item))
                other_is_input = True
                showed_menu = True

        elif other_dot is not None:
            # Dots can be either an input or output.
            if other_name == 'dotinput':
                other_is_input = True

            else:
                other_is_input = False

        elif isinstance(other_item, hou.VopNode) and other_is_group:
            group = other_item.inputGroupNames()[other_index]
            # If the group is expanded, connect to the first input in the
            # group. If it is collapsed, bring up a menu.
            if other_item.isInputGroupExpanded(group):
                other_is_group = False
                other_index = other_item.inputsInGroup(group)[0]

            else:
                result = utils.getPopupMenuResult(
                    popupmenus.VopGroupInputsMenu(self,other_item,other_index))
                showed_menu = True

        elif isinstance(other_item, hou.VopNode) and other_index < 0:
            # We were asked to connect to the 'more' input or output of a
            # VOP node. We want to pop up a menu of all hidden inputs/outputs
            # on the VOP. Only when the user picks from that menu do we want
            # to actually make a connection.
            if other_is_input:
                result = utils.getPopupMenuResult(
                    popupmenus.VopHiddenInputsMenu(self, other_item))
                showed_menu = True

            else:
                result = utils.getPopupMenuResult(
                    popupmenus.VopHiddenOutputsMenu(self, other_item))
                showed_menu = True

        if showed_menu:
            if result is not None:
                if isinstance(other_item, hou.Node):
                    if other_is_input:
                        other_index = other_item.inputIndex(result)
                    else:
                        other_index = other_item.outputIndex(result)
            else:
                return

        # Don't allow a node to connect to itself.
        if other_is_input:
            if not self.outputs:
                return
            if [i for i in self.outputs if i.item == other_item]:
                return
        else:
            if not self.inputs:
                return
            if [i for i in self.inputs if i.item == other_item]:
                return

        # Check if we are about to recreate one connection we have
        # been told to destroy, in which case just bail out.
        if len(self.destroyconnections) == 1:
            conn = self.destroyconnections[0]
            if other_is_input:
                if conn.outputItem() == other_item and \
                   conn.inputIndex() == other_index:
                    return
            else:
                if conn.inputItem() == other_item and \
                   conn.inputItemOutputIndex() == other_index:
                    return

        with hou.undos.group('Connect nodes', editor):
            conns = []
            if other_is_input:
                outputs = self.outputs

                if (isinstance(other_item, hou.VopNode) or
                    isinstance(other_item, hou.ApexNode)):
                    pass
                elif inputOutOfRange(other_item,
                         getNextAvailableInput(other_item, other_index)):
                    # Connecting to a single input. Prefer picked output
                    if self.picked_output:
                        outputs = [self.picked_output]
                else:
                    # Connecting to multi-inputs. Use selection
                    outputs = getEndOutputs(outputs)

                for (outitem, idx, conn) in outputs:
                    if inputOutOfRange(other_item, other_index):
                        break
                    if shouldMakeTopMapperConnection(ctrl, other_item, outitem):
                        conns.extend(makeTopMapperConnection(
                                        other_item, other_index, outitem, idx,
                                        connect_next_unordered))
                    else:
                        conns.append(makeConnection(
                                        other_item, other_index, outitem, idx,
                                        connect_next_unordered))
                    other_index = getNextAvailableInput(other_item, other_index)

            else:
                inputs = self.inputs

                if (isinstance(other_item, hou.VopNode) or
                    isinstance(other_item, hou.ApexNode)):
                    pass
                elif len(self.wires) > 0:
                    # Moving existing wires. Try to maintain the same
                    # number of wires
                    pass
                else:
                    # Use selection
                    inputs = getRootInputs(inputs)

                for (innode, idx, conn) in inputs:
                    if shouldMakeTopMapperConnection(ctrl, other_item, innode):
                        conns.extend(makeTopMapperConnection(
                                        innode, idx, other_item, other_index,
                                        connect_next_unordered))
                    else:
                        conns.append(makeConnection(
                                        innode, idx, other_item, other_index,
                                        connect_next_unordered))
            # Remove any None values from failed connection attempts.
            conns = [c for c in conns if c is not None]

            # Any connections that were flagged for destruction that haven't
            # already been destroyed during the creation of the new connections
            # now need to be destroyed.
            for conn in conns:
                for dconn in self.destroyconnections:
                    if conn.outputItem() == dconn.outputItem() and \
                       conn.inputIndex() == dconn.inputIndex():
                        self.destroyconnections.remove(dconn)
                        break
            utils.deleteConnections(self.destroyconnections, False, editor=editor)

            if self.selectnewconnections:
                view.modifySelection(None, editor, conns)

            # If we have a dot that we created (with an alt-click), it should
            # now be safely wired to something, so unpin it.
            if self.createddot is not None:
                self.createddot.setPinned(False)
            utils.cleanupDisconnectedItems(editor.pwd())

    def getPrompt(self, uievent):
        # TODO: refactor for translation

        if not isinstance(uievent, MouseEvent):
            return None

        if uievent.dragging:
            prompt = \
                'Drag to a connector to finish wire, or press ESC to cancel'
        elif self.inputs or len(self.outputs) == 1:
            prompt = \
                'Click a connector to finish wire, or press ESC to cancel'

            if not self.isapex:
                prompt += '\nAlt-click to add a dot'
        else:
            pwd = uievent.editor.pwd()
            mergetype = theMergeNodeTypes.get(pwd.childTypeCategory(), None)
            prompt = 'Click a connector to finish wire, or press ESC to cancel'
            if mergetype is not None:
                prompt += '\nAlt-click to add a ' + mergetype + ' node'

        return prompt


class ItemConnectHandler(BaseConnectHandler):
    def __init__(self, uievent):
        BaseConnectHandler.__init__(self, uievent)

    def initializePendingConnections(self, selected, eventtype, modifierstate):
        index = None
        isinput = selected.name in theInputConnectorNames
        self.allowdisconnection = isinput
        self.startmultiinput = (selected.name == 'multiinput')

        # Check for a click on a node (not a connector). Provide a menu
        # of connectors to choose from.
        if eventtype == 'mouseup' and \
           isinstance(self.item, hou.Node) and \
           selected.name in theNodeBodyNames:
            result = utils.getPopupMenuResult(
                popupmenus.AllInputsAndOutputsMenu(self, self.item))
            if result is not None:
                conntype, name = result.split(':')
                if conntype == 'input':
                    isinput = True
                    index = self.item.inputIndex(name)
                else:
                    isinput = False
                    index = self.item.outputIndex(name)

        # Check for a click on a VOP 'More...' input or output. Provide
        # a menu to choose which connector was intended.
        elif eventtype == 'mouseup' and \
             isinstance(self.item, hou.VopNode) and \
             selected.index < 0:
            if isinput:
                result = utils.getPopupMenuResult(
                    popupmenus.VopHiddenInputsMenu(self, self.item))
                if result is not None:
                    index = self.item.inputIndex(result)
            else:
                result = utils.getPopupMenuResult(
                    popupmenus.VopHiddenOutputsMenu(self, self.item))
                if result is not None:
                    index = self.item.outputIndex(result)

        # Drag or click on a connector, use the selected item index.
        elif selected.name in theInputConnectorNames or \
             selected.name in theOutputConnectorNames:
            index = selected.index

        if index is not None:
            # Set up a pending connection from every picked node, if the
            # node has the required input or output connector.
            if self.item.isSelected():
                picked_items = self.item.parent().selectedItems()
                for item in picked_items:
                    if isinstance(item, hou.Node):
                        if isinput and utils.isCableInput(item, index):
                            self.inputs.append(makeCI(item, index))
                        elif isinput and index < 0:
                            # We want to connect to the 'next' input. Make
                            # sure this node has space for another input.
                            nextidx = utils.getNextInputIndex(item)
                            if not inputOutOfRange(item, nextidx):
                                self.inputs.append(makeCI(item, index))
                        elif isinput and \
                             not inputOutOfRange(item, index):
                            # Connecting to a specific input. Make sure
                            # this node has that many inputs.
                            self.inputs.append(makeCI(item, index))
                        elif not isinput and \
                             not outputOutOfRange(item, index):
                            # Connecting to a specific output. Make sure
                            # this node has that many outputs.
                            self.outputs.append(makeCI(item, index))

                            if not self.picked_output:
                                self.picked_output = makeCI(self.item, index)

                    elif isinstance(item, hou.IndirectInput):
                        # Indirect inputs can only output from index 0. Dots
                        # can also accept an input to index 0.
                        if isinput and index == 0 and \
                           isinstance(item, hou.NetworkDot):
                            self.inputs.append(makeCI(item, index))
                        elif not isinput and index == 0:
                            self.outputs.append(makeCI(item, index))

            else:
                if isinput:
                    self.inputs = [makeCI(self.item, index)]
                else:
                    self.outputs = [makeCI(self.item, index)]

            return True

        return False

class WireConnectHandler(BaseConnectHandler):
    def __init__(self, uievent):
        BaseConnectHandler.__init__(self, uievent)

    def getUnpinnedDotDepth(self, wire):
        initem = wire.inputItem()
        extra_depth = 0
        if isinstance(initem, hou.NetworkDot) and not initem.isPinned():
            conns = initem.inputConnections()
            if conns:
                extra_depth = self.getUnpinnedDotDepth(conns[0])

        return 1 + extra_depth

    def getSiblingWires(self, wires, primary_wire):
        outwires = []
        depth = self.getUnpinnedDotDepth(primary_wire)
        for wire in wires:
            if self.getUnpinnedDotDepth(wire) == depth:
                outwires.append(wire)

        return outwires

    def initializePendingConnections(self, selected, eventtype, modifierstate):
        # Reconfigure an existing connection.
        if isinstance(self.item, hou.NodeConnection):
            wires = utils.getSelectedWires(self.start_uievent.editor, self.item)
            self.wires = self.getSiblingWires(wires, self.item)

            self.iscopy = modifierstate.shift
            self.buildPendingItemsFromConnections()

            return True

        return False

class WireMenuConnectHandler(WireConnectHandler):
    def __init__(self, uievent, wires, iscopy):
        BaseConnectHandler.__init__(self, uievent)
        self.wires = self.getSiblingWires(wires, uievent.selected.item)
        self.iscopy = iscopy

    def initializePendingConnections(self, selected, eventtype, modifierstate):
        self.buildPendingItemsFromConnections()
        return True

