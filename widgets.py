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


class SearchEntry(Gtk.Window):

    __gsignals__ = {
        'search-changed': (GObject.SIGNAL_RUN_FIRST, None, [str]),
        'select': (GObject.SIGNAL_RUN_FIRST, None, []),
        }

    def __init__(self):
        Gtk.Window.__init__(self)

        self.width = 200
        self.height = -1
        self.timeout = None
        self.entry = Gtk.SearchEntry()

        self.resize(self.width, self.height)
        self.entry.set_size_request(self.width, self.height)

        self.connect('hide', self.__hide_cb)
        self.connect('show', self.__show_cb)
        self.connect('realize', self.__realize_cb)
        self.connect('destroy-event', self.__destroy_event_cb)
        self.entry.connect('changed', self.__text_changed_cb)
        self.entry.connect('focus-out-event', self.__focus_out_event_cb)
        self.entry.connect('key-press-event', self.__key_press_event_cb)

        self.add(self.entry)
        self.show_all()

    def set_pos(self, x, y):
        allocation = self.entry.get_allocation()
        #x += allocation.width
        #x += 10
        y += allocation.height
        self.move(x, y)

    def _show(self, text):
        #self.entry.set_selection(-1, -1)
        self.show_all()
        self.entry.set_text(text)
        self.entry.set_position(-1)

    def reset_timeout(self):
        if self.timeout:
            GObject.source_remove(self.timeout)

        self.timeout = GObject.timeout_add(5000, self.hide)

    def __hide_cb(self, window):
        if self.timeout:
            GObject.source_remove(self.timeout)
            self.timeout = None

    def __show_cb(self, window):
        self.reset_timeout()

    def __realize_cb(self, window):
        self.hide()
        self.set_decorated(0)

    def __destroy_event_cb(self, window, event):
        self.hide()
        return False

    def __text_changed_cb(self, entry):
        if self.entry.get_text():
            self.reset_timeout()
            self.emit('search-changed', self.entry.get_text())

    def __focus_out_event_cb(self, widget, event):
        self.hide()

    def __key_press_event_cb(self, widget, event):
        if not event.keyval in G.KEYS:
            return

        key = G.KEYS[int(event.keyval)]
        if key == 'Scape':
            self.hide()

        elif key == 'Enter':
            self.hide()
            self.emit('select')


class View(Gtk.ScrolledWindow):

    __gsignals__ = {
        'item-selected': (GObject.SIGNAL_RUN_FIRST, None, [object]),
        'new-page': (GObject.SIGNAL_RUN_FIRST, None, [object]),
        'selection-changed': (GObject.SIGNAL_RUN_FIRST, None, [object]),
        'reverse-changed': (GObject.SIGNAL_RUN_FIRST, None, [bool]),
        'show-properties': (GObject.SIGNAL_RUN_FIRST, None, [object]),
        'mkdir': (GObject.SIGNAL_RUN_FIRST, None, []),
        'cut': (GObject.SIGNAL_RUN_FIRST, None, [object]),
        'copy': (GObject.SIGNAL_RUN_FIRST, None, [object]),
        'paste': (GObject.SIGNAL_RUN_FIRST, None, [str]),
        }

    def __init__(self, view_mode, folder):
        Gtk.ScrolledWindow.__init__(self)

        self.history = []
        self.folders = []
        self.files = []
        self.folder = folder
        self.icon_size = G.DEFAULT_ICON_SIZE
        self.dirs = G.Dirs()
        self.menu = None
        self.sort = G.SORT_BY_NAME
        self.reverse = False
        self.activation = G.ACTIVATION_WITH_TWO_CLICKS

        if view_mode == G.MODE_ICONS:
            self.__make_icon_view()

        elif view_mode == G.MODE_LIST:
            self.__make_list_view()

    def get_path_from_treeiter(self, treeiter):
        name = self.model.get_value(treeiter, 0)
        directory = os.path.join(self.folder, name)

        if name == G.HOME_NAME:
            directory = G.HOME_DIR

        return G.clear_path(directory)

    def set_icon_size(self, icon_size):
        if icon_size != self.icon_size:
            GObject.idle_add(self.model.clear)
            self.icon_size = icon_size
            GObject.idle_add(self.__show_icons)

    def mkdir(self, *args):
        self.emit('mkdir')

    def cut(self, *args):
        self.emit('cut', self.get_selected_paths())

    def copy(self, *args):
        self.emit('copy', self.get_selected_paths())

    def paste(self, *args):
        folder = self.folder
        for path in self.get_selected_paths():
            if os.path.isdir(path):
                folder = path
                break

        self.emit('paste', self.folder)

    def make_menu(self, paths):
        data = {'sort': self.sort,
                'reverse': self.reverse,
                'open-from-menu': self.__open_from_menu,
                'mkdir': self.mkdir,
                'cut': self.cut,
                'copy': self.copy,
                'paste': self.paste,
                'rename': self.__rename,
                'sort-changed': self.__sort_changed,
                'reverse-changed': self.__reverse_changed,
                'show-properties': self.__show_properties,
                'compress': self.__compress,
                'move-to-trash': self.__move_to_trash,
                'remove': self.__remove}

        self.menu = G.make_menu(paths, self.folder, data)

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

        GObject.idle_add(self._show_icons)

    def __make_icon_view(self):
        self.model = Gtk.ListStore(str, GdkPixbuf.Pixbuf)
        self.view = Gtk.IconView()

        self.view.set_text_column(0)
        self.view.set_pixbuf_column(1)
        self.view.set_can_focus(True)
        self.view.set_model(self.model)
        self.view.set_item_padding(0)
        self.view.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.add(self.view)

    def __make_list_view(self):
        self.model = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str, str, str, str)
        # Icon, Name, Size, Type, Modified, Path

        self.view = Gtk.TreeView()
        self.view.set_can_focus(True)
        self.view.set_model(self.model)
        self.add(self.view)

        self.selection = self.view.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)

        col_name = Gtk.TreeViewColumn(title=_('Name'))
        col_name.set_expand(True)
        #col_name.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)

        cell_icon = Gtk.CellRendererPixbuf()
        cell_text = Gtk.CellRendererText()
        col_name.pack_start(cell_icon, False)
        col_name.pack_start(cell_text, True)

        col_name.add_attribute(cell_icon, 'pixbuf', 0)
        col_name.add_attribute(cell_text, 'text', 1)

        self.view.append_column(col_name)

        number = 2
        for name in [_('Size'), _('Type'), _('Modified')]:
            col = Gtk.TreeViewColumn(title=name)
            cell = Gtk.CellRendererText()
            col.pack_start(cell, True)
            col.add_attribute(cell, 'text', number)

            self.view.append_column(col)
            number += 1

    def __open_from_menu(self, item, new_page=False):
        paths = self.get_selected_paths()

        if new_page:
            for path in paths:
                self.emit('new-page', path)

        elif not new_page:
            self.emit('item-selected', paths)

    def __rename(self, *args):
        pass

    def __compress(self, *args):
        pass

    def __sort_changed(self, item, sort):
        self.sort = sort

    def __reverse_changed(self, item):
        self.reverse = not self.reverse
        self.emit('reverse-changed', self.reverse)

    def __show_properties(self, item):
        self.emit('show-properties', self.get_selected_paths())

    def __move_to_trash(self, *args):
        pass

    def __remove(self, *args):
        pass


