#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2014, Cristian García <cristian99garcia@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os
import globals as G

from gi.repository import Gtk
from gi.repository import GObject

from widgets import View
from widgets import InfoBar
from widgets import Notebook
from widgets import PlaceBox
from widgets import StatusBar
from widgets import LateralView


class CExplorer(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self)

        self.dirs = G.Dirs()
        self.folder = G.HOME_DIR
        self.folder_name = self.dirs[self.folder]
        self.scan_folder = G.ScanFolder(self.folder)
        self.other_view = False
        self.view = None
        self.icon_size = G.DEFAULT_ICON_SIZE

        self.vbox = Gtk.VBox()
        self.paned = Gtk.HPaned()
        self.place_box = PlaceBox()
        self.lateral_view = LateralView()
        self.notebook = Notebook()
        self.infobar = InfoBar()
        self.statusbar = StatusBar()

        self.new_page()
        self.resize(620, 480)
        self.set_title(self.folder_name)
        self.set_titlebar(self.place_box)

        self.connect('destroy', Gtk.main_quit)
        self.connect('check-resize', self.__size_changed_cb)
        self.place_box.connect('go-up', self.go_up)
        self.place_box.connect('change-directory', self.__item_selected)
        self.lateral_view.connect('item-selected', self.__item_selected)
        self.notebook.connect('switch-page', self.__switch_page)
        self.notebook.connect('new-page', lambda w, p: self.new_page(p))
        self.notebook.connect('remove-page', self.__remove_page_from_notebook)
        self.scan_folder.connect('files-changed', self.update_icons)
        self.statusbar.connect('icon-size-changed', self.__icon_size_changed)

        self.lateral_view.select_item(G.HOME_DIR)
        self.paned.pack1(self.lateral_view, False)
        self.paned.pack2(self.notebook, True)
        self.vbox.pack_start(self.infobar, False, False, 0)
        self.vbox.pack_start(self.paned, True, True, 2)
        self.vbox.pack_start(self.statusbar, False, False, 2)

        self.add(self.vbox)
        self.show_all()
        self.infobar.hide()

    def __size_changed_cb(self, widget):
        self.place_box.entry.set_size_request(self.get_size()[0] / 2, -1)

    def __item_selected(self, widget, path):
        # FIXME: Hay que actualizar las etiquetas de las pestañas

        if os.path.isdir(path) and path != self.folder:
            self.set_folder(path)

    def __multiple_selection(self, widget, paths):
        # FIXME: falta abrir archivos

        directories = 0
        folders = []

        for path in paths:
            if os.path.isdir(path):
                folders.append(path)
                directories += 1

        if directories == 1:
            self.set_folder(folders[0])

        elif directories > 1:
            for folder in folders:
                self.new_page(folder)

    def __switch_page(self, notebook, view, page):
        GObject.idle_add(self.update_widgets, view=view)

    def __remove_page_from_notebook(self, notebook, view):
        idx = self.notebook.get_children().index(view)
        self.remove_page(idx)

    def __icon_size_changed(self, widget, value):
        self.icon_size = value
        for view in self.notebook.get_children():
            GObject.idle_add(view.set_icon_size, value)

    def __update_statusbar(self, view, selection):
        self.statusbar.update_label(view.folder, selection, view.model)

    def remove_page(self, idx=None, view=None):
        if not view:
            if idx is None:
                idx = self.get_current_page()

            view = self.notebook.get_children()[idx]

        self.notebook.remove(view)
        if not self.notebook.get_children():
            self.new_page()

        self.notebook.set_show_tabs(len(self.notebook.get_children()) > 1)

    def set_folder(self, folder):
        readable, writable = G.get_access(folder)
        if readable:
            self.folder = folder
            self.get_actual_view().folder = folder
            self.place_box.set_folder(folder)
            self.scan_folder.set_folder(folder)

        else:
            self.infobar.set_msg(folder)
            self.infobar.show_all()

        GObject.idle_add(self.update_widgets, force=False)

    def go_up(self, *args):
        self.set_folder(G.get_parent_directory(self.folder))

    def new_page(self, path=''):
        path = G.HOME_DIR if not path else path
        view = self.notebook.create_page_from_path(path)
        view.icon_size = self.icon_size
        view.connect('selection-changed', self.__update_statusbar)
        view.connect('item-selected', self.__item_selected)
        view.connect('multiple-selection', self.__multiple_selection)
        view.connect('new-page', lambda x, p: self.new_page(p))

    def update_widgets(self, view=None, force=True):
        # FIXME: hay que fijarse la posición actual con respecto al historial
        #        para poder hacer set_sensitive

        update_icons = False
        if (not view or not isinstance(view, Gtk.ScrolledWindow)) and force:
            view = self.get_actual_view()
            update_icons = True

        self.view = view
        self.other_view = True
        self.folder = view.folder

        GObject.idle_add(self.place_box.set_folder, view.folder)
        #self.place_box.button_left.set_sensitive(bool(view.history))
        #self.place_box.button_right.set_sensitive(bool(view.history))
        self.place_box.button_up.set_sensitive(view.folder != G.SYSTEM_DIR)
        self.lateral_view.select_item(self.folder)
        self.scan_folder.set_folder(view.folder)
        self.scan_folder.scan(force=update_icons)

    def update_icons(self, scan_folder, paths):
        view = self.get_actual_view()
        GObject.idle_add(view.show_icons, paths)

    def get_actual_view(self):
        if not self.other_view:
            idx = self.notebook.get_current_page()
            return self.notebook.get_children()[idx]

        else:
            self.other_view = False
            return self.view


if __name__ == '__main__':
    CExplorer()
    Gtk.main()
