"""Native overview and controls for companion browser sessions."""
from pathlib import Path
import sys
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView
from hypersolve.companion.server import CompanionServer
from hypersolve.companion.native_host import register_bridge


def build_manager(window, auto_start):
    from .dashboard_window import label, button, panel
    window.companion = CompanionServer() if auto_start else None
    if window.companion:
        window.companion.start()
    layout = window._page("Browser manager", "Every tab has its own agent. Approve a quiz, then follow its progress here.")
    stats = QHBoxLayout()
    values = {}
    for key, title in (("active","Working"),("waiting","Awaiting approval"),("selected","Answers selected"),("review","Needs review")):
        frame, body = panel()
        body.addWidget(label(title,"Muted"))
        values[key] = label("0","Title")
        body.addWidget(values[key])
        stats.addWidget(frame)
    layout.addLayout(stats)
    frame, body = panel()
    body.addWidget(label("Browser agents","Section"))
    connection = label("Connect the companion in Chrome or Edge to see your quiz tabs.","Muted")
    body.addWidget(connection)
    table = QTableWidget(0,5)
    table.setAccessibleName("Browser solving agents")
    table.setHorizontalHeaderLabels(["Quiz / browser","Status","Questions","Selected","Provider"])
    table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
    for col in range(1,5):
        table.horizontalHeader().setSectionResizeMode(col,QHeaderView.ResizeMode.ResizeToContents)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.verticalHeader().hide()
    table.setMinimumHeight(210)
    table.setStyleSheet("QTableWidget {background:white;border:0;gridline-color:#edf0f6;selection-background-color:#e9edfb;selection-color:#24293b} QHeaderView::section {background:#f3f4f8;padding:10px;border:0;color:#606b82}")
    body.addWidget(table)
    actions=QHBoxLayout()
    details=label("No quiz selected. Detection runs locally; solving begins after your approval.","Muted")
    rows=[]

    def selected():
        row=table.currentRow()
        return rows[row] if 0 <= row < len(rows) else None

    def control(action):
        job=selected()
        if not job or not window.companion:
            return
        try:
            window.companion.manager.control(job["client"],job["id"],"resume" if action=="pause" and job["paused"] else action)
            refresh()
        except ValueError as exc:
            details.setText(str(exc))

    approve=button("Approve & solve",lambda:control("approve"),True)
    pause=button("Pause",lambda:control("pause"))
    stop=button("Stop",lambda:control("stop"))
    for item in (approve,pause,stop):
        actions.addWidget(item)
    actions.addStretch()
    body.addLayout(actions)
    body.addWidget(details)
    layout.addWidget(frame)

    def selection_changed():
        job=selected()
        active=bool(job and job["phase"] not in {"completed","review","error","ignored","cancelled"})
        approve.setEnabled(bool(job and job["phase"]=="detected" and not job["approved"]))
        pause.setEnabled(bool(active and job["approved"]))
        stop.setEnabled(active)
        pause.setText("Resume" if job and job["paused"] else "Pause")
        if job:
            details.setText(job["detail"]+"\n"+job["url"])
        else:
            details.setText("No quiz selected. Detection runs locally; solving begins after your approval.")

    def refresh():
        if not window.companion:
            selection_changed()
            return
        snapshot=window.companion.manager.snapshot()
        for key, widget in values.items():
            widget.setText(str(snapshot["stats"][key]))
        selected_id=selected()["id"] if selected() else None
        rows[:]=snapshot["sessions"]
        table.blockSignals(True)
        table.setRowCount(len(rows))
        for row,job in enumerate(rows):
            browser=snapshot["clients"].get(job["client"],{}).get("browser","Browser")
            texts=(job["title"]+" · "+browser,job["status"].capitalize(),str(job["total"] or f'{job["visible"]}+'),str(len(job["selected"])),job["provider"] or "—")
            for column,text in enumerate(texts):
                item=table.item(row,column)
                if item is None:
                    item=QTableWidgetItem()
                    table.setItem(row,column,item)
                item.setText(text)
            if job["id"]==selected_id:
                table.selectRow(row)
        table.blockSignals(False)
        connection.setText(f'{len(snapshot["clients"])} browser profile(s) connected · {len(rows)} quiz session(s)' if snapshot["clients"] else "Waiting for the browser companion. Add it once using the setup steps below.")
        window.rail_state.setText("Companion connected" if snapshot["clients"] else "Workspace Chrome connected" if window.connection["connected"] else "Browser not connected")
        selection_changed()

    table.itemSelectionChanged.connect(selection_changed)
    frame, body=panel()
    body.addWidget(label("Connect your everyday browser","Section"))
    body.addWidget(label("1. Open chrome://extensions or edge://extensions and enable Developer mode.\n2. Choose Load unpacked and select HyperSolve’s browser-extension folder.\n3. Open the companion and choose Connect Windows manager. Existing tabs may need one reload.","Muted"))
    setup=QHBoxLayout()
    def open_extension():
        directory=Path(sys.executable).parent / "browser-extension" if getattr(sys,"frozen",False) else Path(__file__).resolve().parents[2] / "extension"
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory)))
    def register():
        try:
            register_bridge()
            connection.setText("Bridge registered for Chrome and Edge. Connect from the companion popup.")
        except (OSError,ValueError) as exc:
            connection.setText(str(exc))
    setup.addWidget(button("Open extension folder",open_extension))
    setup.addWidget(button("Repair browser connection",register))
    setup.addStretch()
    body.addLayout(setup)
    layout.addWidget(frame)
    layout.addStretch()
    window.agent_timer=QTimer(window)
    window.agent_timer.timeout.connect(refresh)
    if auto_start:
        window.agent_timer.start(800)
    refresh()