class IconView(View):

    def __init__(self, folder):
        View.__init__(self, G.MODE_ICONS, folder)

        # FIXME: Cuando se abre una nueva pestaña, y se regresa a la inicial,
        #        se pierde la selección anteriror, hay que guardar los objetos
        #        seleccionados y volverlos a seleccionar.

        self.view.connect('button-press-event', self.__button_press_event_cb)
        self.view.connect('selection-changed', self.__selection_changed)

    def get_selected_paths(self):
        selected = []
        for path in self.view.get_selected_items():
            treeiter = self.model.get_iter(path)
            name = self.model.get_value(treeiter, 0)
            directory = os.path.join(self.folder, name)

            if name == G.HOME_NAME:
                directory = G.HOME_DIR

            selected.append(G.clear_path(directory))

        return selected

    def get_selected_paths(self):
        paths = []

        for path in self.view.get_selected_items():
            treeiter = self.model.get_iter(path)
            paths.append(self.get_path_from_treeiter(treeiter))

        return paths

    def select_all(self):
        self.select_all()

    def __selection_changed(self, view):
        self.emit('selection-changed', self.get_selected_paths())

    def __button_press_event_cb(self, view, event):
        path = view.get_path_at_pos(int(event.x), int(event.y))
        selection = view.get_selected_items()
        paths = []

        if event.button == 3:
            if not path in selection:
                self.view.unselect_all()
                selection = []

                if path:
                    self.view.select_path(path)
                    selection = view.get_selected_items()

            for treepath in selection:
                treeiter = self.model.get_iter(treepath)
                paths.append(self.get_path_from_treeiter(treeiter))

            if not paths:
                paths = [self.folder]

            self.make_menu(paths)
            self.menu.popup(None, None, None, None, event.button, event.time)
            return True

        if not path:
            return

        treeiter = self.model.get_iter(path)
        directory = self.get_path_from_treeiter(treeiter)

        if event.button == 2:
            self.emit('new-page', directory)

        if event.button == 1 and event.type.value_name == self.activation:
            self.emit('item-selected', directory)

    def _show_icons(self):
        if self.reverse:
            self.folders.sort()
            self.folders.reverse()
            self.files.sort()
            self.files.reverse()
            paths = self.files + self.folders

        elif not self.reverse:
            self.folders.sort()
            self.files.sort()
            paths = self.folders + self.files

        for path in paths:
            name = self.dirs[path]
            pixbuf = G.get_pixbuf_from_path(path, self.icon_size)
            self.model.append([name, pixbuf])


class ListView(View):

    def __init__(self, folder):
        View.__init__(self, G.MODE_LIST, folder)

        self.selected_paths = []
        self.view.connect('button-press-event', self.__button_press_event_cb)
        self.selection.connect('changed', self.__selection_changed_cb)

    def get_selected_paths(self):
        return self.selected_paths

    def select_all(self):
        self.selection.select_all()

    def _show_icons(self):
        if self.reverse:
            self.folders.sort()
            self.folders.reverse()
            self.files.sort()
            self.files.reverse()
            paths = self.files + self.folders

        elif not self.reverse:
            self.folders.sort()
            self.files.sort()
            paths = self.folders + self.files

        self.model.clear()

        for path in paths:
            pixbuf = G.get_pixbuf_from_path(path, self.icon_size)
            name = self.dirs[path]
            size = G.get_simple_size(path)
            _type = G.get_simple_type(path)
            modified = G.get_simple_modified_time(path)

            self.model.append([pixbuf, name, size, _type, modified, path])

        self.show_all()

    def __button_press_event_cb(self, view, event):
        data = view.get_path_at_pos(int(event.x), int(event.y))
        treepath = data[0] if data else None
        treeiter = self.model.get_iter(treepath) if treepath else None
        path = self.model.get_value(treeiter, 5) if treeiter else self.folder

        if self.selected_paths:
            if event.button == 1 and event.type.value_name == self.activation:
                self.emit('item-selected', path)

            elif event.button == 2:
                self.emit('new-page', path)

        if event.button == 3:
            if not path in self.selected_paths and bool(treepath):
                self.selection.unselect_all()
                self.selection.select_iter(treeiter)

            self.make_menu(
                self.selected_paths if self.selected_paths else [self.folder])
            self.menu.popup(None, None, None, None, event.button, event.time)
            return True

    def __selection_changed_cb(self, selection):
        del self.selected_paths
        self.selected_paths = []
        model, treepaths = self.selection.get_selected_rows()

        for treepath in treepaths:
            treeiter = model.get_iter(treepath)
            self.selected_paths.append(model.get_value(treeiter, 5))

        self.emit('selection-changed', self.selected_paths)

    def __open_from_menu(self, item, new_page=False):
        if new_page:
            for path in self.selected_paths:
                self.emit('new-page', path)

        elif not new_page:
            self.emit('item-selected', self.selected_paths)


