from builtins import next
from past.utils import old_div
import hou
import math
import traceback
import pdgd
import nodegraphbase as base
import nodegraphpopupmenus as popupmenus
import nodegraphautoscroll as autoscroll
import nodegraphflags as flags
import nodegraphgestures as gestures
import nodegraphhotkeys as hotkeys
import nodegraphconnect as connect
import nodegraphdisplay as display
import nodegraphfastfind as fastfind
import nodegraphpalettes as palettes
import nodegraphprefs as prefs
import nodegraphradialmenu as radialmenu
import nodegraphsnap as snap
import nodegraphstates as states
import nodegraphui as ui
import nodegraphutils as utils
import nodegraphview as view
import nodegraphtopui as topui
from canvaseventtypes import *

try:
    from ZJYRadialMenu.Zjy_RadialMenu import *
    # import Zjy_radialmenu
    print('欢迎使用ZJY Radial Menu！')
except:
    print('import RadialMenu error')
    print(traceback.format_exc())



# print('nodegraph.py!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
theFlagDecorators = ( 'flag', 'flagindicator' )
theFlagTogglers = ( 'flag', 'flagindicator', 'footerflag' )
theNodeSelectors = ( 'node', 'connectorarea', 'preview', 'footer' )
theNodeDraggers = ( 'node', 'connectorarea', 'inputgroup',
                    'flagindicator', 'preview', 'footer' )
theNodeInfoPoppers = ( 'node', 'connectorarea',
                    'flagindicator', 'preview', 'footer', 'input', 'output' )
theInfoTogglers = ( 'info', 'indirectinputinfo' )
theFlyoutExpansions = ( 'nodeexpanded', 'indirectinputexpanded', 'dotexpanded' )
thePaletteBorders = ( 'colorpaletteborder', 'shapepaletteborder' )
thePaletteBackgrounds = ( 'colorpalette', 'shapepalette' )
theSkipDecorators = (
    'input', 'inputgroup', 'connectorarea',
    'output', 'multiinput', 'name',
    'preview', 'previewplane', 'footer', 'footerflag',
    'taskgraphworkitem'
)
theFlyoutParts = (
    'nodeexpanded', 'info', 'flag',
    'indirectinputexpanded', 'indirectinputinfo',
    'dotexpanded', 'dotinput', 'dotoutput'
)
theBackgroundImageElements = (
    'backgroundimage',
    'backgroundimageborder',
    'backgroundimagedelete',
    'backgroundimagelink',
    'backgroundimagebrightness'
)
theBackgroundImageDraggables = (
    'backgroundimage',
    'backgroundimageborder',
    'backgroundimagelink',
    'backgroundimagebrightness'
)

def handleEvent(uievent, last_handler_coroutine):
    """
        Handles events coming from the Network Editor.
        Dispatch events directed at specific graph items,
        and handle events not directed at a particular graph item.
    """
    # hou.ApexEditor is not a class
    if (not uievent.editor or uievent.editor.type() not in (
            hou.paneTabType.ApexEditor,
            hou.paneTabType.NetworkEditor)):
        return None

    handler_coroutine = last_handler_coroutine
    if handler_coroutine is None:
        volatile_hotkeys = []
        volatile_hotkeys.append('h.pane.wsheet.view_mode')
        volatile_hotkeys.append('h.pane.wsheet.select_mode')
        volatile_hotkeys.append('h.pane.wsheet.layout_mode')
        volatile_hotkeys.append('h.pane.wsheet.flag1_mode')
        volatile_hotkeys.append('h.pane.wsheet.flag2_mode')
        volatile_hotkeys.append('h.pane.wsheet.flag3_mode')
        volatile_hotkeys.append('h.pane.wsheet.flag4_mode')
        volatile_hotkeys.append('h.pane.wsheet.bypass_mode')
        volatile_hotkeys.append('h.pane.wsheet.visualize_mode')
        volatile_hotkeys.append('h.pane.wsheet.cut_wires_mode')
        volatile_hotkeys.append('h.pane.wsheet.stitch_mode')
        volatile_hotkeys.append('h.pane.wsheet.drop_on_wire_mode')
        uievent.editor.setVolatileHotkeys(volatile_hotkeys)

        uievent.editor.setCursorMap(utils.getCursorMap())
        uievent.editor.setDefaultCursor(None)
        uievent.editor.setNetworkBoxPendingRemovals([])
        uievent.editor.setDragSourceData([])
        handler_coroutine = handleEventCoroutine()
        next(handler_coroutine)

    # If we are here recursively as a result of the handler running some
    # code already, we have to skip this event.
    if not handler_coroutine.gi_running:
        try:
            handler_coroutine.send(uievent)
        except StopIteration:
            handler_coroutine = None

    return handler_coroutine

def handleEventCoroutine():
    event_handler = None
    pending_actions = []
    keep_state = True
    while keep_state:
        # Wait for the next event to come in from handleEvent
        uievent = yield
        editor = uievent.editor
        editor_updates = utils.EditorUpdates()

        # Hitting the escape key cancels everything. Clear all state by
        # exiting this function.
        if isinstance(uievent, KeyboardEvent) and \
           display.setKeyPrompt(editor, uievent,
                                'h.pane.wsheet.cancel'):
            if event_handler is None:
                            # Cancel TOP cook
                pwd = uievent.editor.pwd()
                if isinstance(pwd, hou.TopNode) or \
                   (isinstance(pwd, hou.SopNode) and \
                   pwd.type().name() == "topnet"):
                    topui.cancelCookWithConfirm(pwd)
                elif isinstance(uievent.editor.currentNode(), hou.TopNode):
                    topui.cancelCookWithConfirm(uievent.editor.currentNode())
            else:
                event_handler = None
                keep_state = False

        # Changing networks is like hitting Escape. It should cancel any
        # ongoing user actions.
        elif isinstance(uievent, ContextEvent):
            from nodegraphrename import RENAME_WINDOW_KEY
            oldpath = uievent.oldcontext
            newpath = uievent.context
            view.handleNetworkChange(editor, oldpath, newpath)
            renamewindow = editor.eventContextData().get(RENAME_WINDOW_KEY)
            if renamewindow and renamewindow.isVisible():
                renamewindow.update()
            event_handler = None
            keep_state = False

        # Clearing our file is like hitting Escape. It should cancel any
        # ongoing user actions.
        elif isinstance(uievent, ContextClearEvent):
            view.clearViewBoundsData(editor, uievent.context)
            event_handler = None
            keep_state = False

        # The initialization event is called once when the NNE pane is
        # first created.
        elif isinstance(uievent, InitializationEvent):
            prefs.registerPreferences(uievent.editor)

        else:
            try:
                if event_handler is None:
                    event_handler = createEventHandler(uievent, pending_actions)

                if isinstance(event_handler, base.EventHandler):
                    event_handler = event_handler.handleEvent(uievent,
                                                              pending_actions)
                    # If we finish off an event handler, clear out any
                    # state data on the editor that is always local to a
                    # single event handler.
                    if event_handler is None:
                        uievent.editor.setNetworkBoxPendingRemovals([])
                        uievent.editor.setDragSourceData([])

                prompt = None
                if isinstance(event_handler, base.EventHandler):
                    editor_updates.combine(event_handler.editor_updates)
                    if isinstance(uievent, MouseEvent) or \
                       isinstance(uievent, KeyboardEvent):
                        prompt = event_handler.getPrompt(uievent)
                        display.setPrompt(editor, prompt, pending_actions)

                elif isinstance(uievent, MouseEvent) or \
                     isinstance(uievent, KeyboardEvent):
                    event_handler = None
                    prompt = utils.getPromptWithNoHandler(uievent)
                    display.setPrompt(editor, prompt, pending_actions,
                        uievent.modifierstate.ctrl)

                elif isinstance(uievent, KeyboardEvent):
                    event_handler = None

                if isinstance(uievent, MouseEvent):
                    # Configure the canvas tool tip.
                    if uievent.eventtype == 'mousemove':
                        editor.setTooltip(utils.getTooltip(uievent))
                    else:
                        editor.setTooltip(None)

                # For all pending actions, give them a chance to complete
                # based on the new event, or incorporate their visual
                # elements into the editor.
                for action in pending_actions:
                    if action.completeAction(uievent):
                        pending_actions.remove(action)
                    else:
                        editor_updates.combine(action.editor_updates)

            except hou.PermissionError as pe:
                editor.flashMessage('STATUS_error',
                    'Permission Denied', 2.0)
                event_handler = None
                keep_state = False

            except Exception as ex:
                traceback.print_exc()
                event_handler = None
                keep_state = False

        # If an action has completed, all drawing state related to the last
        # activity should be cleared.
        editor_updates.applyToEditor(editor)

        # Any time we exit an event handler, for any reason, make sure we
        # re-enable UI element locating in the network editor.
        if event_handler is None:
            editor.setLocatingEnabled(True)

    # If we exit our loop, clean up the editor's pre-selection.
    uievent.editor.setPreSelectedItems(())
    # Reset our background images in case the user was modifying them.
    if prefs.backgroundImageEditing(uievent.editor):
        images = utils.loadBackgroundImages(uievent.editor.pwd())
        uievent.editor.setBackgroundImages(images)

def createNodeTypeEventHandler(uievent, pending_actions):
    handler = None
    handled = False
    if isinstance(uievent.selected.item, hou.OpNode):
        hdamodule = uievent.selected.item.hdaModule()
        try:
            func = hdamodule.__getattr__('createEventHandler')
        except AttributeError:
            func = None
        if func is not None:
            handler, handled = func(uievent, pending_actions)

    return handler, handled

