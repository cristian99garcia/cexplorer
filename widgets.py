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
from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import Pango
from gi.repository import GObject
from gi.repository import GdkPixbuf


class View(Gtk.ScrolledWindow):

    __gsignals__ = {
        'item-selected': (GObject.SIGNAL_RUN_FIRST, None, [str])
        }

    def __init__(self, folder):
        Gtk.ScrolledWindow.__init__(self)

        self.history = []
        self.folder = folder
        self.dirs = G.Dirs()
        self.model = Gtk.ListStore(str, GdkPixbuf.Pixbuf)
        self.view = Gtk.IconView()

        self.view.set_model(self.model)
        self.view.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.view.set_text_column(0)
        self.view.set_pixbuf_column(1)

        self.view.connect('button-press-event', self.__button_press_event_cb)

        self.add(self.view)

    def __button_press_event_cb(self, view, event):
        # FIXME: Hay que fijarse por un event.button == 3
        #        para crear el popup menu

        # FIXME: Hay que agregar funcionalidad para más de una dirección

        if event.button != 1:
            return

        try:
            path = view.get_path_at_pos(int(event.x), int(event.y))
            iter = self.model.get_iter(path)
            name = self.model.get_value(iter, 0)
            directory = os.path.join(self.folder, name)
            if name in self.dirs.names:
                directory = self.dirs[name]

            if event.type.value_name == 'GDK_2BUTTON_PRESS':

                self.emit('item-selected', directory)

        except TypeError:
            pass

    def show_icons(self, paths):
        self.model.clear()

        folders = []
        files = []

        for path in paths:
            if os.path.isdir(path):
                folders.append(path)

            elif os.path.isfile(path):
                files.append(path)

        for path in folders + files:
            name = self.dirs[path]
            pixbuf = G.get_pixbuf_from_path(path)

            self.model.append([name, pixbuf])


class TreeViewItem(Gtk.EventBox):

    __gsignals__ = {
        'selected': (GObject.SIGNAL_RUN_FIRST, None, [])
        }

    def __init__(self, path, selected):
        Gtk.EventBox.__init__(self)

        self.selected = selected
        self.hbox = Gtk.HBox()

        pixbuf = G.get_pixbuf_from_path(path, size=G.DEFAULT_ITEM_ICON_SIZE)
        image = Gtk.Image.new_from_pixbuf(pixbuf)
        self.path = path
        self.label = Gtk.Label(G.Dirs()[path])
        self.label.modify_font(Pango.FontDescription('Bold 12'))

        self.set_selected(self.selected)

        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect('button-press-event', self.__button_press_event_cb)

        self.hbox.pack_start(image, False, False, 10)
        self.hbox.pack_start(self.label, False, False, 0)
        self.add(self.hbox)
        self.show_all()

    def __button_press_event_cb(self, widget, event):
        if event.button == 1 and not self.selected:
            self.emit('selected')

    def set_selected(self, selected):
        self.selected = selected

        if not selected:
            self.modify_bg(Gtk.StateType.NORMAL, G.COLOR_UNSELECTED)
            self.label.modify_fg(Gtk.StateType.NORMAL, Gdk.color_parse('#000000'))

        else:
            self.label.modify_fg(Gtk.StateType.NORMAL, Gdk.color_parse('#FFFFFF'))
            self.modify_bg(Gtk.StateType.NORMAL, G.COLOR_SELECTED)


class TreeViewMountItem(Gtk.HBox):

    def __init__(self, device, selected):
        Gtk.HBox.__init__(self)

        self.selected = selected
        self.mounted = False
        self.path = None

        if hasattr(device, 'get_default_location'):
            self.path = device.get_default_location().get_path()

        icons = device.get_icon().get_names()
        icon_theme = Gtk.IconTheme()
        pixbuf = icon_theme.choose_icon(icons, G.DEFAULT_ITEM_ICON_SIZE, 0).load_icon()
        self.image = Gtk.Image.new_from_pixbuf(pixbuf)
        self.label = Gtk.Label(device.get_name())
        self.label.modify_font(Pango.FontDescription('Bold 12'))

        self.set_selected(selected)

        self.pack_start(self.image, False, False, 10)
        self.pack_start(self.label, False, False, 0)

    def set_selected(self, selected):
        self.selected = selected

        if not selected:
            self.modify_bg(Gtk.StateType.NORMAL, G.COLOR_UNSELECTED)
            self.label.modify_fg(Gtk.StateType.NORMAL, Gdk.color_parse('#000000'))

        else:
            self.label.modify_fg(Gtk.StateType.NORMAL, Gdk.color_parse('#FFFFFF'))
            self.modify_bg(Gtk.StateType.NORMAL, G.COLOR_SELECTED)