class InfoBar(Gtk.InfoBar):

    def __init__(self):
        Gtk.InfoBar.__init__(self)

        self.set_show_close_button(True)
        self.set_message_type(Gtk.MessageType.ERROR)

        self.connect('response', self.__hide)
        self.connect('realize', self.__hide)

        hbox = self.get_content_area()
        vbox = Gtk.VBox()
        hbox.add(vbox)

        self.title = Gtk.Label()
        self.title.modify_font(Pango.FontDescription('Bold 12'))
        vbox.pack_start(self.title, False, False, 2)

        self.msg = Gtk.Label()
        vbox.pack_start(self.msg, False, False, 0)

    def set_msg(self, msg_type, info):
        if msg_type == G.ERROR_NOT_READABLE:
            self.title.set_label(G.TITLE_ERROR_UNREADABLE)
            self.msg.set_label(G.MSG_UNREADABLE.replace('@', info))

        elif msg_type == G.ERROR_NOT_UNWRITABLE:
            self.title.set_label(G.TITLE_ERROR_UNWRITABLE)
            self.msg.set_label(G.MSG_UNWRITABLE.replace('@', info))

        elif msg_type == G.ERROR_ALREADY_EXISTS:
            self.title.set_label(G.TITLE_ERROR_ALREADY_EXISTS)
            self.msg.set_label(G.MSG_ALREADY_EXISTS.replace('@', info))

        elif msg_type == G.ERROR_INVALID_NAME:
            self.title.set_label(G.TITLE_ERROR_INVALID_NAME)
            self.msg.set_label(G.MSG_INVALID_NAME.replace('@', info))

        elif msg_type == G.ERROR_NOT_EXISTS:
            self.title.set_label(G.TITLE_ERROR_NOT_EXISTS)
            self.msg.set_label(G.MSG_NOT_EXISTS.replace('@', info))

    def __hide(self, widget, response=None):
        GObject.idle_add(self.hide)


class MkdirInfoBar(Gtk.InfoBar):

    __gsignals__ = {
        'mkdir': (GObject.SIGNAL_RUN_FIRST, None, [str])
        }

    def __init__(self):
        Gtk.InfoBar.__init__(self)

        self.set_show_close_button(True)
        self.set_message_type(Gtk.MessageType.QUESTION)

        hbox = self.get_content_area()
        vbox = Gtk.VBox()

        label = Gtk.Label(_('Select a name of the new dir'))
        label.modify_font(Pango.FontDescription('Bold'))
        vbox.pack_start(label, False, False, 0)

        self.entry = Gtk.Entry()
        self.entry.set_text(_('New folder'))
        self.entry.set_placeholder_text(_('Select a name for the new folder'))
        self.entry.connect('activate', self.__mkdir)
        vbox.pack_start(self.entry, False, False, 0)

        self.connect('response', lambda _self, response: self.hide())
        self.connect('realize', self.__realize_cb)

        hbox.add(vbox)
        self.show_all()

    def __mkdir(self, entry):
        if entry.get_text():
            self.emit('mkdir', entry.get_text())

        self.destroy()

    def __realize_cb(self, widget):
        self.entry.grab_focus()


