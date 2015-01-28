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
        'show-properties': (GObject.SIGNAL_RUN_FIRST, None, [object]),
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
        self.menu = None
        self.sort = G.SORT_BY_NAME
        self.reverse = False

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
        path = view.get_path_at_pos(int(event.x), int(event.y))
        selection = view.get_selected_items()

        if event.button == 3:
            if path:
                treeiter = self.model.get_iter(path)
                directory = self.get_path_from_treeiter(treeiter)
                if path not in selection:
                    self.view.unselect_all()

                self.view.select_path(path)

            else:
                directory = self.folder

            self.make_menu(directory)
            self.menu.popup(None, None, None, None, event.button, event.time)
            return True

        if not path:
            return

        treeiter = self.model.get_iter(path)
        directory = self.get_path_from_treeiter(treeiter)

        if event.button == 2:
            self.emit('new-page', directory)

        if event.button == 1 and event.type.value_name == 'GDK_2BUTTON_PRESS':
            self.emit('item-selected', directory)

    def make_menu(self, path):
        writable, readable = G.get_access(path)
        selection = self.view.get_selected_items()
        self.menu = Gtk.Menu()

        if path != self.folder:
            item = Gtk.MenuItem(_('Open'))
            item.connect('activate', self.__open_from_menu, path)
            item.set_sensitive(readable)
            self.menu.append(item)

            if os.path.isdir(path):
                item = Gtk.MenuItem(_('Open in new tab'))
                item.connect('activate', self.__open_from_menu, None, True)
                self.menu.append(item)

            self.menu.append(Gtk.SeparatorMenuItem())

        item = Gtk.MenuItem(_('Create a folder'))
        self.menu.append(item)

        self.menu.append(Gtk.SeparatorMenuItem())

        item = Gtk.MenuItem(_('Sort items'))
        menu = Gtk.Menu()
        item.set_submenu(menu)
        self.menu.append(item)

        self.menu.append(Gtk.SeparatorMenuItem())

        item_name = Gtk.RadioMenuItem(_('By name'))
        item_name.set_active(self.sort == G.SORT_BY_NAME)
        item_name.connect('activate', self.__sort_changed, G.SORT_BY_NAME)
        menu.append(item_name)

        item_size = Gtk.RadioMenuItem(_('By size'), group=item_name)
        item_size.set_active(self.sort == G.SORT_BY_SIZE)
        item_size.connect('activate', self.__sort_changed, G.SORT_BY_SIZE)
        menu.append(item_size)

        menu.append(Gtk.SeparatorMenuItem())

        item = Gtk.CheckMenuItem(_('Reverse'))
        item.set_active(self.reverse)
        item.connect('activate', self.__reverse_changed)
        menu.append(item)

        item = Gtk.MenuItem(_('Properties'))
        item.connect('activate', self.__show_properties)
        self.menu.append(item)

        self.menu.show_all()

    def __open_from_menu(self, item, path=None, new_page=False):
        selected = len(self.view.get_selected_items())
        paths = []

        for path in self.view.get_selected_items():
            treeiter = self.model.get_iter(path)
            paths.append(self.get_path_from_treeiter(treeiter))

        if not new_page:
            self.emit('item-selected', paths[0])
            for path in paths[1:]:
                self.emit('new-page', path)

        elif new_page:
            self.emit('multiple-selection', paths)

    def __sort_changed(self, item, sort):
        self.sort = sort

    def __reverse_changed(self, item):
        self.reverse = not self.reverse

    def __show_properties(self, item):
        selected = len(self.view.get_selected_items())
        paths = []

        for path in self.view.get_selected_items():
            treeiter = self.model.get_iter(path)
            paths.append(self.get_path_from_treeiter(treeiter))

        self.emit('show-properties', paths)

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


class InfoBar(Gtk.InfoBar):

    def __init__(self):
        Gtk.InfoBar.__init__(self)

        self.set_show_close_button(True)
        self.set_message_type(Gtk.MessageType.ERROR)

        self.connect('response', self.__response)

        hbox = self.get_content_area()
        vbox = Gtk.VBox()
        hbox.add(vbox)

        self.title = Gtk.Label()
        self.title.modify_font(Pango.FontDescription('Bold 12'))
        vbox.pack_start(self.title, False, False, 2)

        self.msg = Gtk.Label()
        vbox.pack_start(self.msg, False, False, 0)

    def __response(self, widget, response):
        self.hide()

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


