"""The chat panel: a dock widget that lives alongside the model tree.

Not tied to a workbench -- it stays put while you work in Part Design or
Sketcher, and is toggled from View > Panels like any other dock.
"""

from PySide import QtCore, QtWidgets

from ai_cad.chat_widget import ChatWidget

DOCK_NAME = "ConversationalCADPanel"


def install(main):
    """Create the dock if it isn't there. Safe to call more than once."""
    for dock in main.findChildren(QtWidgets.QDockWidget):
        if dock.objectName() == DOCK_NAME:
            return
    dock = QtWidgets.QDockWidget("Conversational CAD", main)
    dock.setObjectName(DOCK_NAME)
    dock.setWidget(ChatWidget())
    main.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