def createEventHandler(uievent, pending_actions):
    # Provide an opportunity for user-customized event handling. Import the
    # hooks module inside this function to avoid circular imports.
    import nodegraphhooks as hooks
    handler, handled = hooks.createEventHandler(uievent, pending_actions)
    if handled:
        return handler

    if isinstance(uievent, KeyboardEvent):
        if uievent.eventtype.endswith('keyhit'):
            return hotkeys.KeyHitHandler(uievent)

        elif uievent.eventtype == 'keydown':
            display.setDecoratedItem(uievent.editor, None,
                    pending_actions, False, False)
            view_hotkey_sym = 'h.pane.wsheet.view_mode'
            select_hotkey_sym = 'h.pane.wsheet.select_mode'
            align_hotkey_sym = 'h.pane.wsheet.layout_mode'
            flag1_hotkey_sym = 'h.pane.wsheet.flag1_mode'
            flag2_hotkey_sym = 'h.pane.wsheet.flag2_mode'
            flag3_hotkey_sym = 'h.pane.wsheet.flag3_mode'
            flag4_hotkey_sym = 'h.pane.wsheet.flag4_mode'
            bypass_hotkey_sym = 'h.pane.wsheet.bypass_mode'
            vis_hotkey_sym = 'h.pane.wsheet.visualize_mode'
            cut_hotkey_sym = 'h.pane.wsheet.cut_wires_mode'
            stitch_hotkey_sym = 'h.pane.wsheet.stitch_mode'
            if hou.ui.isKeyMatch(uievent.key, view_hotkey_sym):
                return states.ViewStateHandler(uievent)

            elif hou.ui.isKeyMatch(uievent.key, select_hotkey_sym):
                return states.BoxSelectStateHandler(uievent)

            elif hou.ui.isKeyMatch(uievent.key, cut_hotkey_sym):
                return states.CutWiresStateHandler(uievent)

            elif hou.ui.isKeyMatch(uievent.key, stitch_hotkey_sym):
                return states.StitchStateHandler(uievent)

            elif hou.ui.isKeyMatch(uievent.key, align_hotkey_sym):
                return states.AlignStateHandler(uievent)

            elif hou.ui.isKeyMatch(uievent.key, bypass_hotkey_sym):
                return states.FlagStateHandler(uievent, 0)

            elif hou.ui.isKeyMatch(uievent.key, flag1_hotkey_sym):
                return states.FlagStateHandler(uievent, 1)

            elif hou.ui.isKeyMatch(uievent.key, flag2_hotkey_sym):
                return states.FlagStateHandler(uievent, 2)

            elif hou.ui.isKeyMatch(uievent.key, flag3_hotkey_sym):
                return states.FlagStateHandler(uievent, 3)

            elif hou.ui.isKeyMatch(uievent.key, flag4_hotkey_sym):
                return states.FlagStateHandler(uievent, 4)

            elif hou.ui.isKeyMatch(uievent.key, vis_hotkey_sym):
                if uievent.editor.pwd().childTypeCategory() in \
                   (hou.vopNodeTypeCategory(), ):
                    return states.VisualizeStateHandler(uievent)

    elif isinstance(uievent, MouseEvent):
        if uievent.eventtype == 'mousedown':
            display.setDecoratedItem(uievent.editor, None,
                    pending_actions, False, False)
            if uievent.selected.name.startswith('overview'):
                return base.OverviewMouseHandler(uievent)
            elif uievent.selected.name == 'colorpalettecolor':
                return palettes.ColorPaletteMouseHandler(uievent)
            elif uievent.selected.name == 'shapepaletteshape':
                return palettes.ShapePaletteMouseHandler(uievent)
            elif uievent.selected.name in (
                'taskgraphworkitem', 'taskgraphcollapseditem'
                ):
                return WorkItemMouseHandler(uievent)
            elif uievent.selected.name == 'taskgraphpage':
                return TaskGraphPageHandler(uievent)
            elif uievent.selected.name == 'taskgraphopentable':
                return TaskGraphSeeMoreHandler(uievent)
            elif uievent.selected.name in thePaletteBackgrounds:
                return palettes.PaletteBackgroundMouseHandler(uievent)
            elif uievent.selected.name in thePaletteBorders:
                return palettes.PaletteBorderMouseHandler(uievent)
            elif uievent.selected.name in theBackgroundImageElements:
                return BackgroundImageMouseHandler(uievent)
            elif uievent.selected.item is None:
                return BackgroundMouseHandler(uievent)
            elif isinstance(uievent.selected.item, hou.Node):
                handler, handled = \
                    createNodeTypeEventHandler(uievent, pending_actions)
                if handled:
                    return handler
                return NodeMouseHandler(uievent)
            elif isinstance(uievent.selected.item, hou.NetworkBox):
                return NetworkBoxMouseHandler(uievent)
            elif isinstance(uievent.selected.item, hou.StickyNote):
                return StickyNoteMouseHandler(uievent)
            elif isinstance(uievent.selected.item, hou.SubnetIndirectInput):
                return IndirectInputMouseHandler(uievent)
            elif isinstance(uievent.selected.item, hou.NetworkDot):
                return NetworkDotMouseHandler(uievent)
            elif isinstance(uievent.selected.item, hou.NodeConnection):
                return NodeConnectionMouseHandler(uievent)
            elif isinstance(uievent.selected.item, NodeDependency):
                return NodeDependencyMouseHandler(uievent)

        # Handle double clicking a TOP work item
        if uievent.eventtype == 'doubleclick':
            if uievent.selected.name == 'taskgraphworkitem':
                return WorkItemMouseHandler(uievent)

        elif uievent.eventtype == 'mousemove':
            prev_decorated = uievent.editor.decoratedItem()
            keep_prev_decorated = False
            locating_decoration = False
            # If the mouse is over one of the flyout parts when they hit ctrl,
            # we want to leave the decoration up and active. Otherwise it's
            # impossible to Ctrl-click the node ring display or template flags.
            if prev_decorated is not None and \
               uievent.located.item == prev_decorated and \
               uievent.located.name in theFlyoutParts and \
               uievent.located.name not in theFlyoutExpansions:
                locating_decoration = True
            # Check if the mouse is over the flyout expanded area. If it is,
            # we want to leave the flyout unchanged regardless of what is
            # located (unless the ctrl key is down).
            if prev_decorated is not None and \
               (not uievent.modifierstate.ctrl or locating_decoration):
                items_under_mouse = uievent.editor.networkItemsInBox(
                    uievent.mousepos, uievent.mousepos, for_select = True)
                if any(item for item in items_under_mouse
                       if item[1] in theFlyoutExpansions):
                    keep_prev_decorated = True

            if not keep_prev_decorated:
                new_decorated = None
                if isinstance(uievent.located.item, hou.Node) and \
                   (uievent.located.name not in theSkipDecorators or \
                    uievent.located.item == prev_decorated):
                    # Bring up the decoration on any part of a node except the
                    # connectors. But a mouse over the connectors should not
                    # remove the decoration if it's already up.
                    new_decorated = uievent.located.item
                elif isinstance(uievent.located.item, hou.NetworkDot) or \
                     isinstance(uievent.located.item, hou.SubnetIndirectInput):
                    # Bring up the decoration on any part of an indirect input.
                    new_decorated = uievent.located.item

                if new_decorated is not None:
                    # If the decoration is changing from interactive to
                    # non-interactive, we may need to update the decorated item
                    # due to the impending removal of the decorations.
                    if uievent.modifierstate.ctrl and \
                       uievent.editor.decorationInteractive():
                        radius = utils.getDropTargetRadius(uievent.editor)
                        p0 = uievent.mousepos - hou.Vector2(radius, radius)
                        p1 = uievent.mousepos + hou.Vector2(radius, radius)
                        items_in_box = uievent.editor.networkItemsInBox(p0, p1)
                        new_decorated = None
                        for item_in_box in items_in_box:
                            item = item_in_box[0]
                            if (isinstance(item, hou.Node) or \
                                isinstance(item, hou.SubnetIndirectInput)) and \
                               item_in_box[1] not in theFlyoutParts:
                                new_decorated = item
                                break
                    # Show the decoration immediately if the Ctrl key is down
                    # or it is a network dot being decorated. They are so small
                    # we don't want to make the user hover over it.
                    display.setDecoratedItem(uievent.editor,
                            new_decorated,
                            pending_actions,
                            isinstance(new_decorated, hou.NetworkDot) or \
                            uievent.modifierstate.ctrl,
                            not uievent.modifierstate.ctrl)

                else:
                    display.setDecoratedItem(uievent.editor, None,
                            pending_actions, False, False)

        elif uievent.eventtype == 'mousewheel':
            if uievent.wheelstate:
                view.panWithMouseWheel(uievent)
            else:
                view.scaleWithMouseWheel(uievent)

    elif isinstance(uievent, GestureEvent):
        if uievent.eventtype == 'gesture':
            view.scaleWithPinch(uievent)

    return None

class BackgroundMouseHandler(base.EventHandler):
    def handleEvent(self, uievent, pending_actions):
        try:
            #获取上下文点击节点的 input output或wave
            if uievent.selected.item != None:
                global context_wave_connect
                context_wave_connect = uievent.selected
            else:
                context_wave_connect = None
        except:
            pass

        if uievent.eventtype == 'mousedrag':
            handler = None
            if self.start_uievent.mousestate.lmb:
                handler = states.BoxPickHandler(self.start_uievent, True)
            elif base.isPanEvent(self.start_uievent):
                handler = base.ViewPanHandler(self.start_uievent)
            elif base.isScaleEvent(self.start_uievent):
                handler = base.ViewScaleHandler(self.start_uievent)
            if handler:
                return handler.handleEvent(uievent, pending_actions)

        elif uievent.eventtype == 'mouseup':
            if self.start_uievent.mousestate.lmb:
                with hou.undos.group('Clear selection', uievent.editor):
                    uievent.editor.clearAllSelected()

            elif self.start_uievent.mousestate.rmb:
                if uievent.modifierstate.shift:
                    # radialmenu.openRadialMenu(uievent)

                    #shift + right clic空白区域 
                    # print("openRadialMenu    1")    
                    global empty_menu
                    zjyitem = Zjy_create_radialmenu_dict(uievent,context_wave_connect)
                    hou_Radialmenu_dict = zjyitem.get_hou_radialmenu_item(hou.getenv('HOUDINI_USER_PREF_DIR') +r'\radialmenu\zjy_radialMenu_empty.radialmenu')
                    # zjy_Radialmenu_dict = zjyitem.get_zjyRadialmenu_dict()
                    # print(zjyitem.get_item())  
                    empty_menu = Zjy_radialmenu( uievent ,context_wave_connect,hou_Radialmenu_dict)
                    # menu.itemClicked.connect(self.menuItemClicked)
                    empty_menu.show()
                   
                else:
                    uievent.editor.openTabMenu(
                            key = utils.getDefaultTabMenuKey(uievent.editor))

            return None

        # deselect TOP workitems
        elif uievent.eventtype == 'mousedown':
            if self.start_uievent.mousestate.lmb:
                pwd = uievent.editor.pwd()
                if isinstance(pwd, hou.OpNode):
                    pwd.deselectWorkItem()

        # Keep handling events until the mouse is dragged, or the mouse button
        # is released.
        return self