class LateralView(Gtk.ScrolledWindow):

    __gsignals__ = {
        'item-selected': (GObject.SIGNAL_RUN_FIRST, None, [str])
        }

    def __init__(self):
        Gtk.ScrolledWindow.__init__(self)

        self.rows = {}
        self.volume_monitor = Gio.VolumeMonitor.get()
        self.view = Gtk.ListBox()
        #   view structur:
        #   GtkVBox:
        #       GtkHBox: add property path
        #           GtkImage, GtkLabel, GtkButton(For eject a mount)
        #   GtkLevelBar(Show used space)

        self.dirs = G.Dirs()
        self.folder = None

        self.view.set_selection_mode(Gtk.SelectionMode.SINGLE)

        #self.volume_monitor.connect('mount-added', self.add_mount)
        #self.volume_monitor.connect('mount-removed', self.remove_mount)

        self.make_items()
        self.select_item(G.HOME_DIR)
        self.set_size_request(200, -1)

        self.view.connect('row-selected', self.__selection_changed)
        self.add(self.view)

    def __selection_changed(self, listview, row):
        if row and G.clear_path(row.path) == self.folder:
            return

        for path, _row in self.rows.items():
            if _row == row:
                self.folder = G.clear_path(row.path)
                self.emit('item-selected', self.folder)
                break

    def make_items(self):
        for x in self.dirs:
            self.add_home_folder(x)

    def add_home_folder(self, path):
        name = self.dirs[path]
        pixbuf = self.dirs.get_pixbuf_symbolic(path)
        image = Gtk.Image.new_from_pixbuf(pixbuf)

        row = Gtk.ListBoxRow()
        row.path = path
        vbox = Gtk.VBox()
        hbox = Gtk.HBox()
        label = Gtk.Label(name)
        umount_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_REMOVE)
        levelbar = Gtk.LevelBar()

        hbox.pack_start(image, False, False, 10)
        hbox.pack_start(label, False, False, 5)
        #hbox.pack_start(umount_button, False, False, 0)
        vbox.pack_start(hbox, False, False, 2)
        #vbox.pack_start(levelbar, False, False, 0)
        row.add(vbox)
        self.view.add(row)

        self.rows[path] = row
        # if is a mount: add levelbar and umount_button

    def select_item(self, path):
        path = G.clear_path(path)
        if not self.folder:
            self.folder = G.HOME_DIR

        if self.folder:
            self.folder = G.clear_path(self.folder)

        if not path in self.rows:
            self.view.set_selection_mode(Gtk.SelectionMode.NONE)
            self.view.set_selection_mode(Gtk.SelectionMode.SINGLE)
            # Unselecting all items
            return

        if path == self.folder and self.view.get_selected_row():
            return

        self.view.select_row(self.rows[path])

    def add_mount(self, device):
        if not self.label_mount_added:
            self.label_mount_added = True
            self.append_section(_('Mounts'))

        item = TreeViewMountItem(device, False)
        self.items.append(item)
        self.view.pack_start(item, False, False, 0)

        item.show_all()

    def remove_mount(self, *args):
        print args


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

    def update_label(self, view):
        hbox = self.get_tab_label(view)
        label = hbox.get_children()[0]
        label.set_label(G.Dirs()[view.folder])