class LateralView(Gtk.ScrolledWindow):

    __gsignals__ = {
        'item-selected': (GObject.SIGNAL_RUN_FIRST, None, [str])
        }

    def __init__(self):
        Gtk.ScrolledWindow.__init__(self)

        self.items = []
        self.label_mount_added = False
        self.dirs = G.Dirs()
        self.view = Gtk.VBox()
        self.volume_monitor = Gio.VolumeMonitor.get()

        self.set_size_request(200, -1)
        self.view.modify_bg(Gtk.StateType.NORMAL, G.COLOR_UNSELECTED)

        self.append_section(_('Personal'))

        for path in self.dirs:
            self.append_item(path, selected=path==G.HOME_DIR)

        for device in self.volume_monitor.get_volumes():
            self.add_device(device)

        self.volume_monitor.connect('mount-added', self.add_mount)
        self.volume_monitor.connect('mount-removed', self.remove_mount)

        self.add(self.view)
        self.show_all()

    def add_mount(self, deamon, device):
        self.add_device(device)

    def add_device(self, device):
        if not self.label_mount_added:
            self.label_mount_added = True
            self.append_section(_('Mounts'))

        item = TreeViewMountItem(device, False)
        self.items.append(item)
        self.view.pack_start(item, False, False, 0)

        item.show_all()

    def append_section(self, name):
        hbox = Gtk.HBox()
        label = Gtk.Label(name)
        label.modify_font(Pango.FontDescription('Bold 12'))

        if name != _('Personal'):
            vbox = Gtk.VBox()
            vbox.set_size_request(-1, 20)
            self.view.pack_start(vbox, False, False, 0)

        self.view.pack_start(label, False, False, 0)
        self.show_all()

    def append_item(self, path, selected=False):
        item = TreeViewItem(path, selected)
        item.connect('selected', self.__item_selected)
        self.items.append(item)
        self.view.pack_start(item, False, False, 0)
        #self.show_all()

    def remove_mount(self, deamon, device):
        pass

    def __item_selected(self, item):
        for _item in self.items:
            _item.set_selected(_item == item)

        if item.path:
            self.emit('item-selected', item.path)

    def select_item(self, path):
        for item in self.items:
            if item.path and not item.path.endswith('/'):
                item.path += '/'

            if not path.endswith('/'):
                path += '/'

            item.set_selected(item.path == path)


class Notebook(Gtk.Notebook):

    __gsignals__ = {
        'new-page': (GObject.SIGNAL_RUN_FIRST, None, [str])
        }

    def __init__(self):
        Gtk.Notebook.__init__(self)

        button_add = Gtk.ToolButton.new_from_stock(Gtk.STOCK_ADD)
        button_add.connect('clicked', self.__new_page_without_path)

        self.set_scrollable(True)
        self.set_show_tabs(False)
        self.set_action_widget(button_add, Gtk.PackType.END)
        button_add.show_all()

    def __new_page_without_path(self, *args):
        self.emit('new-page', '')

    def create_page_from_path(self, path):
        hbox = Gtk.HBox()
        label = Gtk.Label(G.Dirs()[path])
        button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_CLOSE)
        view = View(path)

        self.set_show_tabs(len(self.get_children()) > 1)

        hbox.pack_start(label, False, False, 10)
        hbox.pack_end(button, False, False, 0)
        self.append_page(view, hbox)
        hbox.show_all()
        self.show_all()

        self.set_current_page(self.get_n_pages() - 1)

        return view