class MovableItemMoveHandler(base.ItemEventHandler):
    def __init__(self, start_uievent, click_handler):
        base.ItemEventHandler.__init__(self, start_uievent)
        self.click_handler = click_handler
        self.moveitems = []
        self.moveitemsmodifierstate = None
        self.drag = hou.Vector2(0, 0)
        self.dropitem = None
        self.toggleallowdroponwire = False
        self.cleanuponexit = False
        hotkey = 'h.pane.wsheet.drop_on_wire_mode'
        if start_uievent.editor.isVolatileHotkeyDown(hotkey):
            self.toggleallowdroponwire = True
        # Remember the node-space position of where the drag starts.
        self.start_pos = start_uievent.mousestartpos
        self.start_pos = start_uievent.editor.posFromScreen(self.start_pos)
        # Track the view bounds so we can update our alignment data if
        # they change. Start with invalid bounds so we know we need to
        # build the initial alignment data.
        self.visiblebounds = hou.BoundingRect()
        self.aligntomoveitems = False
        # Test for shaking the items to disconnect them.
        self.gman = gestures.GestureManager()
        self.gman.addDetector(
            gestures.ShakeDetector(start_uievent.editor, 'shake'))
        self.olddefaultcursor = start_uievent.editor.defaultCursor()
        start_uievent.editor.setDefaultCursor(None)

    def isPerformingCopy(self, uievent):
        return uievent.modifierstate.alt

    def isDragFarEnoughToCopy(self, uievent):
        rect = uievent.editor.itemRect(self.item, False)
        pos = uievent.editor.posFromScreen(uievent.mousepos)
        return not rect.contains(pos)

    def getItemsToMove(self, uievent):
        if uievent.modifierstate.alt and \
           uievent.modifierstate.shift and \
           uievent.modifierstate.ctrl:
            # If alt, ctrl, and shift are all down, we can't do tree-based
            # operations. This is a ref copy of the one clicked item, or all
            # selected items if the clicked item is selected.
            if self.item.isSelected():
                itemset = set(list(self.item.parent().selectedItems()))
            else:
                itemset = set([self.item])

        else:
            # If we are dragging a picked item, drag all picked items.
            # Otherwise only drag the selected item. If ctrl or shift are
            # pressed, we are doing tree-based selection.
            include_container_netboxes = False
            if uievent.modifierstate.ctrl and \
               (isinstance(self.item, hou.Node) or \
                isinstance(self.item, hou.NetworkDot) or \
                isinstance(self.item, hou.SubnetIndirectInput)):
                # Nodes, dots, and subnet inputs can drag along all their
                # outputs, or if shift is also being held, we can move all
                # connected items.
                itemset = set()
                if uievent.modifierstate.shift:
                    utils.getAllConnectedItems(self.item, itemset)
                else:
                    utils.getOutputsRecursive(self.item, itemset)
                include_container_netboxes = True

            elif uievent.modifierstate.shift and \
                 (isinstance(self.item, hou.Node) or \
                  isinstance(self.item, hou.NetworkDot)):
                # Nodes and dots can drag along all their inputs.
                itemset = set()
                utils.getInputsRecursive(self.item, itemset)
                include_container_netboxes = True

            else:
                if self.item.isSelected():
                    itemset = set(list(self.item.parent().selectedItems()))
                else:
                    itemset = set([self.item])

            # When moving with Shift or Ctrl down, we want to move any netboxes
            # that contain any items that are being moved.
            if include_container_netboxes:
                # We don't want to move any netboxes that contain the item
                # that is being moved.
                excludenetboxes = set()
                netbox = self.item.parentNetworkBox()
                while netbox is not None:
                    excludenetboxes.add(netbox)
                    netbox = netbox.parentNetworkBox()
                # Now go through and find all netboxes that contain any items
                # the will be moved.
                containedset = itemset
                while containedset:
                    containerset = set()
                    for item in containedset:
                        netbox = item.parentNetworkBox()
                        if netbox is not None and \
                           netbox not in itemset and \
                           netbox not in excludenetboxes:
                            containerset.add(netbox)
                    itemset = itemset.union(containerset)
                    containedset = containerset

        containedset = set()
        for item in itemset:
            if isinstance(item, hou.NetworkBox):
                containedset = containedset.union(set(item.items()))
        itemset = itemset.union(containedset)
        itemset.remove(self.item)

        # Convert the item set into a list.
        moveitems = list(itemset)
        moveitems.insert(0, self.item)

        # Set up drag data in case the mouse leaves the view.
        uievent.editor.setDragSourceData(moveitems)

        return moveitems

    def handleEvent(self, uievent, pending_actions):
        # Check if the user wants to enter the scroll state.
        if states.isScrollStateEvent(uievent):
            return states.ScrollStateHandler(uievent, self)

        if uievent.eventtype == 'keydown' or \
           uievent.eventtype == 'keyup':
            drop_hotkey_sym = 'h.pane.wsheet.drop_on_wire_mode'
            if hou.ui.isKeyMatch(uievent.key, drop_hotkey_sym):
                self.toggleallowdroponwire = (uievent.eventtype == 'keydown')

        elif (isinstance(uievent, MouseEvent) or \
              isinstance(uievent, KeyboardEvent)) and \
             not uievent.modifierstate.alt:
            gesture = self.gman.testForGesture(uievent)
            if gesture == 'shake':
                suffix = 's' if len(self.moveitems) > 1 else ''

                with hou.undos.group('Disconnect node' + suffix, uievent.editor):
                    utils.reconnectAroundItems(self.moveitems, False, editor=uievent.editor)
                self.cleanuponexit = True

                # We may have deleted some picked dots, so regenerate our
                # list of picked items.
                self.moveitems = []

        self.dropitem = None

        if isinstance(uievent, MouseEvent) or \
           isinstance(uievent, KeyboardEvent):
            self.editor_updates.clear()
            radius = utils.getDropTargetRadius(uievent.editor)

            if isinstance(uievent, KeyboardEvent) or \
               uievent.eventtype == 'mousedrag':
                handler = None
                if self.start_uievent.mousestate.lmb:
                    editor = uievent.editor

                    # If the mouse is moved outside the network view, treat it
                    # as a drag and drop to another part of Houdini, so don't
                    # adjust any positions.
                    if not editor.isPosInside(uievent.mousepos, False):
                        self.moveitems = []
                        self.moveitemsmodifierstate = None
                        self.drag = hou.Vector2(0, 0)
                        self.showAllAdjustments(editor, uievent)
                        return self

                    # Start auto-scrolling if we are near the edge.
                    autoscroll.startAutoScroll(self, uievent, pending_actions)

                    # Only allow dragging within the visible area (but with auto
                    # scrolling the visible area may change over time).
                    self.drag = editor.screenBounds().closestPoint(
                                uievent.mousepos)
                    self.drag = self.drag - editor.posToScreen(self.start_pos)
                    duration = self.drag.length()
                    self.drag = editor.sizeFromScreen(self.drag)

                    # If we haven't yet generated our list of things being
                    # moved, do it now.
                    if not self.moveitems or \
                       self.moveitemsmodifierstate != uievent.modifierstate:
                        self.moveitems = self.getItemsToMove(uievent)
                        self.moveitemsmodifierstate = uievent.modifierstate

                    # Get drop targets, but don't allow any of the items
                    # being dragged.
                    items = self.getPossibleDropTargets(uievent) or []
                    mouseitem = self.getPreferredDropTarget(items, uievent)
                    editor.setDropTargetItem(*mouseitem)
                    self.dropitem = mouseitem

                    # Regenerate our possible alignment targets if our view
                    # bounds have changed.
                    newvisiblebounds = uievent.editor.visibleBounds()
                    aligntomoveitems = self.isPerformingCopy(uievent)
                    if self.visiblebounds != newvisiblebounds or \
                       self.aligntomoveitems != aligntomoveitems:
                        # Ignore position adjustments if we are can align
                        # with the items being moved. We want to align with
                        # their unadjusted positions.
                        self.alignrects = uievent.editor.allVisibleRects(
                            [] if aligntomoveitems else self.moveitems,
                            not aligntomoveitems)
                        self.visiblebounds = newvisiblebounds
                        self.aligntomoveitems = aligntomoveitems

                    if not self.isPerformingCopy(uievent) or \
                       self.isDragFarEnoughToCopy(uievent):
                        # Try to do snapping of the item being dragged to any
                        # other visible items in the view.
                        draggedrect = editor.itemRect(self.item, False)
                        draggedrect.translate(self.drag)
                        snapresult = snap.snap(editor, self.item, draggedrect,
                                               self.alignrects)
                        self.editor_updates.addOverlayShapes(
                                    snapresult.shapes(editor))
                        if snapresult.isValid():
                            self.drag += snapresult.delta()

                    # The position of each item changes with each mouse
                    # movement.
                    self.showAllAdjustments(editor, uievent)

                elif base.isPanEvent(self.start_uievent):
                    handler = base.ViewPanHandler(self.start_uievent)

                elif base.isScaleEvent(self.start_uievent):
                    handler = base.ViewScaleHandler(self.start_uievent)

                if handler:
                    uievent.editor.setDefaultCursor(self.olddefaultcursor)
                    return handler.handleEvent(uievent, pending_actions)

                if self.dropitem is not None and self.dropitem.item is not None:
                    uievent.editor.setDefaultCursor(utils.theCursorDragDropOn)
                else:
                    uievent.editor.setDefaultCursor(None)

                return self

            elif uievent.eventtype == 'mouseup':
                # If we looked like we were doing a copy, but didn't move the
                # mouse far enough to do a real copy, treat it as a click
                # instead (if we were given a click handler).
                if self.isPerformingCopy(uievent) and \
                   not self.isDragFarEnoughToCopy(uievent):
                    if self.click_handler is not None:
                        uievent.editor.setDefaultCursor(self.olddefaultcursor)
                        return self.click_handler.handleEvent(uievent,
                                                              pending_actions)

                # Only handle drops if the mouse button is released inside
                # the network view. Also don't drop on any of the items
                # being dragged.
                elif uievent.editor.isPosInside(uievent.mousepos, False):
                    items = self.getPossibleDropTargets(uievent) or []
                    mouseitem = self.getPreferredDropTarget(items, uievent)
                    # If the Alt key is down, we are copying nodes, so don't
                    # do any of the other stuff a drag/drop would normally do.
                    if self.isPerformingCopy(uievent):
                        self.applyAdjustments(uievent)
                    else:
                        self.handleDrop(mouseitem, uievent)

                # Reset the default cursor as we leaev this handler.
                uievent.editor.setDefaultCursor(self.olddefaultcursor)

                if self.cleanuponexit:
                    utils.cleanupDisconnectedItems(uievent.editor.pwd())

                return None

            elif uievent.eventtype == 'mousewheel':
                # This must be scaling only (panning is unlikely)
                view.scaleWithMouseWheel(uievent)
                self.showAllAdjustments(uievent.editor, uievent)

        # Keep handling events until the mouse button is released.
        return self

    def getItemChain(self):
        drag_items = set(self.moveitems)
        parent = self.item.parent()
        visited_items = set([self.item])
        chain = [self.item]
        start_item = self.item
        inputs = list(c.inputItem() for c in start_item.inputConnections())
        while inputs and \
              inputs[0] in drag_items and \
              inputs[0] not in visited_items and \
              inputs[0].parent() == parent:
            start_item = inputs[0]
            visited_items.add(start_item)
            inputs = list(c.inputItem() for c in start_item.inputConnections())
            chain.insert(0, start_item)

        visited_items = set([self.item])
        end_item = self.item
        outputs = list(c.outputItem()
                       for c in end_item.outputConnections())
        while outputs:
            found_output = False
            for output in outputs:
                if output in drag_items and \
                   output not in visited_items and \
                   utils.getMaxNumOutputs(output) > 0:
                    end_item = output
                    visited_items.add(end_item)
                    outputs = list(c.outputItem()
                                   for c in end_item.outputConnections())
                    chain.append(end_item)
                    found_output = True
                    break
            if not found_output:
                outputs = []

        return chain

    def buildPreviewWires(self, editor, conn):
        wire_shapes = []
        zero = hou.Vector2(0.0, 0.0)
        clr = hou.ui.colorFromName('GraphPreSelection')
        item_chain = self.getItemChain()
        initem = item_chain[0]
        outitem = item_chain[-1]
        if utils.getMaxNumInputs(initem) > 0:
            outpos = editor.itemOutputPos(
                    conn.inputItem(),
                    conn.inputItemOutputIndex())
            outdir = editor.itemOutputDir(
                    conn.inputItem(),
                    conn.inputItemOutputIndex())
            inpos = editor.itemInputPos(initem, 0)
            indir = editor.itemInputDir(initem, 0)
            wire_shapes.append(hou.NetworkShapeConnection(
                outpos, outdir, inpos, indir, clr, 1.0))

        if utils.getMaxNumOutputs(outitem) > 0:
            outpos = editor.itemOutputPos(outitem, 0)
            outdir = editor.itemOutputDir(outitem, 0)
            inpos = editor.itemInputPos(
                    conn.outputItem(),
                    conn.inputIndex())
            indir = editor.itemInputDir(
                    conn.outputItem(),
                    conn.inputIndex())
            wire_shapes.append(hou.NetworkShapeConnection(
                outpos, outdir, inpos, indir, clr, 1.0))

        return wire_shapes

    def getPossibleDropTargets(self, uievent):
        if any(isinstance(i, hou.CopNode) for i in self.moveitems):
            return utils.getPossibleDropTargetsForItem(
                    uievent, self.item, self.moveitems)

        radius = utils.getDropTargetRadius(uievent.editor)
        return utils.getPossibleDropTargets(uievent, radius, self.moveitems)

    def getPreferredDropTarget(self, mouseitems, uievent):
        mouseitem = NetworkComponent(None, '', 0)
        for testitem in mouseitems:
            if isinstance(testitem.item, hou.NetworkBox):
                if self.item != testitem.item:
                    mouseitem = NetworkComponent(*testitem)
                    break

        return mouseitem

    def handleDrop(self, mouseitem, uievent):
        if isinstance(mouseitem.item, hou.NetworkBox):
            with hou.undos.group('Move items', uievent.editor):
                self.applyAdjustments(uievent)
                # Only set the new network box parent if it is different
                # than the one that already contains the dragged item.
                new_parent = mouseitem.item
                if self.item.parentNetworkBox() != new_parent:
                    for item in self.moveitems:
                        parent = item.parentNetworkBox()
                        if parent != new_parent and \
                           parent not in self.moveitems:
                            if parent:
                                parent.removeItem(item)
                            new_parent.addItem(item)
                    utils.saveParentNetworkBoxSizes(uievent.editor, self.item)

        else:
            with hou.undos.group('Move items', uievent.editor):
                self.applyAdjustments(uievent)
                # Only clear the new network box parents if the item being
                # dragged is currently in a network box.
                if self.item.parentNetworkBox() is not None:
                    for item in self.moveitems:
                        parent = item.parentNetworkBox()
                        if parent and \
                           parent not in self.moveitems:
                            parent.removeItem(item)

    def showAllAdjustments(self, editor, uievent):
        items = []
        adjustments = []
        shapes = []
        if self.isPerformingCopy(uievent):
            if self.isDragFarEnoughToCopy(uievent):
                for item in self.moveitems:
                    rect = editor.itemRect(item, False)
                    rect.translate(self.drag)
                    clr = hou.ui.colorFromName('GraphPreSelection')
                    # Show shadows of the current node shapes if they are
                    # enabled. Vop, Shop, and Cop2 nodes are always rectangles
                    # and can be larger, so just draw them as rectangles.
                    if isinstance(item, hou.Node) and \
                       not isinstance(item, hou.VopNode) and \
                       not isinstance(item, hou.Cop2Node) and \
                       not isinstance(item, hou.ShopNode) and \
                       prefs.showNodeShapes(editor):
                        nodeshape = item.userData('nodeshape')
                        if not nodeshape:
                            nodeshape = item.type().defaultShape()
                        shape = hou.NetworkShapeNodeShape(
                            rect, nodeshape, clr, 0.7, True, False)
                    else:
                        shape = hou.NetworkShapeBox(
                            rect, clr, 0.7, True, False)
                    shapes.append(shape)

        else:
            for item in self.moveitems:
                start = item.position()
                end = start + self.drag
                adjustments.append(hou.NetworkAnimValue(0.0, start, end))

        if self.isPerformingCopy(uievent):
            self.editor_updates.addOverlayShapes(shapes)
        else:
            if self.dropitem is not None and \
               self.dropitem.item is not None and \
               self.dropitem.item == self.item.parentNetworkBox() and \
               self.item in editor.networkBoxPendingRemovals():
                # We were pending removal from our netbox, but have now been
                # moved back in.
                editor.setNetworkBoxPendingRemovals([])
            elif self.item.parentNetworkBox() is not None:
                mousepos = editor.posFromScreen(uievent.mousepos)
                netbox = self.item.parentNetworkBox()
                netbox_rect = editor.itemRect(netbox, False)
                # We only want to check the escape velocity if the mouse
                # is outside the netbox (before making adjustments).
                if not netbox_rect.contains(mousepos):
                    v = hou.ui.resourceValueFromName('GraphNetworkBoxEscapeVel')
                    v = float(v)
                    v = hou.ui.inchesToPixels(v)
                    if self.gman.velocity() > v:
                        editor.setNetworkBoxPendingRemovals(self.moveitems)
            self.editor_updates.setAdjustments(self.moveitems, adjustments)

    def applyAdjustments(self, uievent):
        if self.isPerformingCopy(uievent):
            if self.isDragFarEnoughToCopy(uievent):
                # Figure out the rectangle that contains all items being moved
                # except indirect inputs (which can't be copy/pasted).
                copyitems = [item for item in self.moveitems
                             if not isinstance(item, hou.SubnetIndirectInput)]
                # Don't try to copy nothing (or nothing but subnet inputs).
                if not copyitems:
                    return

                # Figure out a bounding rect for all items being copied.
                old_rect = hou.BoundingRect()
                for item in copyitems:
                    old_rect.enlargeToContain(uievent.editor.itemRect(item))

                with hou.undos.group('Duplicate items', uievent.editor):
                    # Hold down Shift and Ctrl to get reference copies.
                    uievent.editor.pwd().copyItems(copyitems,
                        channel_reference_originals =
                            uievent.modifierstate.ctrl and
                            uievent.modifierstate.shift,
                        connect_outputs_to_multi_inputs = False)
                    utils.moveItemsToLocation(uievent.editor,
                        old_rect.center() + self.drag,
                        uievent.mousepos,
                        old_rect)
                    utils.updateCurrentItem(uievent.editor)

        else:
            with hou.undos.group('Move items', uievent.editor):
                for item in self.moveitems:
                    if item.parentNetworkBox() not in self.moveitems:
                        item.setPosition(item.position() + self.drag)
                        utils.saveParentNetworkBoxSizes(uievent.editor, item)

    def setParentNetworkBoxFromMousePos(self, uievent):
        # Make sure this is called from within an undo group.
        netbox = utils.getNetworkBoxUnderMouse(uievent.editor,
            uievent.mousepos, self.moveitems)
        if netbox is not None:
            for item in self.moveitems:
                itemnetbox = item.parentNetworkBox()
                if itemnetbox != netbox and itemnetbox not in self.moveitems:
                    netbox.addItem(item)
        else:
            for item in self.moveitems:
                itemnetbox = item.parentNetworkBox()
                if itemnetbox is not None and itemnetbox not in self.moveitems:
                    itemnetbox.removeItem(item)