class LateralView(Gtk.ScrolledWindow):

    __gsignals__ = {
        'item-selected': (GObject.SIGNAL_RUN_FIRST, None, [str]),
        'new-page': (GObject.SIGNAL_RUN_FIRST, None, [str]),
        'copy': (GObject.SIGNAL_RUN_FIRST, None, [str]),
        'show-properties': (GObject.SIGNAL_RUN_FIRST, None, [str]),
        'copy': (GObject.SIGNAL_RUN_FIRST, None, [object]),
        'paste': (GObject.SIGNAL_RUN_FIRST, None, [str]),
        }

    def __init__(self):
        Gtk.ScrolledWindow.__init__(self)

        self.rows = {}
        self.paths = {}
        self.volume_monitor = Gio.VolumeMonitor.get()
        self.menu = None
        self.view = Gtk.ListBox()
        #  GtkListBoxRow structur when is a mount or a device:
        #      GtkListBoxRow: add properties "data" and "_path"
        #        +-- GtkHBox
        #              +-- GtkImage(device image)
        #              +-- GtkVBox
        #              |     +-- GtkHBox
        #              |     |     +-- GtkLabel(show the device name)
        #              |     +-- GtkLevelBar
        #              +-- GtkEventBox
        #                    +-- GtkImage
        #
        #  GtkListBoxRow structur when is a normal folder:
        #      GtkListBoxRow: add property "_path"
        #        +-- GtkHBox
        #              +-- GtkImage(folder image)
        #              +-- GtkLabel(Show the folder name)
        #
        #  GtkListBoxRow structur when is a section indicator:
        #      GtkListBoxRow: set property "sensitive" to False
        #        +-- GtkHBox
        #              +-- GtkLabel(Show the section name)

        self.dirs = G.Dirs()
        self.folder = None
        self._emit = True
        self.__devices_section_added = False

        self.view.set_selection_mode(Gtk.SelectionMode.SINGLE)

        self.connect('realize', self.__realize_cb)
        self.volume_monitor.connect('mount-added', self.add_mount)
        self.volume_monitor.connect('mount-removed', self.remove_mount)

        self.add_section(_('Places'))
        self.make_items()
        self.select_item(G.HOME_DIR)
        self.set_size_request(200, -1)

        for volume in self.volume_monitor.get_volumes():
            self.add_mount(self.volume_monitor, volume)

        self.view.connect('row-selected', self.__selection_changed)
        self.view.connect('button-press-event', self.__button_press_event_cb)
        self.add(self.view)

    def mount_done_cb(self, volume, result, loop, row):
        volume.mount_finish(result)
        loop.quit()

        self.folder = volume.get_mount().get_root().get_path()
        self.dirs.add_mount(self.folder)
        row.path = self.folder
        row.data['path'] = self.folder
        self.emit('item-selected', self.folder)

        total_space, used_space, free_space = G.get_mount_space(self.folder)
        row.data['levelbar'].set_min_value(0)
        row.data['levelbar'].set_max_value(total_space)
        row.data['levelbar'].set_value(used_space)
        row.data['levelbar'].show()

        if not 'umontable' in row.data or \
                ('umontable' in row.data and row.data['umontable']):

            row.data['button-close'].show_all()

    def __realize_cb(self, widget):
        for row in self.view.get_children():
            if not hasattr(row, 'data'):
                continue

            data = row.data
            if ('volume' in data and not data['volume'].get_mount()) or \
                    ('mounted' in data and not data['mounted']):

                data['levelbar'].hide()
                data['button-close'].hide()

            if 'umontable' in data and not data['umontable']:
                data['button-close'].hide()

    def __selection_changed(self, listbox, row):
        if not row:
            return

        if not self._emit:
            self._emit = True
            return

        if not hasattr(row, 'data'):
            self.folder = row._path
            self.emit('item-selected', self.folder)

        elif hasattr(row, 'data'):
            data = row.data
            if data['path']:
                self.folder = data['path']
                self.emit('item-selected', self.folder)

            else:
                if not data['mounted']:
                    # Try mount
                    mo = Gio.MountOperation()
                    mo.set_anonymous(True)
                    loop = GObject.MainLoop()
                    data['volume'].mount(
                        0, mo, None, self.mount_done_cb, loop, row)
                    loop.run()

    def make_menu(self, row):
        path = self.paths[row]
        self.menu = Gtk.Menu()

        item = Gtk.MenuItem(_('Open'))
        item.connect('activate', lambda i: self.emit('item-selected', path))
        self.menu.append(item)

        item = Gtk.MenuItem(_('Open in new tab'))
        item.connect('activate', lambda i: self.emit('new-page', path))
        self.menu.append(item)

        self.menu.append(Gtk.SeparatorMenuItem())

        item = Gtk.MenuItem(_('Copy'))  # Copy path to clipboard
        item.connect('activate', lambda i: self.emit('copy'), path)
        self.menu.append(item)

        self.menu.append(Gtk.SeparatorMenuItem())

        item = Gtk.MenuItem(_('Properties'))
        item.connect('activate', lambda i: self.emit('show-properties', path))
        self.menu.append(item)

        self.menu.connect('hide', self.__reselect_row)
        self.menu.show_all()

    def add_section(self, name):
        row = Gtk.ListBoxRow()
        row.set_sensitive(False)
        self.view.add(row)

        hbox = Gtk.HBox()
        row.add(hbox)

        label = Gtk.Label(name)
        label.modify_font(Pango.FontDescription('bold'))
        hbox.pack_start(label, False, False, 10)

    def make_items(self):
        for x in self.dirs:
            if x != '/':
                self.add_folder(x)

            else:
                data = {'mounted': True, 'umontable': False, 'path': '/',
                        'name': self.dirs['/'], 'device': None,
                        'pixbuf': self.dirs.get_pixbuf_symbolic('/')}

                self.add_mount(data=data)

    def add_folder(self, path=None):
        if path and not path in self.dirs:
            self.remove_mount(path)

        pixbuf = self.dirs.get_pixbuf_symbolic(path)
        name = self.dirs[path]
        image = Gtk.Image.new_from_pixbuf(pixbuf)

        row = Gtk.ListBoxRow()
        row._path = path
        hbox = Gtk.HBox()
        label = Gtk.Label(name)
        label.set_ellipsize(Pango.EllipsizeMode.END)

        hbox.pack_start(image, False, False, 10)
        hbox.pack_start(label, False, False, 5)

        row.add(hbox)
        self.view.add(row)

        self.rows[path] = row
        self.paths[row] = path

    def select_item(self, path):
        path = G.clear_path(path)
        if not self.folder:
            self.folder = G.HOME_DIR

        self.folder = G.clear_path(self.folder)

        if not path in self.dirs:
            self.view.select_row(None)
            return

        if path == self.folder and self.view.get_selected_row():
            return

        self.view.select_row(self.rows[path])

    def add_mount(self, volume_monitor=None, volume=None, data=None):
        if not self.__devices_section_added:
            self.add_section(_('Devices'))
            self.__devices_section_added = True

        if data:
            hbox = Gtk.HBox()
            image = Gtk.Image.new_from_pixbuf(data['pixbuf'])
            label = Gtk.Label(data['name'])
            levelbar = Gtk.LevelBar()
            image_close = Gtk.Image.new_from_icon_name(
                'media-eject-symbolic', Gtk.IconSize.MENU)
            button_close = Gtk.EventBox()

            _hbox = Gtk.HBox()
            _hbox.pack_start(label, False, False, 0)

            if 'volume' in data:
                mount = data['volume'].get_mount()
                gfile = mount.get_root()
                path = gfile.get_path()

            elif 'path' in data:
                path = data['path']

            self.dirs.add_mount(path)

            total_space, used_space, free_space = G.get_mount_space(path)
            levelbar.set_min_value(0)
            levelbar.set_max_value(total_space)
            levelbar.set_value(used_space)

            vbox = Gtk.VBox()
            vbox.pack_start(_hbox, False, False, 0)
            vbox.pack_start(levelbar, False, False, 0)

            button_close.add(image_close)
            hbox.pack_start(image, False, False, 10)
            hbox.pack_start(vbox, True, True, 10)
            hbox.pack_end(button_close, False, False, 10)

            row = Gtk.ListBoxRow()
            row._path = path
            row.data = data
            row.data['hbox'] = hbox
            row.data['row'] = row
            row.data['total-space'] = total_space
            row.data['used-space'] = used_space
            row.data['levelbar'] = levelbar
            row.data['button-close'] = button_close

            row.add(hbox)
            self.view.add(row)
            row.show_all()

            self.rows[path] = row
            self.paths[row] = path

            if ('volume' in data and not data['volume'].get_mount()) or \
                    ('mounted' in data and not data['mounted']):

                levelbar.hide()
                button_close.hide()

            if 'umontable' in data and not data['umontable']:
                button_close.hide()

            return

        path = None
        icons = volume.get_symbolic_icon().get_names()
        icon_theme = Gtk.IconTheme()
        pixbuf = icon_theme.choose_icon(icons, 16, 0).load_icon()
        name = volume.get_name()
        total_space, used_space = 0, 0

        for _row in self.view.get_children():
            if not hasattr(_row, 'data'):
                continue

            if _row.data['name'] == name:
                if hasattr(volume, 'get_mount'):
                    mounted = bool(volume.get_mount())
                    mount = volume.get_mount()

                else:
                    mount = volume

                _row.data['mount'] = mount

                if not mount:
                    _row.data['levelbar'].hide()
                    _row.data['button-close'].hide()
                    return

                gfile = mount.get_root()
                path = gfile.get_path()
                total_space, used_space, free_space = G.get_mount_space(path)

                self.dirs.add_mount(path)

                _row.data['levelbar'].set_min_value(0)
                _row.data['levelbar'].set_max_value(total_space)
                _row.data['levelbar'].set_value(used_space)

                _row.data['levelbar'].show()
                _row.data['button-close'].show()
                return

        image = Gtk.Image.new_from_pixbuf(pixbuf)
        label = Gtk.Label(name)

        button_close = Gtk.EventBox()
        image_close = Gtk.Image.new_from_icon_name(
            'media-eject-symbolic', Gtk.IconSize.MENU)
        button_close.set_can_focus(True)
        button_close.add(image_close)

        levelbar = Gtk.LevelBar()

        _hbox = Gtk.HBox()
        _hbox.pack_start(label, False, False, 0)
        vbox = Gtk.VBox()
        vbox.pack_start(_hbox, False, False, 0)

        hbox = Gtk.HBox()
        hbox.pack_start(image, False, False, 10)
        hbox.pack_start(vbox, True, True, 10)

        if bool(volume.get_mount()):
            mount = volume.get_mount()
            gfile = mount.get_root()
            path = gfile.get_path()
            total_space, used_space, free_space = G.get_mount_space(path)

            self.dirs.add_mount(path)

            levelbar.set_min_value(0)
            levelbar.set_max_value(total_space)
            levelbar.set_value(used_space)

        vbox.pack_start(levelbar, True, True, 0)
        hbox.pack_start(button_close, False, False, 10)

        row = Gtk.ListBoxRow()
        row._path = path
        row.add(hbox)

        data = {}
        data['row'] = row
        data['total-space'] = total_space
        data['used-space'] = used_space
        data['name'] = name
        data['volume'] = volume
        data['mount'] = volume.get_mount()
        data['mounted'] = bool(volume.get_mount())
        data['path'] = path
        data['levelbar'] = levelbar
        data['button-close'] = button_close
        data['hbox'] = hbox
        row.data = data

        button_close.connect('button-release-event', self.eject_mount, data)

        self.rows[path] = row
        self.paths[row] = path

        self.view.add(row)
        row.show_all()

        if not bool(volume.get_mount()):
            levelbar.hide()
            button_close.hide()

    def unmount_done_cb(self):
        pass

    def eject_mount(self, button, event, data):
        # FIXME: This generates core

        if event.button != 1:
            return

        loop = GObject.MainLoop()
        cancellable = Gio.Cancellable()
        data['volume'].eject(0, cancellable, None, self.unmount_done_cb)

    def remove_mount(self, volume_monitor=None, device=None, path=None):
        if device and not path:
            gfile = device.get_default_location()
            path = gfile.get_path()
            self.dirs.remove_mount(path)

        if not path:
            return

        for row, _path in self.paths.items():
            if not _path:
                continue

            if G.clear_path(path) == G.clear_path(_path):
                self.view.remove(row)
                break

        if G.clear_path(self.folder) == G.clear_path(path):
            self.emit('item-selected', G.get_parent_directory(path))

    def __button_press_event_cb(self, listbox, event):
        if event.button == 3:
            row = self.view.get_row_at_y(event.y)
            if not row:
                return

            self._emit = False
            self.view.select_row(row)
            self.make_menu(row)
            self.menu.popup(None, None, None, None, event.button, event.time)
            return True

    def __reselect_row(self, menu):
        self._emit = False
        for row, path in self.paths.items():
            if path == self.folder:
                self.view.select_row(row)
                return


