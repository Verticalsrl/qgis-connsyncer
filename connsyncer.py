"""
ConnSyncer - Shows DB connections active in the project and lets you save them
Compatible with QGIS 3.x (Qt5) and QGIS 4.x (Qt6)
Vertical Srl - https://vertical-srl.it

Copyright (C) 2024-2026 Vertical Srl

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2 of the License, or (at your
option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, see <https://www.gnu.org/licenses/>.
"""

import os
from qgis.core import QgsProject, QgsMessageLog, Qgis
from qgis.PyQt.QtCore import QSettings, Qt, QUrl
from qgis.PyQt.QtWidgets import (
    QAction, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QCheckBox, QWidget, QAbstractItemView, QFrame
)
from qgis.PyQt.QtGui import QIcon, QColor, QDesktopServices

LOG_TAG = "ConnSyncer"

# ---------------------------------------------------------------------------
# Qt5 / Qt6 enum compatibility
# ---------------------------------------------------------------------------
def _qt_enum(cls, name):
    _map = {
        'AlignCenter':      ('Qt', 'AlignmentFlag'),
        'SelectRows':       ('QAbstractItemView', 'SelectionBehavior'),
        'NoEditTriggers':   ('QAbstractItemView', 'EditTrigger'),
        'DoubleClicked':    ('QAbstractItemView', 'EditTrigger'),
        'ResizeToContents': ('QHeaderView', 'ResizeMode'),
        'Stretch':          ('QHeaderView', 'ResizeMode'),
        'Interactive':      ('QHeaderView', 'ResizeMode'),
        'UserRole':         ('Qt', 'ItemDataRole'),
        'ItemIsEditable':   ('Qt', 'ItemFlag'),
    }
    sub = _map.get(name)
    if sub:
        subclass = getattr(cls, sub[1], None)
        if subclass is not None:
            val = getattr(subclass, name, None)
            if val is not None:
                return val
    return getattr(cls, name)


def log(msg, level=Qgis.Info):
    QgsMessageLog.logMessage(msg, LOG_TAG, level)


COL_CHK    = 0
COL_NAME   = 1
COL_TYPE   = 2
COL_DETAIL = 3

VERSION = "1.3.1"


# ==========================================================================
# Plugin main class
# ==========================================================================

class ConnSyncer:

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = "ConnSyncer"

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        self.action = QAction(icon, "DB Connections in Project", self.iface.mainWindow())
        self.action.setToolTip("Show DB datasources in the project and save them to DB Manager")
        self.action.triggered.connect(self.show_dialog)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToDatabaseMenu(self.menu, self.action)
        self.actions.append(self.action)

        self.action_about = QAction("About ConnSyncer", self.iface.mainWindow())
        self.action_about.triggered.connect(self.show_about)
        self.iface.addPluginToDatabaseMenu(self.menu, self.action_about)
        self.actions.append(self.action_about)

    def unload(self):
        for action in self.actions:
            self.iface.removePluginDatabaseMenu(self.menu, action)
        self.iface.removeToolBarIcon(self.action)

    def show_dialog(self):
        dlg = SyncDialog(self)
        dlg.exec()

    def show_about(self):
        dlg = AboutDialog(self.iface.mainWindow())
        dlg.exec()

    # ------------------------------------------------------------------
    # Connection extraction
    # ------------------------------------------------------------------

    def extract_connection(self, layer):
        if not hasattr(layer, 'dataProvider'):
            return None
        provider = layer.dataProvider()
        if provider is None:
            return None
        provider_name = provider.name().lower()
        source = layer.source()

        if provider_name in ("ogr", "gdal"):
            path = source.split("|")[0].strip()
            if os.path.splitext(path)[1].lower() == ".gpkg":
                if not os.path.exists(path):
                    return None
                name = os.path.splitext(os.path.basename(path))[0]
                return {"type": "gpkg", "name": name, "path": path,
                        "detail": path}

        if provider_name == "spatialite":
            from qgis.core import QgsDataSourceUri
            uri = QgsDataSourceUri(source)
            path = uri.database() or source.split("dbname=")[-1].strip().strip("'\"")
            if not os.path.exists(path):
                return None
            name = os.path.splitext(os.path.basename(path))[0]
            return {"type": "spatialite", "name": name, "path": path,
                    "detail": path}

        if provider_name == "postgres":
            from qgis.core import QgsDataSourceUri
            uri = QgsDataSourceUri(source)
            host = uri.host() or "localhost"
            port = uri.port() or "5432"
            db = uri.database()
            user = uri.username()
            pwd = uri.password()
            name = f"{db}@{host}"
            return {"type": "postgres", "name": name, "host": host,
                    "port": port, "database": db, "username": user,
                    "password": pwd, "detail": f"{host}:{port}/{db}"}

        return None

    def scan_project(self):
        found, seen = [], set()
        for layer in QgsProject.instance().mapLayers().values():
            conn = self.extract_connection(layer)
            if conn:
                key = conn.get("path") or conn["name"]
                if key not in seen:
                    seen.add(key)
                    found.append(conn)
        return found

    def is_registered(self, conn):
        s = QSettings()
        t, n = conn["type"], conn["name"]
        if t == "gpkg":
            return bool(s.value(f"providers/ogr/GPKG/connections/{n}/path"))
        if t == "spatialite":
            return bool(s.value(f"SpatiaLite/connections/{n}/sqlitepath"))
        if t == "postgres":
            return bool(s.value(f"PostgreSQL/connections/{n}/host"))
        return False

    def save_connection(self, conn, save_name):
        s = QSettings()
        t = conn["type"]
        n = save_name.strip() or conn["name"]
        if t == "gpkg":
            s.setValue(f"providers/ogr/GPKG/connections/{n}/path", conn["path"])
        elif t == "spatialite":
            s.setValue(f"SpatiaLite/connections/{n}/sqlitepath", conn["path"])
        elif t == "postgres":
            s.setValue(f"PostgreSQL/connections/{n}/host", conn["host"])
            s.setValue(f"PostgreSQL/connections/{n}/port", conn["port"])
            s.setValue(f"PostgreSQL/connections/{n}/database", conn["database"])
            s.setValue(f"PostgreSQL/connections/{n}/username", conn["username"])
            s.setValue(f"PostgreSQL/connections/{n}/password", conn["password"])
            s.setValue(f"PostgreSQL/connections/{n}/saveUsername", "true")
            s.setValue(f"PostgreSQL/connections/{n}/savePassword",
                       "true" if conn["password"] else "false")
            s.setValue(f"PostgreSQL/connections/{n}/sslmode", "SslPrefer")
            s.setValue(f"PostgreSQL/connections/{n}/authcfg", "")
        s.sync()
        log(f"Connection saved: {n} ({t})")


