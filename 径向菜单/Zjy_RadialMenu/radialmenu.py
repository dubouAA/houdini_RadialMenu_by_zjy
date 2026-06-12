import hou
import toolutils
from hutil import py23

aliases = {
    'n': 0,
    'nw': 1,
    'w': 2,
    'sw': 3,
    's': 4,
    'se': 5,
    'e': 6,
    'ne': 7,
    'north': 0,
    'northwest': 1,
    'west': 2,
    'southwest': 3,
    'south': 4,
    'southeast': 5,
    'east': 6,
    'northeast': 7,
    '0': 0,
    '1': 1,
    '2': 2,
    '3': 3,
    '4': 4,
    '5': 5,
    '6': 6,
    '7': 7,
}


def _getSceneViewer(scriptargs):
    pane = toolutils.activePane(scriptargs)
    if not isinstance(pane, (hou.SceneViewer)):
        raise hou.Error("Can't run the tool in the selected pane.")
    return pane


# def runShelfTool(scriptargs, tool):
#     pane = toolutils.activePane(scriptargs)
#     if (not isinstance(pane, (hou.SceneViewer)) and
#         not isinstance(pane, (hou.NetworkEditor))):
#         raise hou.Error("Can't run the tool in the selected pane.")
#     pane.runShelfTool(tool)
def runShelfTool(scriptargs, tool,is_zjy_radialmenu = False):
    # print(scriptargs)
    # print(is_zjy_radialmenu)
    pane = toolutils.activePane(scriptargs)
    if (not isinstance(pane, (hou.SceneViewer)) and
        not isinstance(pane, (hou.NetworkEditor))):
        raise hou.Error("Can't run the tool in the selected pane.")
    if is_zjy_radialmenu:
        # print(tool)
        return tool
    else:
        pane.runShelfTool(tool)
    # pane.runShelfTool(tool)
    # print(new_node)


def snappingMode(scriptargs):
    return _getSceneViewer(scriptargs).snappingMode()


def setSnappingMode(scriptargs, mode):
    _getSceneViewer(scriptargs).setSnappingMode(mode)


def isPickingVisibleGeometry(scriptargs):
    return _getSceneViewer(scriptargs).isPickingVisibleGeometry()


def setPickingVisibleGeometry(scriptargs, on):
    _getSceneViewer(scriptargs).setPickingVisibleGeometry(on)

def isPickingContainedGeometry(scriptargs):
    return _getSceneViewer(scriptargs).isPickingContainedGeometry()


def setPickingContainedGeometry(scriptargs, on):
    _getSceneViewer(scriptargs).setPickingContainedGeometry(on)


def isWholeGeometryPicking(scriptargs):
    return _getSceneViewer(scriptargs).isWholeGeometryPicking()


def setWholeGeometryPicking(scriptargs, on):
    _getSceneViewer(scriptargs).setWholeGeometryPicking(on)


def viewportLayout(scriptargs):
    return _getSceneViewer(scriptargs).viewportLayout()


def setViewportLayout(scriptargs, layout, single=-1):
    _getSceneViewer(scriptargs).setViewportLayout(layout, single)


def shadingMode(scriptargs):
    pane = _getSceneViewer(scriptargs)
    cat = pane.pwd().childTypeCategory()
    if cat == hou.sopNodeTypeCategory() or cat == hou.copNodeTypeCategory():
        t = hou.displaySetType.DisplayModel
    else:
        t = hou.displaySetType.SceneObject
    return pane.curViewport().settings().displaySet(t).shadedMode()


def setShadingMode(scriptargs, mode):
    pane = _getSceneViewer(scriptargs)
    cat = pane.pwd().childTypeCategory()
    if cat == hou.sopNodeTypeCategory() or cat == hou.copNodeTypeCategory():
        types = (hou.displaySetType.DisplayModel,
                 hou.displaySetType.CurrentModel,
                 hou.displaySetType.TemplateModel)
    else:
        types = (hou.displaySetType.SceneObject,
                 hou.displaySetType.SelectedObject,
                 hou.displaySetType.GhostObject)
    viewsettings = pane.curViewport().settings()
    for t in types:
        viewsettings.displaySet(t).setShadedMode(mode)


def pickStyle(scriptargs):
    return _getSceneViewer(scriptargs).pickStyle()


def setPickStyle(scriptargs, style):
    _getSceneViewer(scriptargs).setPickStyle(style)


def networkEditor(scriptargs):
    editor = toolutils.networkEditor()
    return editor


def _toLocation(key):
    if isinstance(key, str):
        key = key.lower()
        if key not in aliases:
            raise ValueError("%r is not a valid direction")
        key = aliases[key]
    if not isinstance(key, int) or key < 0 or key > 7:
        raise ValueError("%r is not a valid direction")
    return key


def _createRadialItem(entry):
    t = entry['type']
    if t in ('script_action', 'action'):
        script = entry['script']
        if callable(script):
            item = hou.ui.createRadialItem(callback=True)
            item.setActionCallback(script)

            check = entry.get('check')
            if check and callable(check):
                item.setCheckCallback(check)

        else:
            item = hou.ui.createRadialItem(callback=False)
            item.setScript(script)
            check = entry.get('check')
            if check:
                item.setCheck(check)

        item.setLabel(entry['label'])

        if 'shortcut' in entry:
            item.setShortcut(entry['shortcut'])

        if 'icon' in entry:
            item.setIcon(entry['icon'])

        return item

    if t in ('script_submenu', 'submenu'):
        script = entry['script']
        if callable(script):
            item = hou.ui.createRadialItem(submenu=True, callback=True)
            item.setActionCallback(script)
        else:
            item = hou.ui.createRadialItem(submenu=True, callback=False)
            item.setScript(script)

        item.setLabel(entry['label'])

        if 'shortcut' in entry:
            item.setShortcut(entry['shortcut'])

        return item

    if t == 'link':
        name = entry['name']
        item = hou.ui.createRadialItem(submenu=True, callback=True)

        def func(**kwargs):
            setRadialMenu(name)

        item.setActionCallback(func)

        if 'label' in entry:
            item.setLabel(entry['label'])
        else:
            label = hou.ui.radialMenu(name).root().label()
            item.setLabel(label)

        if 'shortcut' in entry:
            item.setShortcut(entry['shortcut'])

        return item

    return None


def setRadialMenu(menu):
    if py23.isString(menu):
        hou.ui.injectRadialMenu(menu)
    else:
        for k, v in menu.items():
            location = _toLocation(k)
            item = _createRadialItem(v)
            if item:
                hou.ui.injectRadialItem(location, item)