class Notebook(Gtk.Notebook):

    __gsignals__ = {
        'new-page': (GObject.SIGNAL_RUN_FIRST, None, [str]),
        'remove-page': (GObject.SIGNAL_RUN_FIRST, None, [object]),
        'reconnect-all-views': (GObject.SIGNAL_RUN_FIRST, None, []),
        }

    def __init__(self):
        Gtk.Notebook.__init__(self)

        self.mode = G.MODE_ICONS

        button_add = Gtk.ToolButton.new_from_stock(Gtk.STOCK_ADD)
        button_add.connect('clicked', self.__new_page_without_path)

        self.set_scrollable(True)
        self.set_show_tabs(False)
        self.set_action_widget(button_add, Gtk.PackType.END)
        button_add.show_all()

    def set_view_mode(self, mode):
        if mode == self.mode:
            return

        self.mode = mode
        folders = []
        idx = self.get_current_page()

        for view in self.get_children():
            folders.append(view.folder)

        while self.get_children():
            self.remove(self.get_children()[0])

        for folder in folders:
            self.create_page_from_path(folder)

        self.set_current_page(idx)
        self.emit('reconnect-all-views')

    def create_page_from_path(self, path):
        eventbox = Gtk.EventBox()
        hbox = Gtk.HBox()
        label = Gtk.Label(G.Dirs()[path])
        button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_CLOSE)
        if self.mode == G.MODE_ICONS:
            view = IconView(path)

        elif self.mode == G.MODE_LIST:
            view = ListView(path)

        button.connect('clicked', self.__close_page, view)

        hbox.pack_start(label, False, False, 10)
        hbox.pack_end(button, False, False, 0)
        eventbox.add(hbox)
        self.append_page(view, eventbox)
        eventbox.show_all()
        self.show_all()

        eventbox.connect('scroll-event', self.__scroll_event_cb)

        self.set_show_tabs(len(self.get_children()) > 1)
        self.set_current_page(self.get_n_pages() - 1)

        return view

    def update_tab_labels(self):
        for view in self.get_children():
            eventbox = self.get_tab_label(view)
            hbox = eventbox.get_children()[0]
            label = hbox.get_children()[0]
            label.set_label(G.Dirs()[view.folder])

    def __new_page_without_path(self, *args):
        self.emit('new-page', '')

    def __close_page(self, button, view):
        self.emit('remove-page', view)

    def __scroll_event_cb(self, widget, event):
        if event.direction == Gdk.ScrollDirection.UP:
            if self.get_current_page() > 0:
                self.prev_page()

        elif event.direction == Gdk.ScrollDirection.DOWN:
            if self.get_current_page() < len(self.get_children()):
                self.next_page()