class NodeMoveHandler(MovableItemMoveHandler):
    def __init__(self, start_uievent, click_handler):
        MovableItemMoveHandler.__init__(self, start_uievent, click_handler)
        self.dropkeys = None

    def getPrompt(self, uievent):
        if self.dropkeys is None:
            self.dropkeys = uievent.editor.hotkeyAssignments(('h.pane.wsheet.drop_on_wire_mode',))[0]
        if self.dropkeys:
            allowdroponwire = prefs.allowDropOnWireNetworkSpecific(uievent.editor, self.moveitems)
            prompt = 'Hold ' + ' or '.join(self.dropkeys) + ' to '
            prompt += 'disable' if allowdroponwire else 'enable'
            prompt += ' dropping nodes on existing wires.'

            return prompt

    def getPreferredDropTarget(self, mouseitems, uievent):
        mouseitem = NetworkComponent(None, '', 0)
        # Don't allow drop on wire if the pref is disabled,
        # or when doing a copy.
        allowdroponwire = prefs.allowDropOnWireNetworkSpecific(uievent.editor, self.moveitems)
        if (bool(allowdroponwire) != bool(self.toggleallowdroponwire)) and \
           not self.isPerformingCopy(uievent):
            for testitem in mouseitems:
                if isinstance(testitem.item, hou.NodeConnection):
                    # Don't allow dropping on a wire that is connected to
                    # any node that is being dragged along.
                    if testitem.item.inputNode() not in self.moveitems and \
                       testitem.item.outputItem() not in self.moveitems:
                        mouseitem = NetworkComponent(*testitem)
                        wire_shapes = self.buildPreviewWires(
                            self.start_uievent.editor, mouseitem.item)
                        self.editor_updates.addOverlayShapes(wire_shapes)
                        break

        # Only accept a network box drop target if nothing else is available.
        if mouseitem.item is None:
            for testitem in mouseitems:
                if isinstance(testitem.item, hou.NetworkBox):
                    mouseitem = NetworkComponent(*testitem)
                    break

        return mouseitem

    def handleDrop(self, mouseitem, uievent):
        if isinstance(mouseitem.item, hou.NodeConnection):
            with hou.undos.group('Insert node', uievent.editor):
                item_chain = self.getItemChain()
                utils.insertItemsIntoWire(mouseitem.item, item_chain,
                    self.moveitems, remove_existing_connections=True,
                    editor=uievent.editor)
                # Do the actual node move, and set the parent network box.
                self.applyAdjustments(uievent)
                self.setParentNetworkBoxFromMousePos(uievent)
                utils.moveNodesToAvoidOverlap(uievent.editor, self.moveitems)

        else:
            MovableItemMoveHandler.handleDrop(self, mouseitem, uievent)

