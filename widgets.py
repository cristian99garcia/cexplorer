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
        'item-selected': (GObject.SIGNAL_RUN_FIRST, None, [str]),
        'new-page': (GObject.SIGNAL_RUN_FIRST, None, [str]),
        'multiple-selection': (GObject.SIGNAL_RUN_FIRST, None, [object]),
        'selection-changed': (GObject.SIGNAL_RUN_FIRST, None, [object]),
        }

    def __init__(self, folder):
        Gtk.ScrolledWindow.__init__(self)

        self.history = []
        self.folders = []
        self.files = []
        self.folder = folder
        self.icon_size = G.DEFAULT_ICON_SIZE
        self.dirs = G.Dirs()
        self.model = Gtk.ListStore(str, GdkPixbuf.Pixbuf)
        self.view = Gtk.IconView()

        self.view.set_text_column(0)
        self.view.set_can_focus(True)
        self.view.set_pixbuf_column(1)
        self.view.set_model(self.model)
        self.view.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.add_events(Gdk.EventMask.KEY_RELEASE_MASK)

        self.view.connect('key-release-event', self.__key_release_event_cb)
        self.view.connect('button-press-event', self.__button_press_event_cb)
        self.view.connect('selection-changed', self.__selection_changed)

        self.add(self.view)

    def __selection_changed(self, view):
        self.emit('selection-changed', view.get_selected_items())

    def __key_release_event_cb(self, view, event):
        key = G.KEYS.get(event.keyval, False)

        if key == 'Enter':
            paths = []

            for path in self.view.get_selected_items():
                treeiter = self.model.get_iter(path)
                paths.append(self.get_path_from_treeiter(treeiter))

            if len(paths) == 1:
                self.emit('item-selected', paths[0])

            elif len(paths) >= 1:
                self.emit('multiple-selection', paths)

    def __button_press_event_cb(self, view, event):
        # FIXME: Hay que fijarse por un event.button == 3
        #        para crear el popup menu

        if event.button == 3:
            self.create_menu(event.x, event.y, event.time)
            return

        path = view.get_path_at_pos(int(event.x), int(event.y))
        if not path:
            return

        treeiter = self.model.get_iter(path)
        directory = self.get_path_from_treeiter(treeiter)

        if event.button == 2:
            self.emit('new-page', directory)

        if event.button == 1 and event.type.value_name == 'GDK_2BUTTON_PRESS':
            self.emit('item-selected', directory)

    def set_icon_size(self, icon_size):
        GObject.idle_add(self.model.clear)
        self.icon_size = icon_size
        GObject.idle_add(self.__show_icons)

    def get_path_from_treeiter(self, treeiter):
        name = self.model.get_value(treeiter, 0)
        directory = os.path.join(self.folder, name)

        if name == G.HOME_NAME:
            directory = G.HOME_DIR

        directory = directory.replace('//', '/')
        directory = directory.replace('//', '/')

        return directory

    def show_icons(self, paths):
        GObject.idle_add(self.model.clear)

        del self.folders
        del self.files

        self.folders = []
        self.files = []

        for path in paths:
            if os.path.isdir(path):
                self.folders.append(path)

            elif os.path.isfile(path):
                self.files.append(path)

        GObject.idle_add(self.__show_icons)

    def __show_icons(self):
        for path in self.folders + self.files:
            name = self.dirs[path]
            pixbuf = G.get_pixbuf_from_path(path, self.icon_size)
            self.model.append([name, pixbuf])

    def create_menu(self, x, y, time):
        print x, y, time