# ==========================================================================
# About dialog
# ==========================================================================

class AboutDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About ConnSyncer")
        self.setMinimumWidth(460)
        self.setMaximumWidth(500)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 16)

        # Header: icon + title
        header = QHBoxLayout()
        icon_lbl = QLabel()
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(icon_path):
            icon_lbl.setPixmap(QIcon(icon_path).pixmap(40, 40))
        header.addWidget(icon_lbl)
        header.addSpacing(10)
        title_block = QVBoxLayout()
        title_lbl = QLabel("<b style='font-size:14px'>ConnSyncer</b>")
        version_lbl = QLabel(f"<span style='color:#666'>Version: {VERSION} &nbsp;·&nbsp; Author: Vertical Srl — "
                              "<a href='https://vertical-srl.it'>vertical-srl.it</a></span>")
        version_lbl.setOpenExternalLinks(True)
        title_block.addWidget(title_lbl)
        title_block.addWidget(version_lbl)
        header.addLayout(title_block)
        header.addStretch()
        layout.addLayout(header)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine if hasattr(QFrame, 'HLine') else QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Sunken if hasattr(QFrame, 'Sunken') else QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # Description
        desc = QLabel(
            "Shows all DB datasources active in the current QGIS project and lets you "
            "register them in the DB Manager with a single click.<br><br>"
            "When you load a layer from a GeoPackage, SpatiaLite or PostgreSQL database, "
            "QGIS uses it as a layer source but does not automatically add it to the "
            "DB Manager connections. This means you cannot use DB Manager to create tables, "
            "run queries or save data to that source — until the connection is registered.<br><br>"
            "ConnSyncer scans the open project, lists all detected datasources, and lets "
            "you choose which ones to save and under what name."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # How to use
        how_lbl = QLabel("<b>How to use</b>")
        layout.addWidget(how_lbl)
        how = QLabel(
            "1. Open the plugin from <i>Database → ConnSyncer → DB Connections in Project</i> "
            "or from the toolbar button.<br>"
            "2. The table lists every DB datasource found in the project. "
            "Connections already registered in DB Manager are shown in grey.<br>"
            "3. Double-click on the <i>Connection name</i> column to rename a connection.<br>"
            "4. Tick the connections you want to save and click <b>Save selected</b>.<br>"
            "5. Re-open DB Manager to see the new connections."
        )
        how.setWordWrap(True)
        layout.addWidget(how)

        # Supported sources
        src_lbl = QLabel("<b>Supported datasources</b>")
        layout.addWidget(src_lbl)
        src = QLabel("GeoPackage (.gpkg) &nbsp;·&nbsp; SpatiaLite &nbsp;·&nbsp; PostgreSQL / PostGIS")
        layout.addWidget(src)

        # Separator
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine if hasattr(QFrame, 'HLine') else QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Sunken if hasattr(QFrame, 'Sunken') else QFrame.Shadow.Sunken)
        layout.addWidget(line2)

        # Report
        report = QLabel(
            "Found a bug or have a request? Contact Vertical:<br>"
            "✉ <a href='mailto:supporto@vertical-srl.it'>supporto@vertical-srl.it</a> &nbsp;&nbsp; "
            "🌐 <a href='https://vertical-srl.it'>vertical-srl.it</a>"
        )
        report.setOpenExternalLinks(True)
        layout.addWidget(report)

        # Close button
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_close.setFixedWidth(80)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(btn_close)
        layout.addLayout(row)