class NodeClickHandler(base.ItemEventHandler):
    def handleEvent(self, uievent, pending_actions):
        try:
            #获取上下文点击节点的 input output或wave
            if uievent.selected.item != None:
                global context_wave_connect
                context_wave_connect = uievent.selected
        except:
            pass
        if self.start_uievent.selected.name in theNodeSelectors:
            if uievent.modifierstate.alt and \
               not uievent.modifierstate.shift and \
               not uievent.modifierstate.ctrl:
                handler = connect.ItemConnectHandler(uievent)
                return handler.handleEvent(uievent, pending_actions)

            else:
                itemset = set([self.item])
                if uievent.modifierstate.alt and \
                   uievent.modifierstate.shift:
                    initemset = set()
                    utils.getInputsRecursive(self.item, initemset)
                    itemset.update(initemset)
                if uievent.modifierstate.alt and \
                   uievent.modifierstate.ctrl:
                    outitemset = set()
                    utils.getOutputsRecursive(self.item, outitemset)
                    itemset.update(outitemset)
                view.modifySelection(uievent, None, itemset, self.item,
                    shift = False if uievent.modifierstate.alt else None,
                    ctrl = False if uievent.modifierstate.alt else None)

        elif self.start_uievent.selected.name == 'inputgroup':
            groups = self.item.inputGroupNames()
            group = groups[self.start_uievent.selected.index]
            expanded = self.item.isInputGroupExpanded(group)
            # Shift-click on a group modifies the expand state of all groups.
            if uievent.modifierstate.shift:
                group = None
            if self.item.isSelected():
                items = list(self.item.parent().selectedItems())
            else:
                items = [self.item]
            undomsg = ('Collapse' if expanded else 'Expand') + ' Input Group'
            with hou.undos.group(undomsg, self.start_uievent.editor):
                for item in items:
                    if isinstance(item, hou.VopNode):
                        item.setInputGroupExpanded(group, not expanded)

        elif self.start_uievent.selected.name == 'input' or \
             self.start_uievent.selected.name == 'multiinput':
            if self.start_uievent.mousestate.lmb:
                handler = connect.ItemConnectHandler(uievent)
                return handler.handleEvent(uievent, pending_actions)

            else:
                # Branch on mmb click. Insert inline for RMB click.
                dobranch = (self.start_uievent.mousestate.mmb != 0)
                # If we are branching, we can wire all selected items into the
                # new node created from the tab menu.
                items = utils.getSelectedItems(uievent.editor, self.item,
                    (hou.Node, hou.NetworkDot))
                indexes = [0] * len(items)
                item_index = items.index(self.start_uievent.selected.item)
                if item_index >= 0:
                    indexes[item_index] = self.start_uievent.selected.index

                if uievent.modifierstate.shift and \
                   self.start_uievent.mousestate.rmb:
                    # radialmenu.openRadialMenu(
                    #         uievent,
                    #         branch = dobranch,
                    #         dest_items = items,
                    #         dest_connector_indexes = indexes)

                    global input_menu
                    zjyitem = Zjy_create_radialmenu_dict(uievent,context_wave_connect)
                    hou_Radialmenu_dict = zjyitem.get_hou_radialmenu_item(hou.getenv('HOUDINI_USER_PREF_DIR') + r'\radialmenu\zjy_radialMenu_input.radialmenu')
                    # zjy_Radialmenu_dict = zjyitem.get_zjyRadialmenu_dict()
                    # print(zjyitem.get_item())  
                    input_menu = Zjy_radialmenu( uievent ,context_wave_connect,hou_Radialmenu_dict)
                    # menu.itemClicked.connect(self.menuItemClicked)
                    input_menu.show()
                 
                else:
                    uievent.editor.openTabMenu(branch = dobranch,
                        dest_items = items, dest_connector_indexes = indexes)

        elif self.start_uievent.selected.name == 'output':
            if self.start_uievent.mousestate.lmb:
                handler = connect.ItemConnectHandler(uievent)
                return handler.handleEvent(uievent, pending_actions)

            else:
                # Branch on mmb click. Insert inline for RMB click.
                dobranch = (self.start_uievent.mousestate.mmb != 0)
                # If we are branching, we can wire all selected items into the
                # new node created from the tab menu.
                items = utils.getSelectedItems(uievent.editor, self.item,
                    (hou.Node, hou.NetworkDot, hou.SubnetIndirectInput))
                indexes = [0] * len(items)
                item_index = items.index(self.start_uievent.selected.item)
                if item_index >= 0:
                    indexes[item_index] = self.start_uievent.selected.index

                if uievent.modifierstate.shift and \
                   self.start_uievent.mousestate.rmb:

                    global output_menu
                    zjyitem = Zjy_create_radialmenu_dict(uievent,context_wave_connect)
                    hou_Radialmenu_dict = zjyitem.get_hou_radialmenu_item(hou.getenv('HOUDINI_USER_PREF_DIR') + r'\radialmenu\zjy_radialMenu_output.radialmenu')
                    # zjy_Radialmenu_dict = zjyitem.get_zjyRadialmenu_dict()
                    # print(zjyitem.get_item())  
                    output_menu = Zjy_radialmenu( uievent ,context_wave_connect,hou_Radialmenu_dict)
                    # menu.itemClicked.connect(self.menuItemClicked)
                    output_menu.show()

                    # radialmenu.openRadialMenu(
                    #         uievent,
                    #         branch = dobranch,
                    #         src_items = items,
                    #         src_connector_indexes = indexes)
                else:
                    uievent.editor.openTabMenu(branch = dobranch,
                        src_items = items, src_connector_indexes = indexes)

        elif self.start_uievent.selected.name == 'previewplane':
            if isinstance(self.start_uievent.selected.item, hou.Cop2Node):
                menu = popupmenus.Cop2PreviewPlaneMenu(
                            uievent, uievent.located.item)
                result = utils.getPopupMenuResult(menu)
                menu.executeCommand(result)
            elif isinstance(self.start_uievent.selected.item, hou.CopNode):
                menu = popupmenus.CopPreviewPlaneMenu(
                            uievent, uievent.located.item)
                result = utils.getPopupMenuResult(menu)
                menu.executeCommand(result)

            return None

        elif self.start_uievent.selected.name in theInfoTogglers:
            if self.start_uievent.mousestate.lmb or \
               self.start_uievent.mousestate.mmb:
                ui.toggleInfoWindow(self.item, True,
                    prefs.transientInfo(uievent.editor),
                    self.start_uievent.modifierstate.shift,
                    uievent.editor)

        elif self.start_uievent.selected.name in theFlagTogglers:
            flag = flags.getFlagEnumFromIndex(self.start_uievent.selected.index)
            if self.item.isSelected():
                items = list(self.item.parent().selectedChildren())
                items.remove(self.item)
                items.insert(0, self.item)
            else:
                items = [self.item]
            flags.handleFlagClick(uievent.editor,
                    items,
                    flag,
                    self.start_uievent.selected.name,
                    uievent.modifierstate.shift,
                    uievent.modifierstate.ctrl,
                    uievent.modifierstate.alt,
                    False, False)

        return None

class NodeMouseHandler(base.ItemEventHandler):

    @staticmethod
    def _findNodeInfoSource(node, ui_event):
        """
            Given a hou.Node and mouse event, returns the node and output index
            that the info window should be opened for.
        """
        if ui_event.selected.name == 'input':
            input_index = ui_event.selected.index

            # There might not be anything connected to the input.
            if not node.inputConnectors()[input_index]:
                return None, -1

            # Find the connected node and output index.
            connection = node.inputConnectors()[input_index][0]
            return connection.inputNode(), connection.outputIndex()
        else:
            return node, ui_event.selected.index

    def handleEvent(self, uievent, pending_actions):        
        # Check if the user wants to enter the scroll state.
        if states.isScrollStateEvent(uievent):
            return states.ScrollStateHandler(uievent, self)

        if uievent.eventtype == 'mousedrag':
            handler = None
            if uievent.dragging and self.start_uievent.mousestate.lmb:
                if self.start_uievent.selected.name in theNodeDraggers:
                    display.setDecoratedItem(uievent.editor, None,
                            pending_actions, False, False)
                    handler = NodeMoveHandler(self.start_uievent,
                                NodeClickHandler(self.start_uievent))

                elif self.start_uievent.selected.name == 'input' or \
                     self.start_uievent.selected.name == 'multiinput' or \
                     self.start_uievent.selected.name == 'output':
                    # Don't allow drag-connecting of VOP 'more...' inputs
                    # or outputs. We need a popup menu to choose one
                    if not isinstance(self.item, hou.VopNode) or \
                       self.start_uievent.selected.index >= 0:
                        handler = connect.ItemConnectHandler(uievent)

            elif self.start_uievent.selected.name not in theNodeDraggers and \
                 self.start_uievent.selected.name not in theNodeInfoPoppers:
                handler = NodeMoveHandler(self.start_uievent,
                            NodeClickHandler(self.start_uievent))

            if handler:
                return handler.handleEvent(uievent, pending_actions)

            return self

        elif uievent.eventtype == 'mouseup':
            if self.start_uievent.selected.name in theNodeInfoPoppers and \
               self.start_uievent.mousestate.mmb:

                if self.start_uievent.modifierstate.ctrl:
                    node, output_index = self._findNodeInfoSource(
                        self.item, self.start_uievent)

                    if node and not isinstance(node, hou.ApexNode):
                        ui.toggleInfoWindow(node, True,
                            prefs.transientInfo(uievent.editor),
                            self.start_uievent.modifierstate.shift,
                            uievent.editor, output_index)
                else:
                    if self.popupinfo:
                        self.popupinfo.mmbReleased()

            elif self.start_uievent.selected.item == uievent.located.item:
                handler = NodeClickHandler(self.start_uievent)
                return handler.handleEvent(uievent, pending_actions)

            return None

        elif uievent.eventtype == 'doubleclick':
            if self.start_uievent.selected.item == uievent.located.item and \
               self.start_uievent.mousestate.lmb and \
               self.start_uievent.selected.name in theNodeSelectors:
                view.diveIntoNode(uievent.editor, self.item)
                return None

        elif uievent.eventtype == 'mousedown':
            self.popupinfo = None
            if self.start_uievent.selected.name == 'name':
                if self.start_uievent.mousestate.lmb:
                    if uievent.editor.pwd().isEditable():
                        valueid = uievent.editor.openNameEditor(self.item)
                        pending_actions.append(
                            base.PendingTextChangeAction(self.item, valueid))
                        return None

            elif isinstance(self.item, hou.VopNode) and \
                self.start_uievent.mousestate.mmb and \
                self.start_uievent.selected.name == 'input':
                # VOPs special case handling for MMB click on inputs.
                uievent.editor.openVopEffectsMenu(self.item,
                        self.start_uievent.selected.index)
                return None

            elif isinstance(self.item, hou.ApexNode) and \
                self.start_uievent.mousestate.mmb and \
                (self.start_uievent.selected.name == 'input' or \
                 self.start_uievent.selected.name == 'output'):
                # APEX special case handling for MMB click on ports.
                ui.renameConnector(self.item, self.start_uievent.selected.index,
                        self.start_uievent.selected.name)
                return None

            elif self.start_uievent.selected.name in theNodeInfoPoppers and \
                self.start_uievent.mousestate.mmb and \
                not self.start_uievent.modifierstate.ctrl:

                node, output_index = self._findNodeInfoSource(
                    self.item, self.start_uievent)

                if node and not isinstance(node, hou.ApexNode):
                    self.popupinfo = ui.createInfoWindow(node, False,
                        prefs.transientInfo(uievent.editor),
                        not self.start_uievent.modifierstate.shift,
                        uievent.editor, output_index)

            elif (self.start_uievent.selected.name in theFlagDecorators or \
                self.start_uievent.selected.name in theInfoTogglers) and \
                (self.start_uievent.mousestate.lmb or \
                 self.start_uievent.mousestate.mmb):
                display.setDecoratedItem(uievent.editor,
                    self.start_uievent.selected.item,
                    pending_actions, True, True)

            elif self.start_uievent.selected.name in theNodeDraggers and \
                self.start_uievent.mousestate.rmb:
                if self.start_uievent.selected.name == 'preview' and \
                   isinstance(self.item, hou.VopNode):
                    menu = popupmenus.VopPreviewContextMenu(
                                uievent, uievent.located.item)
                    result = utils.getPopupMenuResult(menu)
                    menu.executeCommand(result)

                else:
                    uievent.editor.openNodeMenu(self.item)

                return None

            elif isinstance(self.item, hou.VopNode) and \
                 self.start_uievent.mousestate.rmb and \
                 self.start_uievent.modifierstate.alt and \
                 self.start_uievent.selected.name == 'output':
                # VOPs special case handling for Alt+RMB click on outputs.
                uievent.editor.openVopOutputInfoMenu(self.item,
                        self.start_uievent.selected.index)

                return None

        # Keep handling events until a mouse action is identified.
        return self