class PlaceBox(Gtk.HBox):

    __gsignals__ = {
        'go-back': (GObject.SIGNAL_RUN_FIRST, None, []),
        'go-forward': (GObject.SIGNAL_RUN_FIRST, None, []),
        'go-up': (GObject.SIGNAL_RUN_FIRST, None, []),
        'change-directory': (GObject.SIGNAL_RUN_FIRST, None, [str]),
        'change-view-mode': (GObject.SIGNAL_RUN_FIRST, None, [int]),
        }

    def __init__(self):
        Gtk.HBox.__init__(self)

        self.vbox = Gtk.VBox()
        self.hbox = Gtk.HBox()
        self.show_buttons = False
        self.buttons = []
        self.dirs = G.Dirs()
        self.folder = G.HOME_DIR

        # HACK: Using more boxes, gtk errors are avoided.
        self.vbox.set_margin_top(5)
        self.vbox.set_margin_bottom(5)
        self.hbox.set_margin_right(10)
        self.hbox.set_margin_left(10)

        hbox = Gtk.HBox()
        Gtk.StyleContext.add_class(hbox.get_style_context(), 'linked')
        self.hbox.pack_start(hbox, False, False, 0)

        self.button_left = Gtk.Button()
        arrow = Gtk.Arrow(Gtk.ArrowType.LEFT, Gtk.ShadowType.NONE)
        arrow.set_size_request(28, 28)
        self.button_left.connect('clicked', self.__go, 'go-back')
        self.button_left.add(arrow)
        hbox.pack_start(self.button_left, False, False, 0)

        self.button_right = Gtk.Button()
        arrow = Gtk.Arrow(Gtk.ArrowType.RIGHT, Gtk.ShadowType.NONE)
        arrow.set_size_request(28, 28)
        self.button_right.connect('clicked', self.__go, 'go-forward')
        self.button_right.add(arrow)
        hbox.pack_start(self.button_right, False, False, 0)

        self.button_up = Gtk.Button()
        arrow = Gtk.Arrow(Gtk.ArrowType.UP, Gtk.ShadowType.NONE)
        arrow.set_size_request(28, 28)
        self.button_up.connect('clicked', self.__go, 'go-up')
        self.button_up.add(arrow)
        hbox.pack_start(self.button_up, False, False, 0)

        self.buttonbox = Gtk.HBox()
        Gtk.StyleContext.add_class(
            self.buttonbox.get_style_context(), 'linked')
        self.hbox.pack_start(self.buttonbox, True, True, 10)

        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text('Select a directory')
        self.entry.connect('activate', self.__change_directory)
        self.hbox.pack_start(self.entry, True, True, 10)

        hbox = Gtk.HBox()
        Gtk.StyleContext.add_class(hbox.get_style_context(), 'linked')
        self.hbox.pack_start(hbox, False, False, 10)

        button_icons = Gtk.RadioToolButton(icon_name='view-grid-symbolic')
        button_icons.connect('toggled', self.change_view_mode, G.MODE_ICONS)
        hbox.pack_start(button_icons, False, False, 0)

        button_list = Gtk.RadioToolButton(
            group=button_icons, icon_name='view-list-symbolic')
        button_list.connect('toggled', self.change_view_mode, G.MODE_LIST)
        hbox.pack_start(button_list, False, False, 0)

        button_close = Gtk.Button()
        image = Gtk.Image.new_from_icon_name(
            'window-close', Gtk.IconSize.BUTTON)
        button_close.set_relief(Gtk.ReliefStyle.NONE)
        button_close.add(image)
        button_close.connect('clicked', self.__close)
        self.hbox.pack_end(button_close, False, False, 0)

        self.connect('realize', self.__realize_cb)
        self.set_folder(G.HOME_DIR)

        self.vbox.add(self.hbox)
        self.add(self.vbox)

    def set_folder(self, folder):
        # FIXME: Hay que agregar botones de desplazamientos, de lo contrario
        #        cuando haya que abrir una dirección larga, se agrandara la
        #        ventana

        folder = G.clear_path(folder)
        self.folder = G.clear_path(self.folder)
        self.entry.set_text(folder)
        self.entry.set_position(-1)

        if folder != '/' and folder.endswith('/'):
            folder = folder[:-1]

        if self.folder != '/' and self.folder.endswith('/'):
            self.folder = self.folder[:-1]

        home = G.HOME_DIR[:-1]
        startswith = self.folder.startswith(folder)
        has_children = bool(self.buttonbox.get_children())
        if has_children:
            no_home = self.folder.startswith(folder) and self.folder != '/home'
            button = self.buttonbox.get_children()[0]
            label = button.get_children()[0]
            other_label = not label.get_label() == G.HOME_NAME
            no_home_or_other_label = no_home or other_label

            if startswith and has_children and no_home_or_other_label:
                self.folder = folder
                return

        self.folder = folder

        del self.buttons
        self.buttons = []

        if not folder.startswith(home):
            self.buttons.append('/')

        while self.buttonbox.get_children():
            self.buttonbox.remove(self.buttonbox.get_children()[0])

        if folder.startswith(home):
            self.buttons.append(G.HOME_NAME)
            folder = folder[len(home):]
            folder = folder[1:] if folder.startswith('/') else folder

        for x in folder.split('/'):
            if x:
                self.buttons.append(x)

        path = ''
        for x in self.buttons:
            if x == G.HOME_NAME:
                path += home + '/'

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
            self.buttonbox.pack_start(button, False, False, 0)

        if self.show_buttons:
            self.buttonbox.show_all()

        else:
            self.entry.show()

    def change_mode(self):
        self.show_buttons = not self.show_buttons

        if self.show_buttons:
            self.entry.hide()
            self.buttonbox.show_all()

        else:
            self.buttonbox.hide()
            self.entry.show()
            GObject.idle_add(self.entry.grab_focus)

    def change_view_mode(self, button, mode):
        if button.get_active():
            self.emit('change-view-mode', mode)

    def __realize_cb(self, widget):
        self.entry.hide()

    def __go(self, widget, direction):
        self.emit(direction)

    def __change_directory(self, entry):
        self.emit('change-directory', entry.get_text())

    def __button_clicked(self, button):
        self.emit('change-directory', button.path)

    def __close(self, button):
        self.get_toplevel().destroy()