# ==========================================================================
# Main sync dialog
# ==========================================================================

class SyncDialog(QDialog):

    def __init__(self, plugin):
        super().__init__(plugin.iface.mainWindow())
        self.plugin = plugin
        self.setWindowTitle("ConnSyncer — DB Connections in Project")
        self.setMinimumWidth(720)
        self.setMinimumHeight(380)
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        lbl = QLabel(
            "<b>DB datasources active in the current project</b><br>"
            "<small>Double-click on the connection name to rename it before saving.</small>"
        )
        layout.addWidget(lbl)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Save", "Connection name", "Type", "Path / Host"]
        )
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(COL_CHK,    _qt_enum(QHeaderView, 'ResizeToContents'))
        hh.setSectionResizeMode(COL_NAME,   _qt_enum(QHeaderView, 'Interactive'))
        hh.setSectionResizeMode(COL_TYPE,   _qt_enum(QHeaderView, 'ResizeToContents'))
        hh.setSectionResizeMode(COL_DETAIL, _qt_enum(QHeaderView, 'Stretch'))
        self.table.setColumnWidth(COL_NAME, 200)
        self.table.setEditTriggers(_qt_enum(QAbstractItemView, 'DoubleClicked'))
        self.table.setSelectionBehavior(_qt_enum(QAbstractItemView, 'SelectRows'))
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.status = QLabel("")
        self.status.setStyleSheet("font-style: italic; color: #555;")
        layout.addWidget(self.status)

        btns = QHBoxLayout()
        btn_about = QPushButton("ℹ  About")
        btn_about.clicked.connect(lambda: AboutDialog(self).exec())
        btn_refresh = QPushButton("🔄  Refresh")
        btn_refresh.clicked.connect(self._refresh)
        self.btn_save = QPushButton("💾  Save selected")
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._save_selected)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btns.addWidget(btn_about)
        btns.addWidget(btn_refresh)
        btns.addStretch()
        btns.addWidget(self.btn_save)
        btns.addWidget(btn_close)
        layout.addLayout(btns)

    def _refresh(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self._conns = self.plugin.scan_project()

        tipo_label = {
            "gpkg": "GeoPackage",
            "spatialite": "SpatiaLite",
            "postgres": "PostgreSQL"
        }

        not_editable_flag = ~_qt_enum(Qt, 'ItemIsEditable')

        for conn in self._conns:
            already = self.plugin.is_registered(conn)
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Checkbox
            chk = QCheckBox()
            chk.setChecked(not already)
            chk.setEnabled(not already)
            w = QWidget()
            h = QHBoxLayout(w)
            h.addWidget(chk)
            h.setAlignment(_qt_enum(Qt, 'AlignCenter'))
            h.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, COL_CHK, w)
            conn["_chk"] = chk
            conn["_row"] = row

            # Name (editable only if not already registered)
            name_item = QTableWidgetItem(conn["name"])
            if already:
                name_item.setForeground(QColor("#888"))
                name_item.setToolTip("Already registered in DB Manager")
                name_item.setFlags(name_item.flags() & not_editable_flag)
            else:
                name_item.setBackground(QColor("#f0f8ff"))
                name_item.setToolTip("Double-click to rename")
            self.table.setItem(row, COL_NAME, name_item)

            # Type
            tipo_item = QTableWidgetItem(tipo_label.get(conn["type"], conn["type"]))
            tipo_item.setFlags(tipo_item.flags() & not_editable_flag)
            if already:
                tipo_item.setForeground(QColor("#888"))
            self.table.setItem(row, COL_TYPE, tipo_item)

            # Detail
            detail_item = QTableWidgetItem(conn["detail"])
            detail_item.setFlags(detail_item.flags() & not_editable_flag)
            if already:
                detail_item.setForeground(QColor("#888"))
            self.table.setItem(row, COL_DETAIL, detail_item)

        self.table.blockSignals(False)

        if not self._conns:
            self.status.setText("No DB datasources found in the project.")
            self.btn_save.setEnabled(False)
        else:
            nuove = sum(1 for c in self._conns if not self.plugin.is_registered(c))
            self.status.setText(
                f"{len(self._conns)} datasource(s) found — "
                f"{nuove} not yet registered. Double-click the name to rename."
            )
            self.btn_save.setEnabled(nuove > 0)

    def _save_selected(self):
        saved = []
        for conn in self._conns:
            chk = conn.get("_chk")
            if not (chk and chk.isChecked() and chk.isEnabled()):
                continue
            row = conn.get("_row", 0)
            name_item = self.table.item(row, COL_NAME)
            save_name = name_item.text().strip() if name_item else ""
            save_name = save_name or conn["name"]
            self.plugin.save_connection(conn, save_name)
            saved.append(save_name)

        if saved:
            self.status.setText(
                f"✅ Saved: {', '.join(saved)}. Re-open DB Manager to see them."
            )
            self._refresh()
        else:
            self.status.setText("No connection selected.")