class InfoBar(Gtk.InfoBar):

    def __init__(self):
        Gtk.InfoBar.__init__(self)

        self.set_show_close_button(True)
        self.set_message_type(Gtk.MessageType.ERROR)

        self.connect('response', self.__response)

        hbox = self.get_content_area()
        vbox = Gtk.VBox()
        hbox.add(vbox)

        title = Gtk.Label(G.MSG_UNREADABLE_TITLE)
        title.modify_font(Pango.FontDescription('Bold 12'))
        vbox.pack_start(title, False, False, 2)

        self.msg = Gtk.Label()
        vbox.pack_start(self.msg, False, False, 0)

    def __response(self, widget, response):
        self.hide()

    def set_msg(self, path):
        msg = G.MSG_UNREADABLE_CONTENT.replace('@', '"%s"' % path)
        self.msg.set_label(msg)


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
        'new-page': (GObject.SIGNAL_RUN_FIRST, None, [str]),
        'remove-page': (GObject.SIGNAL_RUN_FIRST, None, [object]),
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

    def __close_page(self, button, view):
        self.emit('remove-page', view)

    def create_page_from_path(self, path):
        hbox = Gtk.HBox()
        label = Gtk.Label(G.Dirs()[path])
        button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_CLOSE)
        view = View(path)

        button.connect('clicked', self.__close_page, view)

        hbox.pack_start(label, False, False, 10)
        hbox.pack_end(button, False, False, 0)
        self.append_page(view, hbox)
        hbox.show_all()
        self.show_all()

        self.set_show_tabs(len(self.get_children()) > 1)
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
        # FIXME: Hay que agregar botones de desplazamientos, de lo contrario
        #        cuando haya que abrir una dirección larga, se agrandara la
        #        ventana

        folder = folder.replace('//', '/')
        folder = folder.replace('//', '/')
        self.folder = self.folder.replace('//', '/')
        self.folder = self.folder.replace('//', '/')

        if self.show_buttons:
            if self.folder.startswith(folder) and \
                self.buttonbox.get_children() and \
                (not G.HOME_DIR.startswith(self.folder) or \
                not self.buttonbox.get_children()[0].get_children()[0].get_label() == G.HOME_NAME):

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


class StatusBar(Gtk.HBox):

    __gsignals__ = {
        'icon-size-changed': (GObject.SIGNAL_RUN_FIRST, None, [int])
        }

    def __init__(self):
        Gtk.HBox.__init__(self)

        self.icon_size = G.DEFAULT_ICON_SIZE / 8
        self.set_margin_left(10)

        self.label = Gtk.Label(G.HOME_DIR)
        self.label.modify_font(Pango.FontDescription('12'))
        self.pack_start(self.label, False, False, 0)

        self.scale = Gtk.HScale.new_with_range(1, 8, 1)
        self.scale.set_draw_value(False)
        self.scale.set_value(self.icon_size)
        self.scale.set_size_request(100, -1)
        self.scale.connect('value-changed', self.__value_changed)
        self.pack_end(self.scale, False, False, 10)

    def update_label(self, folder, paths, model):
        selected = []
        for path in paths:
            treeiter = model.get_iter(path)
            name = model.get_value(treeiter, 0)
            directory = os.path.join(folder, name)

            if name == G.HOME_NAME:
                directory = G.HOME_DIR

            directory = directory.replace('//', '/')
            directory = directory.replace('//', '/')
            selected.append(directory)

        if not selected:
            self.label.set_label(folder)

        elif len(selected) == 1:
            directory = selected[0]
            self.label.set_label(directory + '    ' + G.get_size(directory))

        elif len(selected) > 1:
            folders = []
            files = []
            label = ''

            for x in selected:
                if os.path.isdir(x):
                    folders.append(x)

                if os.path.isfile(x):
                    files.append(x)

            if folders:
                label = '%d %s' % (len(folders), _('folders selecteds'))

            if folders and files:
                label += ' %s ' % _('and')

            if files:
                label += '%d %s' % (len(files), _('files selecteds'))
                if folders:
                    label = label.replace(_('selecteds'), '') + _(' selecteds')

            self.label.set_label(label)

    def __value_changed(self, widget):
        value = int(widget.get_value())
        if value != self.icon_size:
            self.icon_size = value
            self.emit('icon-size-changed', value * 16)