class StatusBar(Gtk.HBox):

    __gsignals__ = {
        'icon-size-changed': (GObject.SIGNAL_RUN_FIRST, None, [int])
        }

    def __init__(self):
        Gtk.HBox.__init__(self)

        self.icon_size = G.DEFAULT_ICON_SIZE / 8
        self.set_margin_left(10)

        self.label = Gtk.Label(G.HOME_DIR)
        self.label.set_selectable(True)
        self.label.modify_font(Pango.FontDescription('12'))
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        self.pack_start(self.label, False, False, 0)

        self.scale = Gtk.HScale.new_with_range(1, 8, 1)
        self.scale.set_draw_value(False)
        self.scale.set_value(3)
        self.scale.set_size_request(200, -1)
        self.scale.connect('value-changed', self.__value_changed)
        self.pack_end(self.scale, False, False, 10)

    def update_label(self, selected=[], folder=''):
        label = ''
        if len(selected) == 0:
            label += folder

        elif len(selected) == 1:
            label += selected[0]

        label += ' ' + G.get_size(selected)
        if not label.replace(' ', ''):
            label = folder

        self.label.set_label(label)

    def aument(self):
        value = self.scale.get_value()
        value += 1
        if value > 8:
            value = 8

        self.scale.set_value(value)

    def disminuit(self):
        value = self.scale.get_value()
        value -= 1
        if value < 1:
            value = 1

        self.scale.set_value(value)

    def __value_changed(self, widget):
        value = int(widget.get_value())
        if value != self.icon_size:
            self.icon_size = value
            self.emit('icon-size-changed', value * 16)