class PlaceBox(Gtk.HeaderBar):

    __gsignals__ = {
        'go-back': (GObject.SIGNAL_RUN_FIRST, None, []),
        'go-forward': (GObject.SIGNAL_RUN_FIRST, None, []),
        'go-up': (GObject.SIGNAL_RUN_FIRST, None, []),
        'change-directory': (GObject.SIGNAL_RUN_FIRST, None, [str]),
        }

    def __init__(self):
        Gtk.HeaderBar.__init__(self)

        self.hbox = Gtk.HBox()
        self.place_buttonbox = Gtk.HBox()
        self.show_buttons = True
        self.buttons = []
        self.dirs = G.Dirs()
        self.folder = G.HOME_DIR

        self.set_show_close_button(True)

        self.navigate_buttonbox = Gtk.HBox()
        Gtk.StyleContext.add_class(
            self.navigate_buttonbox.get_style_context(), 'linked')

        self.button_left = Gtk.Button()
        arrow = Gtk.Arrow(Gtk.ArrowType.LEFT, Gtk.ShadowType.NONE)
        arrow.set_size_request(28, 28)
        self.button_left.connect('clicked', self.__go, 'go-back')
        self.button_left.add(arrow)
        self.navigate_buttonbox.add(self.button_left)

        self.button_right = Gtk.Button()
        arrow = Gtk.Arrow(Gtk.ArrowType.RIGHT, Gtk.ShadowType.NONE)
        arrow.set_size_request(28, 28)
        self.button_right.connect('clicked', self.__go, 'go-forward')
        self.button_right.add(arrow)
        self.navigate_buttonbox.add(self.button_right)

        self.button_up = Gtk.Button()
        arrow = Gtk.Arrow(Gtk.ArrowType.UP, Gtk.ShadowType.NONE)
        arrow.set_size_request(28, 28)
        self.button_up.connect('clicked', self.__go, 'go-up')
        self.button_up.add(arrow)
        self.navigate_buttonbox.add(self.button_up)

        self.buttonbox = Gtk.HBox()
        Gtk.StyleContext.add_class(self.buttonbox.get_style_context(), 'linked')

        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text('Select a directory')
        self.entry.connect('activate', self.__change_directory)

        #self.entry.set_text(G.HOME_DIR)
        self.set_folder(G.HOME_DIR)

        self.hbox.pack_start(self.navigate_buttonbox, False, False, 10)
        #self.hbox.pack_start(self.entry, True, True, 0)
        self.hbox.pack_start(self.buttonbox, True, True, 0)
        self.add(self.hbox)

    def set_folder(self, folder):
        folder = folder.replace('//', '/')
        folder = folder.replace('//', '/')
        self.folder = self.folder.replace('//', '/')
        self.folder = self.folder.replace('//', '/')

        if self.show_buttons:
            if self.folder.startswith(folder) and \
                self.buttonbox.get_children() and self.folder != G.HOME_DIR:

                self.folder = folder
                return

            self.folder = folder

            del self.buttons
            self.buttons = []

            if not folder.startswith(G.HOME_DIR):
                self.buttons.append('/')

            while self.buttonbox.get_children():
                self.buttonbox.remove(self.buttonbox.get_children()[0])

            if folder.startswith(G.HOME_DIR):
                self.buttons.append(G.HOME_NAME)
                folder = folder[len(G.HOME_DIR):]
                folder = folder[1:] if folder.startswith('/') else folder

            for x in folder.split('/'):
                if x:
                    self.buttons.append(x)

            path = ''
            for x in self.buttons:
                if x == G.HOME_NAME:
                    path += G.HOME_DIR + '/'

                else:
                    if not path.endswith('/'):
                        path += '/'

                    path += x + '/'

                if x == G.SYSTEM_DIR:
                    x = self.dirs[G.SYSTEM_DIR]

                label = Gtk.Label(x)
                label.modify_font(Pango.FontDescription('Bold 12'))
                button = Gtk.Button()
                button.path = path
                button.connect('clicked', self.__button_clicked)
                button.add(label)
                self.buttonbox.add(button)

        self.entry.set_text(folder)
        self.show_all()

    def __go(self, widget, direction):
        self.emit(direction)

    def __change_directory(self, entry):
        self.emit('change-directory', entry.get_text())

    def __button_clicked(self, button):
        self.emit('change-directory', button.path)
