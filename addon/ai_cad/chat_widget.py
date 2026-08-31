"""The chat interface itself: transcript above, input box below."""

from PySide import QtCore, QtGui, QtWidgets

from ai_cad.responder import ModelResponder


class ChatInput(QtWidgets.QPlainTextEdit):
    """Multi-line input where Enter sends and Shift+Enter makes a new line."""

    submitted = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Ask for a change, or describe what to make...")
        self.setTabChangesFocus(True)
        self._sync_height()
        self.textChanged.connect(self._sync_height)

    def keyPressEvent(self, event):
        enter = event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter)
        if enter and not event.modifiers() & QtCore.Qt.ShiftModifier:
            self.submitted.emit()
            return
        super().keyPressEvent(event)

    def _sync_height(self):
        """Grow with the text, up to six lines, then scroll."""
        line = self.fontMetrics().lineSpacing()
        lines = min(max(self.document().size().height(), 1), 6)
        self.setFixedHeight(int(lines * line) + 12)


class ChatWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._bold = QtGui.QTextCharFormat()
        self._bold.setFontWeight(QtGui.QFont.Bold)
        self._plain = QtGui.QTextCharFormat()

        self._responder = ModelResponder(self)
        self._responder.chunk.connect(self._append_chunk)
        self._responder.thinking.connect(self._append_detail)
        self._responder.note.connect(self._append_note)
        self._responder.finished.connect(lambda: self._set_busy(False))
        self._responder.failed.connect(self._on_failed)
        self._build()

    def _build(self):
        self.transcript = QtWidgets.QTextBrowser(self)

        # Reasoning and tool calls, folded away until asked for.
        self.details_button = QtWidgets.QToolButton(self)
        self.details_button.setText("Thinking and tools")
        self.details_button.setCheckable(True)
        self.details_button.setArrowType(QtCore.Qt.RightArrow)
        self.details_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.details_button.setAutoRaise(True)
        self.details_button.toggled.connect(self._toggle_details)

        self.details = QtWidgets.QTextBrowser(self)
        self.details.setMaximumHeight(160)
        self.details.hide()

        self.input = ChatInput(self)
        self.input.submitted.connect(self._on_submit)

        self.send_button = QtWidgets.QPushButton("Send", self)
        self.send_button.clicked.connect(self._on_submit)

        self.status = QtWidgets.QLabel("", self)
        self.status.setStyleSheet("color: palette(mid);")

        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.status, 1)
        row.addWidget(self.send_button, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        layout.addWidget(self.transcript, 1)
        layout.addWidget(self.details_button, 0, QtCore.Qt.AlignLeft)
        layout.addWidget(self.details, 0)
        layout.addWidget(self.input, 0)
        layout.addLayout(row, 0)

    def _on_submit(self):
        text = self.input.toPlainText().strip()
        if not text or not self.input.isEnabled():
            return
        self.input.clear()
        self._start_detail_turn(text)
        self._write_role("You")
        self._append_chunk(text)
        self._set_busy(True)
        self._write_role("Assistant")
        self._responder.send(text)

    def _set_busy(self, busy):
        self.input.setEnabled(not busy)
        self.send_button.setEnabled(not busy)
        self.status.setText("Thinking..." if busy else "")
        if not busy:
            self.input.setFocus()

    def _toggle_details(self, shown):
        self.details.setVisible(shown)
        self.details_button.setArrowType(
            QtCore.Qt.DownArrow if shown else QtCore.Qt.RightArrow)

    def _start_detail_turn(self, text):
        if not self.details.document().isEmpty():
            self._append_detail("\n\n")
        self._append_detail("--- %s\n" % text)

    def _append_note(self, text):
        self._append_detail("\n" + text + "\n")

    def _append_detail(self, text):
        cursor = self.details.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text)
        self.details.setTextCursor(cursor)
        QtCore.QTimer.singleShot(0, self._snap_details_to_bottom)

    def _snap_details_to_bottom(self):
        bar = self.details.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _on_failed(self, message):
        self._write_role("Error")
        self._append_chunk(message)
        self._set_busy(False)

    def _write_role(self, role):
        cursor = self._cursor_at_end()
        if not self.transcript.document().isEmpty():
            cursor.insertBlock()
            cursor.insertBlock()
        cursor.insertText(role, self._bold)
        cursor.insertBlock()
        self._scroll_to_end()

    def _append_chunk(self, text):
        # State the format on every insert, or body text inherits the bold
        # used for the role heading above it.
        self._cursor_at_end().insertText(text, self._plain)
        self._scroll_to_end()

    def _cursor_at_end(self):
        cursor = self.transcript.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        self.transcript.setTextCursor(cursor)
        return cursor

    def _scroll_to_end(self):
        # Deferred: read straight after inserting text and the scrollbar's
        # maximum is still the old one, leaving the view part-way up.
        QtCore.QTimer.singleShot(0, self._snap_to_bottom)

    def _snap_to_bottom(self):
        bar = self.transcript.verticalScrollBar()
        bar.setValue(bar.maximum())