class NetworkMovableItemSizeHandler(base.ItemEventHandler):
    def __init__(self, start_uievent):
        base.ItemEventHandler.__init__(self, start_uievent)
        self.direction = utils.getResizeDirection(start_uievent.selected.index)
        self.initialrect = start_uievent.editor.itemRect(self.item)
        self.start_pos = start_uievent.mousestartpos
        self.start_pos = start_uievent.editor.posFromScreen(self.start_pos)
        self.visiblebounds = None
        if isinstance(self.item, hou.NetworkBox):
            self.undostr = 'Resize Network Box'
            self.titleheight = float(
                hou.ui.resourceValueFromName('GraphNetworkBoxTitleHeight'))
        else:
            self.textsize = self.item.textSize()
            if self.textsize <= 0.0:
                self.textsize = utils.getDefaultStickyNoteTextSize()
            self.undostr = 'Resize Sticky Note'
            if self.item.drawBackground():
                self.titleheight = float(
                    hou.ui.resourceValueFromName('GraphStickyNoteTitleHeight'))
            else:
                self.titleheight = 0.0

    def handleEvent(self, uievent, pending_actions):
        # Check if the user wants to enter the scroll state.
        if states.isScrollStateEvent(uievent):
            return states.ScrollStateHandler(uievent, self)

        if not isinstance(uievent, MouseEvent):
            return self

        # Regenerate our possible alignment targets if our view
        # bounds have changed.
        newvisiblebounds = uievent.editor.visibleBounds()
        if self.visiblebounds != newvisiblebounds:
            self.alignrects = uievent.editor.allVisibleRects([self.item])
            self.visiblebounds = newvisiblebounds

        (rect, snapresult) = snap.snapResizeRect(uievent,
            self.item, self.initialrect, self.direction, self.titleheight,
            self.start_pos, alignrects = self.alignrects)
        self.editor_updates.setOverlayShapes(
            snapresult.shapes(uievent.editor))

        new_pos = rect.min()
        new_size = rect.size()

        if uievent.eventtype == 'mousedrag':
            # Start auto-scrolling if we are near the edge.
            autoscroll.startAutoScroll(self, uievent, pending_actions)

            # Create an adjustment to make the item look a different size
            items = [self.item]
            rect = hou.Vector4(new_pos.x(), new_pos.y(),
                               new_size.x(), new_size.y())
            adjustments = [hou.NetworkAnimValue(0.0, rect, rect)]
            self.editor_updates.setAdjustments(items, adjustments)

            return self

        elif uievent.eventtype == 'mouseup':
            # Actually resize the network item
            visible_rect = uievent.editor.itemRect(self.item)
            # Make sure we don't make the item smaller than it appears
            # on screen.
            new_size = hou.Vector2(
                    max(new_size.x(), visible_rect.size().x()),
                    max(new_size.y(), visible_rect.size().y()))
            new_pos = hou.Vector2(
                    min(new_pos.x(), visible_rect.min().x()),
                    min(new_pos.y(), visible_rect.min().y()))

            with hou.undos.group(self.undostr, uievent.editor):
                if isinstance(self.item, hou.NetworkBox):
                    self.item.setAutoFit(False)

                elif uievent.modifierstate.shift:
                    # Change the text size by the geometric mean of the change
                    # in size of the separate axes.
                    xratio = old_div(rect.size().x(), self.initialrect.size().x())
                    yratio = old_div(rect.size().y(), self.initialrect.size().y())
                    ratio = math.sqrt(xratio * yratio)
                    newtextsize = self.textsize * ratio
                    self.item.setTextSize(newtextsize)

                new_size -= hou.Vector2(0.0, self.titleheight)
                self.item.setBounds(hou.BoundingRect(new_pos, new_pos+new_size))
                utils.saveParentNetworkBoxSizes(uievent.editor, self.item)

            return None

        # Keep handling events until the mouse button is released.
        return self

class NetworkBoxClickHandler(base.ItemEventHandler):
    def handleEvent(self, uievent, pending_actions):
        if self.start_uievent.selected.name == 'networkboxtitle':
            view.modifySelection(uievent, None, [self.item])

        elif self.start_uievent.selected.name == 'networkboxminimize':
            utils.setMinimized(uievent.editor, self.item,
                               not self.item.isMinimized(),
                               uievent.modifierstate.ctrl)

        return None

class NetworkBoxMouseHandler(base.ItemEventHandler):
    def handleEvent(self, uievent, pending_actions):
        # Check if the user wants to enter the scroll state.
        if states.isScrollStateEvent(uievent):
            return states.ScrollStateHandler(uievent, self)

        if uievent.eventtype == 'mousedown':
            if self.start_uievent.mousestate.rmb:
                if self.start_uievent.selected.name == 'networkboxtitle':
                    menu = popupmenus.NetworkBoxContextMenu(
                                uievent, uievent.located.item)
                    result = utils.getPopupMenuResult(menu)
                    menu.executeCommand(result)
                    return None

        elif uievent.eventtype == 'mousedrag':
            handler = None
            if self.start_uievent.selected.name == 'networkboxtitle' and \
               self.start_uievent.mousestate.lmb and \
               uievent.dragging:
                handler = MovableItemMoveHandler(self.start_uievent,
                             NetworkBoxClickHandler(self.start_uievent))

            elif self.start_uievent.selected.name == 'networkboxborder' and \
               self.start_uievent.mousestate.lmb and \
               uievent.dragging:
                handler = NetworkMovableItemSizeHandler(self.start_uievent)

            elif base.isPanEvent(self.start_uievent):
                handler = base.ViewPanHandler(self.start_uievent)

            elif base.isScaleEvent(self.start_uievent):
                handler = base.ViewScaleHandler(self.start_uievent)

            if handler:
                return handler.handleEvent(uievent, pending_actions)

        elif uievent.eventtype == 'mouseup':
            if self.start_uievent.selected.item == uievent.located.item:
                handler = NetworkBoxClickHandler(self.start_uievent)
                return handler.handleEvent(uievent, pending_actions)

            return None

        elif uievent.eventtype == 'doubleclick':
            if self.start_uievent.selected.name == 'networkboxtitle' and \
               self.start_uievent.mousestate.lmb:
                if uievent.editor.pwd().isEditable():
                    valueid = uievent.editor.openCommentEditor(self.item)
                    pending_actions.append(
                        base.PendingTextChangeAction(self.item, valueid))
                    return None

        # Keep handling events until a mouse action is identified.
        return self

class StickyNoteClickHandler(base.ItemEventHandler):
    def handleEvent(self, uievent, pending_actions):
        if self.start_uievent.selected.name == 'stickynotetitle':
            view.modifySelection(uievent, None, [self.item])

        elif self.start_uievent.selected.name == 'stickynotetext':
            if uievent.editor.pwd().isEditable():
                valueid = uievent.editor.openNoteEditor(self.item)
                pending_actions.append(
                    base.PendingTextChangeAction(self.item, valueid))

        elif self.start_uievent.selected.name == 'stickynoteminimize':
            utils.setMinimized(uievent.editor, self.item,
                               not self.item.isMinimized(),
                               uievent.modifierstate.ctrl)

        return None

class StickyNoteMouseHandler(base.ItemEventHandler):
    def handleEvent(self, uievent, pending_actions):
        # Check if the user wants to enter the scroll state.
        if states.isScrollStateEvent(uievent):
            return states.ScrollStateHandler(uievent, self)

        if uievent.eventtype == 'mousedrag':
            handler = None
            if (self.start_uievent.selected.name == 'stickynotetitle' or \
                self.start_uievent.selected.name == 'stickynotetext') and \
               self.start_uievent.mousestate.lmb:
                handler = MovableItemMoveHandler(self.start_uievent,
                            StickyNoteClickHandler(self.start_uievent))
                return handler.handleEvent(uievent, pending_actions)

            elif self.start_uievent.selected.name == 'stickynoteborder' and \
                 self.start_uievent.mousestate.lmb:
                handler = NetworkMovableItemSizeHandler(self.start_uievent)
                return handler.handleEvent(uievent, pending_actions)

            elif base.isPanEvent(self.start_uievent):
                handler = base.ViewPanHandler(self.start_uievent)

            elif base.isScaleEvent(self.start_uievent):
                handler = base.ViewScaleHandler(self.start_uievent)

            if handler:
                return handler.handleEvent(uievent, pending_actions)

            return self

        elif uievent.eventtype == 'mouseup':
            if self.start_uievent.mousestate.lmb and \
               self.start_uievent.selected.item == uievent.located.item:
                handler = StickyNoteClickHandler(self.start_uievent)
                return handler.handleEvent(uievent, pending_actions)

            elif self.start_uievent.mousestate.rmb and \
                 self.start_uievent.selected.item == uievent.located.item:
                menu = popupmenus.StickyNoteContextMenu(
                            uievent, uievent.located.item)
                result = utils.getPopupMenuResult(menu)
                menu.executeCommand(result)

            return None

        # Keep handling events until a mouse action is identified.
        return self

class IndirectInputClickHandler(base.ItemEventHandler):
    def handleEvent(self, uievent, pending_actions):
        if self.start_uievent.selected.name == 'indirectinput':
            if self.start_uievent.mousestate.lmb and \
               uievent.modifierstate.alt and \
               not uievent.modifierstate.shift and \
               not uievent.modifierstate.ctrl:
                handler = connect.ItemConnectHandler(uievent)
                return handler.handleEvent(uievent, pending_actions)

            else:
                itemset = set([self.item])
                if uievent.modifierstate.alt and \
                   uievent.modifierstate.ctrl:
                    outitemset = set()
                    utils.getOutputsRecursive(self.item, outitemset)
                    itemset.update(outitemset)
                view.modifySelection(uievent, None, itemset, None,
                    shift = False if uievent.modifierstate.alt else None,
                    ctrl = False if uievent.modifierstate.alt else None)

        elif self.start_uievent.selected.name == 'indirectinputoutput':
            if self.start_uievent.mousestate.lmb:
                handler = connect.ItemConnectHandler(uievent)
                return handler.handleEvent(uievent, pending_actions)

            else:
                # Branch on mmb click. Insert inline for RMB click.
                dobranch = (self.start_uievent.mousestate.mmb != 0)
                # If we are branching, we can wire all selected items into the
                # new node created from the tab menu.
                items = utils.getSelectedItems(uievent.editor, self.item,
                    (hou.Node, hou.NetworkDot, hou.SubnetIndirectInput))
                indexes = [0] * len(items)
                uievent.editor.openTabMenu(branch = dobranch,
                    src_items = items, src_connector_indexes = indexes)

        elif self.start_uievent.selected.name in theInfoTogglers and \
             self.item.input() is not None:
            if self.start_uievent.mousestate.lmb or \
               self.start_uievent.mousestate.mmb:
                ui.toggleInfoWindow(self.item.input(), True,
                    prefs.transientInfo(uievent.editor),
                    self.start_uievent.modifierstate.shift,
                    uievent.editor, self.item.inputOutputIndex())

        return None