class PlaceBox(Gtk.HBox):

    __gsignals__ = {
        'go-back': (GObject.SIGNAL_RUN_FIRST, None, []),
        'go-forward': (GObject.SIGNAL_RUN_FIRST, None, []),
        'go-up': (GObject.SIGNAL_RUN_FIRST, None, []),
        'change-directory': (GObject.SIGNAL_RUN_FIRST, None, [str]),
        }

    def __init__(self):
        Gtk.HBox.__init__(self)

        self.vbox = Gtk.VBox()
        self.hbox = Gtk.HBox()
        self.show_buttons = True
        self.buttons = []
        self.dirs = G.Dirs()
        self.folder = G.HOME_DIR

        # HACK: Using more boxes, gtk errors are avoided.
        self.vbox.set_margin_top(5)
        self.vbox.set_margin_bottom(5)
        self.hbox.set_margin_right(10)
        self.hbox.set_margin_left(10)

        Gtk.StyleContext.add_class(
            self.get_style_context(), 'linked')

        self.button_left = Gtk.Button()
        arrow = Gtk.Arrow(Gtk.ArrowType.LEFT, Gtk.ShadowType.NONE)
        arrow.set_size_request(28, 28)
        self.button_left.connect('clicked', self.__go, 'go-back')
        self.button_left.add(arrow)
        self.hbox.pack_start(self.button_left, False, False, 0)

        self.button_right = Gtk.Button()
        arrow = Gtk.Arrow(Gtk.ArrowType.RIGHT, Gtk.ShadowType.NONE)
        arrow.set_size_request(28, 28)
        self.button_right.connect('clicked', self.__go, 'go-forward')
        self.button_right.add(arrow)
        self.hbox.pack_start(self.button_right, False, False, 0)

        self.button_up = Gtk.Button()
        arrow = Gtk.Arrow(Gtk.ArrowType.UP, Gtk.ShadowType.NONE)
        arrow.set_size_request(28, 28)
        self.button_up.connect('clicked', self.__go, 'go-up')
        self.button_up.add(arrow)
        self.hbox.pack_start(self.button_up, False, False, 0)

        self.buttonbox = Gtk.HBox()
        Gtk.StyleContext.add_class(self.buttonbox.get_style_context(), 'linked')
        self.hbox.pack_start(self.buttonbox, True, True, 10)

        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text('Select a directory')
        self.entry.connect('activate', self.__change_directory)
        #self.hbox.pack_start(self.entry, True, True, 10)

        button_close = Gtk.Button()
        image = Gtk.Image.new_from_icon_name('window-close', Gtk.IconSize.BUTTON)
        button_close.set_relief(Gtk.ReliefStyle.NONE)
        button_close.add(image)
        button_close.connect('clicked', self.__close)
        self.hbox.pack_start(button_close, False, False, 0)

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
                self.buttonbox.pack_start(button, False, False, 0)

        self.show_all()

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
        self.label.modify_font(Pango.FontDescription('12'))
        self.pack_start(self.label, False, False, 0)

        self.scale = Gtk.HScale.new_with_range(1, 8, 1)
        self.scale.set_draw_value(False)
        self.scale.set_value(3)
        self.scale.set_size_request(200, -1)
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


class PropertiesWindow(Gtk.Dialog):

    __gsignals__ = {
        'rename-file': (GObject.SIGNAL_RUN_FIRST, None, [str, str]),
        }

    def __init__(self, paths):
        Gtk.Dialog.__init__(self)

        self.dirs = G.Dirs()
        self.info_number = 0
        self.old_path = paths[0]

        hbox = Gtk.HBox()
        self.vbox.pack_start(hbox, False, False, 0)

        pixbuf = G.get_pixbuf_from_path(paths[0], size=64)
        self.icon = Gtk.Image.new_from_pixbuf(pixbuf)
        hbox.pack_start(self.icon, False, False, 5)

        self.entry = Gtk.Entry()
        self.entry.modify_font(Pango.FontDescription('20'))
        self.entry.set_text(self.dirs[paths[0]])
        self.entry.connect('activate', self.__rename_file)
        if len(paths) == 1:
            hbox.pack_start(self.entry, False, True, 10)

        self.label = Gtk.Label('%d elements\nselecteds' % len(paths))
        self.label.modify_font(Pango.FontDescription('20'))

        if len(paths) > 1:
            hbox.pack_start(self.label, False, True, 10)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(1000)

        self.grid_info = Gtk.Grid()
        self.grid_info.set_column_spacing(10)
        self.stack.add_titled(self.grid_info, 'general', _('General'))

        self.make_info(_('Size:'), G.get_size(paths))
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

        grid_permissions = Gtk.Grid()
        grid_permissions.set_row_homogeneous(True)
        self.stack.add_titled(grid_permissions, 'permissions', _('Permissions'))

        self.stack_switcher = Gtk.StackSwitcher()
        self.stack_switcher.set_stack(self.stack)
        self.stack_switcher.set_hexpand(True)
        self.stack_switcher.set_halign(Gtk.Align.CENTER)
        self.vbox.pack_start(self.stack_switcher, True, True, 10)
        self.vbox.pack_start(self.stack, True, True, 0)

        self.set_resizable(False)
        self.set_title(_('Properties'))
        self.vbox.set_margin_left(20)
        self.vbox.set_margin_right(20)

        self.grid_info.show_all()
        grid_permissions.show_all()
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
        self.grid_info.attach(label_info, 1, self.info_number, 1, 1)

        self.info_number += 1

    def __rename_file(self, entry):
        self.emit('rename-file', self.old_path, entry.get_text())
