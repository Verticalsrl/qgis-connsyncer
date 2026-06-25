# -*- coding: utf-8 -*-
"""
ConnSyncer - QGIS plugin
Copyright (C) 2024-2026 Vertical Srl

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2 of the License, or (at your
option) any later version. See <https://www.gnu.org/licenses/>.
"""


def classFactory(iface):
    from .connsyncer import ConnSyncer
    return ConnSyncer(iface)
