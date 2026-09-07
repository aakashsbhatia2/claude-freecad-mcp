"""One line in FreeCAD's status bar.

This is the only sign inside FreeCAD that anything is driving it: whether
something is attached, what it last ran, and what FreeCAD thinks you have
clicked -- which is what the model sees when you say "this face".

It goes in as a permanent widget. Transient status messages get overwritten
by FreeCAD's own.
"""

import atexit

import FreeCADGui
from PySide import QtCore, QtWidgets

from ai_cad.server import destroy

REFRESH_MS = 500


def _selection():
    """What is clicked, in the words the model would get."""
    try:
        chosen = FreeCADGui.Selection.getSelectionEx()
    except Exception:
        return ""

    names = []
    for one in chosen:
        if one.SubElementNames:
            names.extend("%s %s" % (one.Object.Label, sub)
                         for sub in one.SubElementNames)
        else:
            names.append(one.Object.Label)

    if not names:
        return ""
    if len(names) > 2:
        return "%s and %d more" % (names[0], len(names) - 1)
    return ", ".join(names)


class Status(QtWidgets.QLabel):

    def __init__(self, bridge, parent=None):
        QtWidgets.QLabel.__init__(self, parent)
        self._bridge = bridge
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(REFRESH_MS)
        self.refresh()

    def refresh(self):
        parts = ["connected" if self._bridge.clients else "no client"]
        if self._bridge.last_tool:
            parts.append("last: %s" % self._bridge.last_tool)
        picked = _selection()
        if picked:
            parts.append("selected: %s" % picked)
        self.setText("Claude Code | " + " | ".join(parts))

    def shutdown(self):
        """Called as FreeCAD exits."""
        destroy(self._timer)


def install(main, bridge):
    status = Status(bridge, main)
    main.statusBar().addPermanentWidget(status)
    atexit.register(status.shutdown)