class IndirectInputMouseHandler(base.ItemEventHandler):
    def handleEvent(self, uievent, pending_actions):
        # Check if the user wants to enter the scroll state.
        if states.isScrollStateEvent(uievent):
            return states.ScrollStateHandler(uievent, self)

        if uievent.eventtype == 'mousedown':
            self.popupinfo = None
            if self.start_uievent.selected.name == 'indirectinput' and \
               self.start_uievent.mousestate.mmb and \
               not self.start_uievent.modifierstate.ctrl and \
               self.item.input() is not None:
                self.popupinfo = ui.createInfoWindow(self.item.input(), False,
                    prefs.transientInfo(uievent.editor),
                    not self.start_uievent.modifierstate.shift,
                    uievent.editor, self.item.inputOutputIndex())

            elif self.start_uievent.selected.name in theInfoTogglers and \
                (self.start_uievent.mousestate.lmb or \
                 self.start_uievent.mousestate.mmb):
                display.setDecoratedItem(uievent.editor,
                    self.start_uievent.selected.item,
                    pending_actions, True, True)

            elif self.start_uievent.selected.name == 'indirectinput' and \
                 self.start_uievent.mousestate.rmb:
                menu = popupmenus.IndirectInputContextMenu(
                            uievent, uievent.located.item)
                result = utils.getPopupMenuResult(menu)
                menu.executeCommand(result)
                return None

            return self

        elif uievent.eventtype == 'mousedrag':
            if self.start_uievent.selected.name == 'indirectinput' and \
               self.start_uievent.mousestate.lmb and \
               uievent.dragging:
                handler = MovableItemMoveHandler(self.start_uievent,
                            IndirectInputClickHandler(self.start_uievent))
                return handler.handleEvent(uievent, pending_actions)

            elif self.start_uievent.selected.name == 'indirectinputoutput':
                handler = connect.ItemConnectHandler(uievent)
                return handler.handleEvent(uievent, pending_actions)

            return self

        elif uievent.eventtype == 'mouseup':
            if self.start_uievent.selected.name == 'indirectinput' and \
               self.start_uievent.mousestate.mmb and \
               self.item.input() is not None:
                if self.start_uievent.modifierstate.ctrl:
                    ui.toggleInfoWindow(self.item.input(), True,
                        prefs.transientInfo(uievent.editor),
                        self.start_uievent.modifierstate.shift,
                        uievent.editor, self.item.inputOutputIndex())
                else:
                    if self.popupinfo:
                        self.popupinfo.close()

            elif self.start_uievent.selected.item == uievent.located.item:
                handler = IndirectInputClickHandler(self.start_uievent)
                return handler.handleEvent(uievent, pending_actions)

            return None

        elif uievent.eventtype == 'doubleclick':
            if self.start_uievent.mousestate.lmb:
                node = self.item.input()
                if node is None:
                    node = self.item.parent()
                view.jumpToNode(uievent.editor, node, [self.item.parent()])
                return None

        # Keep handling events until a mouse action is identified.
        return self

class NetworkDotClickHandler(base.ItemEventHandler):
    def handleEvent(self, uievent, pending_actions):
        if self.start_uievent.mousestate.lmb:
            if uievent.selected.name in ('dotinput', 'dotoutput'):
                handler = connect.ItemConnectHandler(uievent)
                return handler.handleEvent(uievent, pending_actions)

            elif uievent.modifierstate.alt and \
                 not uievent.modifierstate.shift and \
                 not uievent.modifierstate.ctrl:
                newpinned = not self.item.isPinned()
                if newpinned:
                    msg = 'Pin Network Dot'
                else:
                    msg = 'Unpin Network Dot'
                with hou.undos.group(msg, uievent.editor):
                    self.item.setPinned(newpinned)
                    if not newpinned:
                        utils.cleanupDisconnectedItems(uievent.editor.pwd())

            else:
                itemset = set([self.item])
                if uievent.modifierstate.alt and \
                   uievent.modifierstate.shift:
                    initemset = set()
                    utils.getInputsRecursive(self.item, initemset)
                    itemset.update(initemset)
                if uievent.modifierstate.alt and \
                   uievent.modifierstate.ctrl:
                    outitemset = set()
                    utils.getOutputsRecursive(self.item, outitemset)
                    itemset.update(outitemset)
                view.modifySelection(uievent, None, itemset, None,
                    shift = False if uievent.modifierstate.alt else None,
                    ctrl = False if uievent.modifierstate.alt else None)

        else:
            if self.start_uievent.selected.name == 'dotinput':
                # Branch on mmb click. Insert inline for RMB click.
                dobranch = (self.start_uievent.mousestate.mmb != 0)
                # If we are branching, we can wire all selected items into the
                # new node created from the tab menu.
                items = utils.getSelectedItems(uievent.editor, self.item,
                    (hou.Node, hou.NetworkDot))
                indexes = [0] * len(items)
                uievent.editor.openTabMenu(branch = dobranch,
                    dest_items = items, dest_connector_indexes = indexes)

            elif self.start_uievent.selected.name == 'dotoutput':
                # Branch on mmb click. Insert inline for RMB click.
                dobranch = (self.start_uievent.mousestate.mmb != 0)
                # If we are branching, we can wire all selected items into the
                # new node created from the tab menu.
                items = utils.getSelectedItems(uievent.editor, self.item,
                    (hou.Node, hou.NetworkDot, hou.SubnetIndirectInput))
                indexes = [0] * len(items)
                uievent.editor.openTabMenu(branch = dobranch,
                    src_items = items, src_connector_indexes = indexes)

        return None

class NetworkDotMoveHandler(MovableItemMoveHandler):
    def __init__(self, start_uievent, click_handler):
        MovableItemMoveHandler.__init__(self, start_uievent, click_handler)
        self.lastpos = start_uievent.mousepos

    def isPerformingCopy(self, uievent):
        return len(self.moveitems) > 1 and uievent.modifierstate.alt

    def handleEvent(self, uievent, pending_actions):
        handler = MovableItemMoveHandler.handleEvent(self, uievent,
                                                     pending_actions)
        # If we alt-drag over a wire with the same source, join that wire
        # to the dot. If the dot being dragged has no input it can pick up
        # any connection.
        if handler is not None and \
           uievent.eventtype == 'mousedrag' and \
           self.start_uievent.mousestate.lmb and \
           uievent.modifierstate.alt and \
           len(self.moveitems) == 1:
            pick_rect = hou.BoundingRect()
            pick_rect.enlargeToContain(uievent.mousepos)
            pick_rect.enlargeToContain(self.lastpos)
            radius = utils.getDropTargetRadius(uievent.editor)
            p0 = pick_rect.min() - hou.Vector2(radius, radius)
            p1 = pick_rect.max() + hou.Vector2(radius, radius)
            items = uievent.editor.networkItemsInBox(p0,p1,for_select=True)

            # Find all wires we pass over with the same input item as the
            # dot being dragged. Replace these wires with a wire from the
            # dot being dragged to wherever the wire ends up.
            dotinputitem = self.item.inputItem()
            dotoutputindex = self.item.inputItemOutputIndex()
            # If the dot has no input connection, any wire can feed into it.
            # But if multiple wires are going to feed in, they must all be
            # connected to the same input.
            with hou.undos.group('Add wires to dot', uievent.editor):
                if dotinputitem is None:
                    for item in items:
                        if isinstance(item[0], hou.NodeConnection) and \
                            item[0].inputItem() is not None and \
                            item[0].inputItem() != self.item and \
                            item[0].outputItem() != self.item:
                            dotinputitem = item[0].inputItem()
                            dotoutputindex = item[0].inputItemOutputIndex()
                            self.item.setInput(dotinputitem, dotoutputindex)
                            break
                items = list(item[0] for item in items
                    if isinstance(item[0], hou.NodeConnection) and \
                       item[0].inputItem() == dotinputitem and \
                       item[0].inputItemOutputIndex() == dotoutputindex and \
                       item[0].outputItem() != self.item)
                for item in items:
                    item.outputItem().setInput(item.inputIndex(), self.item, 0)
                utils.cleanupDisconnectedItems(uievent.editor.pwd())

        if isinstance(uievent, MouseEvent):
            self.lastpos = uievent.mousepos

        return handler

class NetworkDotMouseHandler(base.ItemEventHandler):
    def handleEvent(self, uievent, pending_actions):
        # Check if the user wants to enter the scroll state.
        if states.isScrollStateEvent(uievent):
            return states.ScrollStateHandler(uievent, self)

        if uievent.eventtype == 'mousedown':
            self.popupinfo = None
            if self.start_uievent.selected.name == 'dot' and \
               self.start_uievent.mousestate.mmb and \
               not self.start_uievent.modifierstate.ctrl and \
               self.item.input() is not None:
                self.popupinfo = ui.createInfoWindow(self.item.input(), False,
                    prefs.transientInfo(uievent.editor),
                    not self.start_uievent.modifierstate.shift,
                    uievent.editor, self.item.inputOutputIndex())

            elif self.start_uievent.mousestate.rmb and \
               self.start_uievent.selected.name == 'dot':
                menu = popupmenus.IndirectInputContextMenu(
                            uievent, uievent.located.item)
                result = utils.getPopupMenuResult(menu)
                menu.executeCommand(result)
                return None

            return self

        elif uievent.eventtype == 'mousedrag':
            if uievent.dragging and self.start_uievent.mousestate.lmb:
                if self.start_uievent.selected.name == 'dot':
                    display.setDecoratedItem(uievent.editor, None,
                            pending_actions, False, False)
                    handler = NetworkDotMoveHandler(self.start_uievent,
                                NetworkDotClickHandler(self.start_uievent))
                    return handler.handleEvent(uievent, pending_actions)

                elif self.start_uievent.selected.name == 'dotinput' or \
                     self.start_uievent.selected.name == 'dotoutput':
                    handler = connect.ItemConnectHandler(uievent)
                    return handler.handleEvent(uievent, pending_actions)

            return self

        elif uievent.eventtype == 'mouseup':
            if self.start_uievent.selected.name == 'dot' and \
               self.start_uievent.mousestate.mmb and \
               self.item.input() is not None:
                if self.start_uievent.modifierstate.ctrl:
                    ui.toggleInfoWindow(self.item.input(), True,
                        prefs.transientInfo(uievent.editor),
                        self.start_uievent.modifierstate.shift,
                        uievent.editor, self.item.inputOutputIndex())
                else:
                    if self.popupinfo:
                        self.popupinfo.close()

            elif self.start_uievent.selected.item == uievent.located.item:
                handler = NetworkDotClickHandler(self.start_uievent)
                return handler.handleEvent(uievent, pending_actions)
            return None

        # Keep handling events until a mouse action is identified.
        return self

class NodeConnectionMouseHandler(base.ItemEventHandler):
    def handleEvent(self, uievent, pending_actions):
        if uievent.selected.name == 'wire':
            handler = NodeWireMouseHandler(uievent)
        else:
            handler = NodeWireStubMouseHandler(uievent)
        return handler.handleEvent(uievent, pending_actions)

class NodeWireMouseHandler(base.ItemEventHandler):
    def handleEvent(self, uievent, pending_actions):
        # Check if the user wants to enter the scroll state.
        if states.isScrollStateEvent(uievent):
            return states.ScrollStateHandler(uievent, self)

        editor = uievent.editor
        if uievent.eventtype == 'mousedown':
            if uievent.modifierstate.alt and \
               self.start_uievent.mousestate.lmb and \
               utils.supportsNetworkDots(editor.pwd()):
                with hou.undos.group('Create dot', editor):
                    dot = editor.pwd().createNetworkDot()
                    dot.setPosition(editor.posFromScreen(uievent.mousepos))
                    dot.setInput(self.item.inputItem(),
                        self.item.inputItemOutputIndex())
                    self.item.outputItem().setInput(self.item.inputIndex(),
                        dot, 0)
                    handler = NetworkDotMoveHandler(self.start_uievent, None)
                    handler.item = dot
                    utils.cleanupDisconnectedItems(editor.pwd())
                    return handler

            elif self.start_uievent.mousestate.rmb:
                menu = popupmenus.WireContextMenu(uievent, uievent.located.item)
                result = utils.getPopupMenuResult(menu)
                result = menu.executeCommand(result)
                if isinstance(result, base.EventHandler):
                    return result

                return None

        elif uievent.eventtype == 'mousedrag':
            handler = None
            if self.start_uievent.mousestate.lmb:
                handler = connect.WireConnectHandler(uievent)
            elif base.isPanEvent(self.start_uievent):
                handler = base.ViewPanHandler(self.start_uievent)
            elif base.isScaleEvent(self.start_uievent):
                handler = base.ViewScaleHandler(self.start_uievent)
            if handler:
                return handler.handleEvent(uievent, pending_actions)

        elif uievent.eventtype == 'mouseup':
            if self.start_uievent.selected.item == uievent.located.item:
                if self.start_uievent.mousestate.lmb and \
                     uievent.modifierstate.alt:
                    handler = connect.WireMenuConnectHandler(
                                        self.start_uievent,
                                        [self.item],
                                        False)
                    return handler.handleEvent(uievent, pending_actions)

                elif self.start_uievent.mousestate.lmb:
                    view.modifySelection(uievent, None, [self.item])

            return None

        # Keep handling events until a mouse action is identified.
        return self