class PropertiesWindow(Gtk.Dialog):

    __gsignals__ = {
        'rename-file': (GObject.SIGNAL_RUN_FIRST, None, [str, str]),
        }

    def __init__(self, paths):
        Gtk.Dialog.__init__(self)

        self.dirs = G.Dirs()
        self.info_number = 0
        self.old_path = paths[0]
        readable, writable = G.get_access(paths[0])

        hbox = Gtk.HBox()
        self.vbox.pack_start(hbox, False, False, 0)

        pixbuf = G.get_pixbuf_from_path(paths[0], size=64)
        self.icon = Gtk.Image.new_from_pixbuf(pixbuf)
        hbox.pack_start(self.icon, False, False, 5)

        self.entry = Gtk.Entry()
        self.entry.modify_font(Pango.FontDescription('20'))
        self.entry.set_text(self.dirs[paths[0]])
        self.entry.set_sensitive(writable)

        self.entry.connect('activate', self.__rename_file)
        if len(paths) == 1:
            hbox.pack_start(self.entry, True, True, 10)

        self.label = Gtk.Label('%d elements selecteds' % len(paths))
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        self.label.modify_font(Pango.FontDescription('20'))

        if len(paths) > 1:
            hbox.pack_start(self.label, True, True, 10)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(
            Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(1000)

        self.grid_info = Gtk.Grid()
        self.grid_info.set_column_spacing(10)
        self.stack.add_titled(self.grid_info, 'general', _('General'))

        self.make_info(_('Size:'), G.get_size(paths).capitalize())
        if len(paths) == 1:
            self.make_info(_('Mime type:'), G.get_type(paths[0]))
            self.make_info(_('Created:'), G.get_created_time(paths[0]))
            self.make_info(_('Last modified:'), G.get_modified_time(paths[0]))
            self.make_info(_('Ubication:'), paths[0])

        elif len(paths) > 1:
            self.make_info(_('Ubication:'), G.get_parent_directory(paths[0]))

        if len(paths) == 1 and os.path.isfile(paths[0]):
            label = Gtk.Label(('Open with:'))
            label.set_selectable(True)
            label.modify_font(Pango.FontDescription('Bold'))
            self.grid_info.attach(label, 0, self.info_number, 1, 1)

            button = Gtk.AppChooserButton(content_type=G.get_type(paths[0]))
            button.set_show_dialog_item(True)
            self.grid_info.attach(button, 1, self.info_number, 1, 1)

        self.vbox_permissions = Gtk.VBox()
        self.make_permissions()
        self.stack.add_titled(
            self.vbox_permissions, 'permissions', _('Permissions'))

        self.stack_switcher = Gtk.StackSwitcher()
        self.stack_switcher.set_stack(self.stack)
        self.stack_switcher.set_hexpand(True)
        self.stack_switcher.set_halign(Gtk.Align.CENTER)
        self.vbox.pack_start(self.stack_switcher, True, True, 10)
        self.vbox.pack_start(self.stack, True, True, 0)

        self.set_title(_('Properties'))
        self.vbox.set_margin_left(20)
        self.vbox.set_margin_right(20)

        self.grid_info.show_all()
        self.vbox_permissions.show_all()
        self.show_all()

    def make_info(self, title, info):
        label = Gtk.Label(title)
        label.set_selectable(True)
        label.modify_font(Pango.FontDescription('bold'))
        label.set_justify(Gtk.Justification.LEFT)
        self.grid_info.attach(label, 0, self.info_number, 1, 1)

        label_info = Gtk.Label(info)
        label_info.set_selectable(True)
        label_info.set_justify(Gtk.Justification.FILL)
        label_info.set_ellipsize(Pango.EllipsizeMode.END)
        self.grid_info.attach(label_info, 1, self.info_number, 1, 1)

        self.info_number += 1

    def make_permissions(self):
        hbox = Gtk.HBox()
        self.vbox_permissions.add(hbox)

        button1 = Gtk.Button('read')
        button2 = Gtk.Button('write')
        button3 = Gtk.Button('execute')

        hbox.add(button1)
        hbox.add(button2)
        hbox.add(button3)

        hbox = Gtk.HBox()
        self.vbox_permissions.add(hbox)

        button1 = Gtk.Button('read')
        button2 = Gtk.Button('write')
        button3 = Gtk.Button('execute')

        hbox.add(button1)
        hbox.add(button2)
        hbox.add(button3)

        hbox = Gtk.HBox()
        self.vbox_permissions.add(hbox)

        button1 = Gtk.Button('read')
        button2 = Gtk.Button('write')
        button3 = Gtk.Button('execute')

        hbox.add(button1)
        hbox.add(button2)
        hbox.add(button3)

    def __rename_file(self, entry):
        self.emit('rename-file', self.old_path, entry.get_text())


class ProgressWindow(Gtk.Window):

    def __init__(self, ccpmanager):
        Gtk.Window.__init__(self)

        self.operations = {}
        self.box = Gtk.ListBox()
        self.box.set_selection_mode(Gtk.SelectionMode.NONE)

        self.manager = ccpmanager
        self.manager.connect('progress-changed', self.__progress_changed)
        self.manager.connect('end', self.__operation_ended)

        scrolled = Gtk.ScrolledWindow()
        scrolled.add(self.box)
        self.add(scrolled)

    def add_operation(self, time_id):
        min_value = 0
        max_value = self.maganer[time_id]['total-size']
        value = self.manager[time_id]['progress']

        row = Gtk.ListBoxRow()
        box = Gtk.HBox()
        hbox.set_spacing(5)

        levelbar = Gtk.LevelBar()
        levelbar.set_min_value(min_value)
        levelbar.set_max_value(max_value)
        levelbar.set_value(value)

        button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_CANCEL)

        hbox.pack_start(levelbar, True, True, 0)
        hbox.pack_start(button, False, False, 0)
        row.add(hbox)

        self.listbox.add(row)
        self.listbox.show_all()

        self.operations[time_id] = {'levelbar': levelbar,
                                    'button': button,
                                    'row': row}

    def __progress_changed(self, manager, time_id):
        progress = self.manager[time_id]['progress']
        self.operations[time_id]['levelbar'].set_value(progress)

    def __operation_ended(self, manager, time_id):
        self.box.remove(self.operations[time_id]['row'])