class NodeWireStubMouseHandler(base.ItemEventHandler):
    def handleEvent(self, uievent, pending_actions):
        # Check if the user wants to enter the scroll state.
        if states.isScrollStateEvent(uievent):
            return states.ScrollStateHandler(uievent, self)

        editor = uievent.editor
        if uievent.eventtype == 'mousedown' and \
           uievent.mousestate.rmb:
            menu = popupmenus.WireStubBundleContextMenu(uievent)
            result = utils.getPopupMenuResult(menu)
            menu.executeCommand(result)

            return None

        elif uievent.eventtype == 'mouseup':
            # LMB selects the stubbed node. Any other mouse button just exits
            # this handler.
            if self.start_uievent.mousestate.lmb:
                if self.start_uievent.selected.item == uievent.located.item:
                    bundle = utils.getWireStubBundle(self.item,
                                uievent.located.name)
                    view.modifySelection(uievent, None, bundle)

            return None

        elif uievent.eventtype == 'doubleclick':
            if self.start_uievent.selected.item == uievent.located.item and \
               self.start_uievent.mousestate.lmb:
                utils.exposeWireStubBundle(self.item, uievent.located.name,
                                           editor=uievent.editor)

                return None

        # Keep handling events until a mouse action is identified.
        return self

class NodeDependencyMouseHandler(base.EventHandler):
    def __init__(self, start_uievent):
        base.EventHandler.__init__(self, start_uievent)
        self.dependency = start_uievent.selected.item
        self.isexternalinput = \
            (start_uievent.selected.name == 'dependencyexternalinput')
        self.isexternaloutput = \
            (start_uievent.selected.name == 'dependencyexternaloutput')

    def handleEvent(self, uievent, pending_actions):
        editor = uievent.editor
        if uievent.eventtype == 'mousedown':
            if self.dependency == uievent.selected.item:
                if self.start_uievent.mousestate.rmb:
                    if self.isexternalinput or self.isexternaloutput:
                        menu = popupmenus.ExternalDependencyContextMenu(
                                    uievent, self.dependency,
                                    self.isexternalinput)
                    else:
                        menu = popupmenus.LocalDependencyContextMenu(
                                    uievent, self.dependency)
                    result = utils.getPopupMenuResult(menu)
                    menu.executeCommand(result)
                    return None

        elif uievent.eventtype == 'mouseup':
            return None

        # Keep handling events until a mouse action is identified.
        return self

class BackgroundImageMouseHandler(base.EventHandler):
    def __init__(self, start_uievent):
        base.EventHandler.__init__(self, start_uievent)
        images = start_uievent.editor.backgroundImages()
        self.imageindex = start_uievent.selected.item
        self.image = images[self.imageindex]
        self.initialrect = self.image.rect()
        self.visiblerect = self.image.rect()
        self.start_pos = start_uievent.mousestartpos
        self.start_pos = start_uievent.editor.posFromScreen(self.start_pos)
        rel = self.image.relativeToPath()
        rel = start_uievent.editor.pwd().item(rel)
        if rel is not None:
            rel_rect = start_uievent.editor.itemRect(rel)
            rel_pos = hou.Vector2(rel_rect.min().x(), rel_rect.max().y())
            self.visiblerect.translate(rel_pos)
        self.dragged = False
        self.isborder = \
            (start_uievent.selected.name == 'backgroundimageborder')
        self.isbrightness = \
            (start_uievent.selected.name == 'backgroundimagebrightness')
        self.islink = \
            (start_uievent.selected.name == 'backgroundimagelink')
        if self.isborder:
            self.direction = \
                utils.getResizeDirection(start_uievent.selected.index)
            self.startsize = self.image.rect()

    def updateImages(self, editor, dosave, dodelete = False):
        images = list(editor.backgroundImages())
        if dodelete:
            images.pop(self.imageindex)
        else:
            images[self.imageindex] = self.image
        editor.setBackgroundImages(images)
        if dosave:
            utils.saveBackgroundImages(editor.pwd(), images, editor=editor)

    def getDropTarget(self, uievent):
        radius = utils.getDropTargetRadius(uievent.editor)
        items = utils.getPossibleDropTargets(uievent, radius)
        items = list(item.item for item in items
                     if isinstance(item.item, hou.Node) or
                        isinstance(item.item, hou.NetworkBox) or
                        isinstance(item.item, hou.StickyNote))
        item = items[0] if items else None
        return item

    def handleEvent(self, uievent, pending_actions):
        # Check if the user wants to enter the scroll state.
        if states.isScrollStateEvent(uievent):
            return states.ScrollStateHandler(uievent, self)

        # RMB opens context menu on any part of an image's UI.
        if uievent.eventtype == 'mousedown' and \
           uievent.mousestate.rmb:
            menu = popupmenus.BackgroundImageContextMenu(
                        uievent, uievent.located.item)
            result = utils.getPopupMenuResult(menu)
            menu.executeCommand(result)
            return None

        # Only handle LMB interactions, ignore MMB.
        if not self.start_uievent.mousestate.lmb:
            return None

        if self.isbrightness and \
           (uievent.eventtype == 'mousedown' or \
            uievent.eventtype == 'mousedrag' or \
            uievent.eventtype == 'mouseup'):
            if uievent.located.item == self.imageindex:
                brightness = uievent.located.index / 100.0
                self.image.setBrightness(brightness)
                self.updateImages(uievent.editor, uievent.eventtype=='mouseup')
            if uievent.eventtype == 'mouseup':
                return None

        elif uievent.eventtype == 'mousedrag' and \
             self.start_uievent.selected.name in theBackgroundImageDraggables:
            # Start auto-scrolling if we are near the edge.
            autoscroll.startAutoScroll(self, uievent, pending_actions)

            self.dragged = True
            if self.isborder:
                (rect, snapresult) = snap.snapResizeRect(uievent,
                    None, self.initialrect, self.direction, 0.0,
                    self.start_pos, preserve_aspect_ratio = True)
                self.image.setRect(rect)
                self.updateImages(uievent.editor, False)

            elif self.islink:
                drop_target = self.getDropTarget(uievent)
                uievent.editor.setDropTargetItem(drop_target, '', 0)
                link = hou.NetworkShapeLine(
                    uievent.editor.posFromScreen(uievent.mousepos),
                    self.start_pos,
                    hou.ui.colorFromName('GraphPreSelection'),
                    screen_space = False)
                self.editor_updates.setOverlayShapes([link])

            else:
                rect = hou.BoundingRect(self.initialrect)
                pos = uievent.editor.posFromScreen(uievent.mousepos)
                drag = pos - self.start_pos
                rect.translate(drag)
                self.image.setRect(rect)
                self.updateImages(uievent.editor, False)

        elif uievent.eventtype == 'mouseup':
            if uievent.located.item == self.imageindex and \
               not self.dragged:
                if uievent.located.name == self.start_uievent.selected.name:
                    if uievent.located.name=='backgroundimagedelete':
                        self.updateImages(uievent.editor, True, True)

            elif self.dragged and self.islink:
                rect = self.visiblerect
                drop_target_name = ''
                drop_target = self.getDropTarget(uievent)
                if drop_target is not None:
                    drop_target_rect = uievent.editor.itemRect(drop_target)
                    rel_pos = hou.Vector2(drop_target_rect.min().x(),
                                          drop_target_rect.max().y())
                    rect.translate(-rel_pos)
                    drop_target_name = drop_target.name()

                self.image.setRect(rect)
                self.image.setRelativeToPath(drop_target_name)

            if self.dragged:
                self.updateImages(uievent.editor, True)

            return None

        # Keep handling events until a mouse action is identified.
        return self

class TaskGraphPageHandler(base.EventHandler):
    def __init__(self, start_uievent):
        base.EventHandler.__init__(self, start_uievent)

    def handleEvent(self, uievent, pending_actions):
        if uievent.eventtype == 'mousedown':
            page_index = uievent.selected.index
            uievent.selected.item.setCurrentTOPPage(page_index)

class WorkItemMouseHandler(base.EventHandler):
    def __init__(self, start_uievent):
        base.EventHandler.__init__(self, start_uievent)
        self.start_uievent = start_uievent
        self.start_idx = start_uievent.selected.index
        self.start_node = topui.displayedTopNode(start_uievent.selected.item)

    def handleEvent(self, uievent, pending_actions):
        # Get Work Item index and send to TOP_Network to mark selected
        if not hasattr(uievent, 'selected'):
            return self

        node = topui.displayedTopNode(uievent.selected.item)
        idx = uievent.selected.index

        if uievent.eventtype == 'mousedown':
            if uievent.mousestate.lmb:
                uievent.editor.setDragSourceWorkItem(idx)
                return self
            elif uievent.mousestate.rmb:
                context_name = node.getPDGGraphContextName()

                data_layer_id = node.getDataLayerInterfaceId()
                data_layer_manager = pdgd.DataLayerInterfaceManager.Instance()
                data_layer = data_layer_manager.getInterfaceById(data_layer_id)
                
                # May have lost connection
                if not data_layer:
                    return None
                    
                menu = popupmenus.TopWorkItemContextMenu(
                    idx, node.path(), node.getPDGNodeId(), context_name, data_layer)
                result = utils.getPopupMenuResult(menu)
                menu.executeCommand(result)
                return None
            elif uievent.mousestate.mmb:
                topui.toggleWorkItemInfoWindow(
                    idx, node, True, uievent.modifierstate.ctrl,
                    editor=uievent.editor
                )
                if uievent.modifierstate.ctrl:
                    return None

        elif uievent.eventtype == 'mouseup':
            if self.start_uievent.mousestate.mmb:
                if not uievent.modifierstate.ctrl:
                    topui.toggleWorkItemInfoWindow(
                        self.start_idx, self.start_node)
                    return None
            elif self.start_uievent.mousestate.lmb:
                if not uievent.dragging:
                    node.setSelectedWorkItem(idx)
                    uievent.selected.item.setSelected(True, True)
                uievent.editor.setDragSourceWorkItem(-1)
                return None

        elif uievent.eventtype == 'doubleclick':
            if uievent.mousestate.lmb:
                topui.toggleWorkItemInfoWindow(
                    idx, node, True, True, editor=uievent.editor)
                return None

        return self

class TaskGraphSeeMoreHandler(base.EventHandler):
    def __init__(self, start_uievent):
        base.EventHandler.__init__(self, start_uievent)
        self.start_uievent = start_uievent

    def handleEvent(self, uievent, pending_actions):
        if uievent.eventtype == 'mousedown':
            if uievent.mousestate.lmb:
                node = uievent.selected.item
                topui.openTaskGraphTableWindow(node)
        return None
