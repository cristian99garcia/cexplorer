#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2014, Cristian García <cristian99garcia@gmail.com>
# Copyright (C) 2015, Cristian García <cristian99garcia@gmail.com>
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
import re
import time
import thread
import datetime
import subprocess
import ConfigParser
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import GdkPixbuf


TILDES = {'%C3%81': 'Á',
          '%C3%89': 'É',
          '%C3%8D': 'Í',
          '%C3%93': 'Ó',
          '%C3%9A': 'Ú',
          '%C3%A1': 'á',
          '%C3%A9': 'é',
          '%C3%AD': 'í',
          '%C3%B3': 'ó',
          '%C3%BA': 'ú'}


def clear_path(path):
    path = path.replace('//', '/')
    path = path.replace('//', '/')

    for representation, tilde in TILDES.items():
        path = path.replace(representation, tilde)

    if not path.endswith('/') and os.path.isdir(path):
        path = path + '/'

    if '%20' in path:
        path = path.replace('%20', ' ')

    return path


DEFAULT_ICON_SIZE = 48
DEFAULT_ITEM_ICON_SIZE = 16

ERROR_NOT_READABLE = 0
ERROR_NOT_UNWRITABLE = 1
ERROR_ALREADY_EXISTS = 2
ERROR_INVALID_NAME = 3
ERROR_NOT_EXISTS = 4

TITLE_ERROR_UNREADABLE = _('Could not be displayed here.')
TITLE_ERROR_UNWRITABLE = _('Could not be set.')
TITLE_ERROR_ALREADY_EXISTS = _('Could not rename.')
TITLE_ERROR_INVALID_NAME = _('Could not rename.')
TITLE_ERROR_NOT_EXISTS = _('Could not be displayed here.')

MSG_UNREADABLE = _(
    'You do not have sufficient permissions to view the content of "@".')
MSG_UNWRITABLE = _('You do not have sufficient permissions to edit "@".')
MSG_ALREADY_EXISTS = _('You can not rename to "@", because already exists.')
MSG_INVALID_NAME = _('"@"" is a invalid name for a file.')
MSG_NOT_EXISTS = _('"@" can not be displayed because it does not exist.')

SORT_BY_NAME = 0
SORT_BY_SIZE = 1

MODE_ICONS = 0
MODE_LIST = 1

CUT = 'mv'
COPY = 'cp'

ACTIVATION_WITH_A_CLICK = 'GDK_BUTTON_PRESS'
ACTIVATION_WITH_TWO_CLICKS = 'GDK_2BUTTON_PRESS'

HOME_DIR = clear_path(os.path.expanduser('~'))
HOME_NAME = _('Personal folder')
DESKTOP_DIR = clear_path(
    GLib.get_user_special_dir(GLib.USER_DIRECTORY_DESKTOP))
DESKTOP_NAME = _('Desktop')
DOCUMENTS_DIR = clear_path(
    GLib.get_user_special_dir(GLib.USER_DIRECTORY_DOCUMENTS))
DOCUMENTS_NAME = _('Documents')
DOWNLOADS_DIR = clear_path(
    GLib.get_user_special_dir(GLib.USER_DIRECTORY_DOWNLOAD))
DOWNLOADS_NAME = _('Donwloads')
MUSIC_DIR = clear_path(GLib.get_user_special_dir(GLib.USER_DIRECTORY_MUSIC))
MUSIC_NAME = _('Music')
PICTURES_DIR = clear_path(
    GLib.get_user_special_dir(GLib.USER_DIRECTORY_PICTURES))
PICTURES_NAME = _('Pictures')
VIDEOS_DIR = clear_path(GLib.get_user_special_dir(GLib.USER_DIRECTORY_VIDEOS))
VIDEOS_NAME = _('Videos')
SYSTEM_DIR = '/'
SYSTEM_NAME = _('Equipment')
TRASH_DIR = os.path.expanduser('~/.local/share/Trash/files/')
TRASH_NAME = _('Trash')
TRASH_INFO_DIR = os.path.expanduser('~/.local/share/Trash/info/')


KEYS = {65288: 'Backspace',
        65293: 'Enter',
        65507: 'Ctrl',
        65513: 'Alt',
        65505: 'Mayus',
        65307: 'Scape',
        65361: 'Left',
        65362: 'Up',
        65363: 'Right',
        65364: 'Down',
        43: '+',
        45: '-'}

SPECIAL_KEYS = [KEYS[x] for x in KEYS.keys()]

for x in range(65, 91) + range(97, 123):
    KEYS[x] = chr(x)


class Dirs(object):
    """
    A Singleton class, is possible make a only instance of this class:

    >>> dirs1 = Dirs()
    >>> dirs2 = Dirs()
    >>> print dirs1 == dirs2
    ... True

    >>> dirs1.hello = 'Hello'
    >>> print dirs2.hello
    ... Hello
    """

    _instance = None

    def __init__(self):

        self.dirs = [HOME_DIR,
                     DESKTOP_DIR,
                     DOCUMENTS_DIR,
                     DOWNLOADS_DIR,
                     MUSIC_DIR,
                     PICTURES_DIR,
                     VIDEOS_DIR,
                     TRASH_DIR,
                     SYSTEM_DIR]

        self.names = [HOME_NAME,
                      DESKTOP_NAME,
                      DOCUMENTS_NAME,
                      DOWNLOADS_NAME,
                      MUSIC_NAME,
                      PICTURES_NAME,
                      VIDEOS_NAME,
                      TRASH_NAME,
                      SYSTEM_NAME]

        self.specials_dirs = {HOME_DIR: HOME_NAME,
                              TRASH_DIR: TRASH_NAME,
                              SYSTEM_DIR: SYSTEM_NAME}

        self.symbolic_icons = {HOME_DIR: 'go-home-symbolic',
                               DESKTOP_DIR: 'user-desktop-symbolic',
                               DOCUMENTS_DIR: 'folder-documents-symbolic',
                               DOWNLOADS_DIR: 'folder-download-symbolic',
                               MUSIC_DIR: 'folder-music-symbolic',
                               PICTURES_DIR: 'folder-pictures-symbolic',
                               VIDEOS_DIR: 'folder-videos-symbolic',
                               TRASH_DIR: 'user-trash-symbolic',
                               SYSTEM_DIR: 'drive-harddisk-system-symbolic'}

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Dirs, cls).__new__(cls, *args, **kwargs)

        return cls._instance

    def __getitem__(self, path):
        """
        >>> dirs = Dirs()
        >>> print dirs[HOME_DIR]  # Get directory name a special directory
        ... 'Personal folder'

        >>> print dirs[SYSTEM_DIR]
        ... 'Equipment'

        >>> print dirs['/home/cristian/']  # Get name from another directory
        ... 'cristian'
        """
        if type(path) == int:
            return self.dirs[path]

        elif type(path) == slice:
            return self.dirs[path.start:path.stop:path.step]

        elif type(path) == str:
            path = clear_path(path)

            if path in self.specials_dirs:
                return self.specials_dirs[path]

            else:
                if path.endswith('.desktop'):
                    cfg = ConfigParser.ConfigParser()
                    cfg.read([path])

                    if cfg.has_option('Desktop Entry', 'Name'):
                        return cfg.get('Desktop Entry', 'Name')

                return get_name(path)

    def __setitem__(self, name, value):
        if not name in self[name]:
            if '/' in name:
                self.dirs.append(name)
                self.names.append(value)

            else:
                self.names.append(name)
                self.dirs.append(value)

        else:
            if name in self.dirs:
                self.names[self.dirs.index(name)] = value

            elif name in self.names:
                self.dirs[self.names.index(name)] = value

    def __iter__(self):
        for x in self.dirs:
            yield x

    def __contains__(self, name):
        if name in self.dirs + self.names:
            return True

        if clear_path(name) in self.mounts:
            return True

        for x in self.dirs:
            if not x.endswith('/'):
                x += '/'

            if not name.endswith('/'):
                name += '/'

            if name == x:
                return True

        return False

    def get_pixbuf_symbolic(self, path):
        screen = Gdk.Screen.get_default()
        icon_theme = Gtk.IconTheme.get_for_screen(screen)
        return icon_theme.load_icon(
            self.symbolic_icons[path], DEFAULT_ITEM_ICON_SIZE, 0)

    def add_mount(self, path):
        if not clear_path(path) in self.mounts:
            self.mounts.append(clear_path(path))

    def remove_mount(self, path):
        if clear_path(path) in self.mounts:
            self.mounts.remove(clear_path(path))


class ScanFolder(GObject.GObject):

    __gsignals__ = {
        'files-changed': (GObject.SIGNAL_RUN_FIRST, None, [object]),
        'realized-searching': (GObject.SIGNAL_RUN_FIRST, None, []),
        }

    def __init__(self, folder, timeout=500):

        GObject.GObject.__init__(self)

        self.folder = folder
        self.files = []
        self.show_hidden_files = False
        self.can_scan = True
        self.mounts = {}

        GObject.timeout_add(timeout, self.scan)

    def scan(self, force=False):
        if not self.can_scan:
            return True

        files = []
        directories = []

        if (self.files != self.get_files()) or force:
            self.files = self.get_files()

            self.emit('files-changed', self.files)

        self.emit('realized-searching')

        return True

    def set_folder(self, folder):
        self.folder = folder
        GObject.idle_add(self.scan)

    def get_files(self):
        directories = []
        files = []
        if os.path.isdir(self.folder):
            _files = os.listdir(self.folder)

        else:
            self.folder = get_parent_directory(self.folder)
            return

        for name in _files:
            filename = clear_path(os.path.join(self.folder, name))

            if (not name.startswith('.') and not name.endswith('~')) or \
                    self.show_hidden_files:

                if os.path.isdir(filename):
                    directories.append(filename)

                elif os.path.isfile(filename):
                    files.append(filename)

        directories = natural_sort(directories)
        files = natural_sort(files)

        return directories + files

    def set_show_hidden_files(self, if_show):
        if type(if_show) != bool:
            raise TypeError(_('The parameter must to be a bool'))

        self.show_hidden_files = if_show
        GObject.idle_add(self.scan)


class CCPManager(GObject.GObject):
    # Cut, Copy and Paste

    __gsignals__ = {
        'error': (GObject.SIGNAL_RUN_FIRST, None, [int]),
        'warning': (GObject.SIGNAL_RUN_FIRST, None, [str]),
        'start': (GObject.SIGNAL_RUN_FIRST, None, [float]),
        'progress-changed': (GObject.SIGNAL_RUN_FIRST, None, [float]),
        'end': (GObject.SIGNAL_RUN_FIRST, None, [float]),
        }

    def __init__(self):
        GObject.GObject.__init__(self)

        self.operations = {}
        # Operations structur:
        #    {time_id: {'action': int,
        #               'files': list,
        #               'destination': str,
        #               'active': bool,
        #               'total-size': int,
        #               'progress': int}}

    def __start_new_operation(self, time_id):
        operation = self.operations[time_id]

        def start():
            self.emit('start', time_id)

            actual = 0
            loop_time = 1
            action = operation['action']
            files = operation['files']
            operation['total-size'] = get_total_size(files)
            operation['progress'] = 0

            while operation['active']:
                path = files[actual]
                actual += 1
                readable, writable = get_access(path)
                if (not readable and action == COPY) or \
                    (not writable and action == CUT):

                    #self.emit('error', 1)
                    #return
                    continue

                if operation['action'] == COPY:
                    command = 'cp -r %s' % path

                elif operation['action'] == CUT:
                    command = 'mv -r %s' % path

                os.system(command)

                if actual == len(files):
                    operation[active] = False

                if actual % 2:
                    operacion['progress'] = get_total_size(operacion['destination'])
                    self.emit('progress-changed', time_id)

            self.emit('end', time_id)

        readable, writable = get_access(operation[2])
        if not writable:
            #self.emit('error', 0)
            return

        thread.start_new_thread(start, ())

    def add_action(self, action, files, destination, time_id):
        self.operations[time_id] = {'action': action,
                                    'files': files,
                                    'destination': destination,
                                    'active': True}

        GObject.idle_add(self.__start_new_operation, time_id)

    def cancel_operation(self, time_id):
        self.operations[time_id]['active'] = False

    def __getitem__(self, time_id):
        return self.operations[time_id]


class TrashManager(GObject.GObject):

    __gsignals__ = {
        'files-changed': (GObject.SIGNAL_RUN_FIRST, None, [object]),
        'error': (GObject.SIGNAL_RUN_FIRST, None, [int]),
        }

    def __init__(self):
        GObject.GObject.__init__(self)

        self.files = {}
        self.files_path = TRASH_DIR
        self.info_path = TRASH_INFO_DIR
        self.can_scan = True
        self.timeout = None

    def start(self, timeout=500):
        self.stop()
        GObject.idle_add(self.scan)
        self.timeout = GObject.timeout_add(timeout, self.scan)

    def stop(self):
        if self.timeout is None:
            return

        GObject.source_remove(self.timeout)
        self.files = {}
        self.timeout = None

    def move_to(self, paths):
        readable1, writable1 = get_access(self.files_path)
        readable2, writable2 = get_access(self.info_path)

        if not writable1 or not writable2:
            #self.emit('error')
            return

        for path in paths:
            readable, writable = get_access(path)
            name = get_name(path)
            new_path = os.path.join(self.files_path, name)
            info_path = os.path.join(self.info_path, name) + '.trashinfo'

            if not writable:
                #self.emit('error')
                continue

            os.rename(path, new_path)

            info_file = open(info_path, 'w')
            cfg = ConfigParser.ConfigParser()

            cfg.add_section('Trash Info')
            cfg.set('Trash Info', 'Path', path)
            cfg.set('Trash Info', 'DeletionDate', get_current_time())
            cfg.write(info_file)
            info_file.close()

    def remove_paths(self, paths):
        for path in paths:
            name = get_name(path)
            info_path = os.path.join(self.info_path, name) + '.trashinfo'
            if os.path.isdir(path):
                os.removedirs(path)

            elif os.path.isfile(path):
                os.remove(path)

            os.remove(info_path)

    def clear(self):
        files = [os.path.join(self.files_path, x) \
                for x in os.listdir(self.files_path)]

        self.purge(files)

    def restore(self, paths):
        for path in paths:
            name = get_name(path)
            info_path = os.path.join(self.info_path, name) + '.trashinfo'
            cfg = ConfigParser.ConfigParser()
            cfg.read([info_path])
            if cfg.has_section('Trash Info'):
                if cfg.has_option('Trash Info', 'Path'):
                    save_path = cfg.get('Trash Info', 'Path')

                else:
                    # self.emit('error')
                    continue

            else:
                # self.emit('error')
                continue

            parent_directory = get_parent_directory(save_path)
            readable, writable = get_access(parent_directory)
            if not writable:
                # self.emit('error')
                continue

            os.rename(path, save_path)

    def scan(self):
        files = {}

        for path in [self.files_path, self.info_path]:
            if not os.path.isdir(path):
                try:
                    os.makedirs(path)

                except:
                    print 'error creating %s' % self.files_path
                    return False

        for name in os.listdir(self.info_path):
            if not name.endswith('.trashinfo'):
                continue

            info_path = os.path.join(self.info_path, name)
            real_file = os.path.join(self.files_path, name[:-10])

            cfg = ConfigParser.ConfigParser()
            cfg.read([info_path])

            if cfg.has_section('Trash Info'):
                if cfg.has_option('Trash Info', 'Path'):
                    path = clear_path(cfg.get('Trash Info', 'Path'))
                    files[info_path] = {'path': clear_path(path),
                                        'real-file': clear_path(real_file)}

                    if cfg.has_option('Trash Info', 'DeletionDate'):
                        deletion_date = cfg.get('Trash Info', 'DeletionDate')
                        files[info_path]['deletion-date'] = deletion_date

        if files != self.files:
            self.files = files
            self.emit('files-changed', files)

        return True


def get_pixbuf_from_path(path, size=None):
    size = DEFAULT_ICON_SIZE if not size else size
    screen = Gdk.Screen.get_default()
    icon_theme = Gtk.IconTheme.get_for_screen(screen)
    gfile = Gio.File.new_for_path(path)
    info = gfile.query_info(
        'standard::icon', Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, None)
    icon = info.get_icon()
    types = icon.get_names()
    pixbuf = None

    if 'text-x-generic' in types:
        types.remove('text-x-generic')

    types.append('text-x-generic')

    if path == '/':
        types.insert(0, 'drive-harddisk')

    if 'image-x-generic' in types:
        try:
            return GdkPixbuf.Pixbuf.new_from_file_at_size(path, size, size)
        except GLib.Error:
            pass

    if path.endswith('.desktop'):
        cfg = ConfigParser.ConfigParser()
        cfg.read([path])

        if cfg.has_option('Desktop Entry', 'Icon'):
            if '/' in cfg.get('Desktop Entry', 'Icon'):
                d = cfg.get('Desktop Entry', 'Icon')
                return GdkPixbuf.Pixbuf.new_from_file_at_size(d, size, size)

            else:
                name = cfg.get('Desktop Entry', 'Icon')
                try:
                    pixbuf = icon_theme.load_icon(name, size, 0)

                except:
                    pixbuf = None

    if not pixbuf:
        try:
            return icon_theme.choose_icon(types, size, 0).load_icon()

        except:
            pixbuf = icon_theme.load_icon(icon, size, 0)

    return pixbuf


def make_menu(paths, folder, data):
    all_are_dirs = True
    readable = True
    writable = True
    if paths:
        for x in paths:
            r, w = get_access(x)
            readable = readable and r
            writable = writable and w

    else:
        readable, writable = get_access(folder)

    for x in paths:
        if not os.path.isdir(x):
            all_are_dirs = False
            break

    menu = Gtk.Menu()
    is_trash = clear_path(folder) == clear_path(TRASH_DIR)

    if paths and (paths[0] != folder or len(paths) > 1):
        item = Gtk.MenuItem(_('Open'))
        item.set_sensitive(readable)
        item.connect('activate', data['open-from-menu'])
        menu.append(item)

        if all_are_dirs:
            item = Gtk.MenuItem(_('Open in new tab'))
            item.set_sensitive(readable)
            item.connect('activate', data['open-from-menu'], True)
            menu.append(item)

        menu.append(Gtk.SeparatorMenuItem())

    if not is_trash:
        item = Gtk.MenuItem(_('Create a folder'))
        item.set_sensitive(writable)
        item.connect('activate', data['mkdir'])
        menu.append(item)

        menu.append(Gtk.SeparatorMenuItem())

    item = Gtk.MenuItem(_('Cut'))  # Copy path to clipboard
    item.set_sensitive(writable)
    item.connect('activate', data['cut'])
    menu.append(item)

    item = Gtk.MenuItem(_('Copy'))  # Copy path to clipboard
    item.set_sensitive(readable)
    item.connect('activate', data['copy'])
    menu.append(item)

    paste = _('Paste')
    """if self.selected_paths and \
        os.path.isdir(self.selected_paths[0]) and \
        self.selected_paths[0] == self.folder and \
        len(self.selected_paths) > 1 else _('Paste on this folder')
    """

    if not is_trash:
        item = Gtk.MenuItem(paste)
        item.set_sensitive(writable)  # And clipboard has paths
        item.connect('activate', data['paste'])
        menu.append(item)

        if writable and paths[0] != folder:
            item = Gtk.MenuItem(_('Rename'))
            item.connect('activate', data['rename'])
            menu.append(item)

            menu.append(Gtk.SeparatorMenuItem())

    item = Gtk.MenuItem(_('Sort items'))
    submenu = Gtk.Menu()
    item.set_submenu(submenu)
    menu.append(item)

    menu.append(Gtk.SeparatorMenuItem())

    item_name = Gtk.RadioMenuItem(_('By name'))
    item_name.set_active(data['sort'] == SORT_BY_NAME)
    item_name.connect('activate', data['sort-changed'], SORT_BY_NAME)
    submenu.append(item_name)

    item_size = Gtk.RadioMenuItem(_('By size'), group=item_name)
    item_size.set_active(data['sort'] == SORT_BY_SIZE)
    item_size.connect('activate', data['sort-changed'], SORT_BY_SIZE)
    submenu.append(item_size)

    submenu.append(Gtk.SeparatorMenuItem())

    item = Gtk.CheckMenuItem(_('Reverse'))
    item.set_active(data['reverse'])
    item.connect('activate', data['reverse-changed'])
    submenu.append(item)

    item = Gtk.MenuItem(_('Properties'))
    item.connect('activate', data['show-properties'])
    menu.append(item)

    if readable and not is_trash:
        menu.append(Gtk.SeparatorMenuItem())

        item = Gtk.MenuItem(_('Compress'))
        item.connect('activate', data['compress'])
        menu.append(item)

    if writable and not is_trash:
        menu.append(Gtk.SeparatorMenuItem())

        item = Gtk.MenuItem(_('Move to trash'))
        item.connect('activate', data['move-to-trash'])
        menu.append(item)

    if writable and paths[0] != folder:
        item = Gtk.MenuItem(_('Remove'))
        item.connect('activate', data['remove'])
        menu.append(item)

    menu.show_all()
    return menu


def get_parent_directory(folder):
    path = '/'
    folders = []

    if folder == '/':
        return folder

    if folder.endswith('/'):
        folder = folder[:-1]

    for _folder in folder.split('/'):
        if not folder:
            continue

        folders.append(_folder)

    if not folders:
        return folder

    for _folder in folders[:-1]:
        if _folder:
            path += _folder + '/'

    return path


def get_access(path):
    #  R_OK = Readable, W_OK = Writable
    return os.access(path, os.R_OK), os.access(path, os.W_OK)


def natural_sort(_list):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(_list, key=alphanum_key)


def get_size_unit(num):
    min_unit = 'B'
    units = ['KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', None]
    for unit in units:
        if abs(num) < 1024.0:
            idx = units.index(unit)
            unit = units[(idx - 1)] if idx > 0 else min_unit
            return "%3.1f%s" % (num, unit)

        if unit != 'B':
            num /= 1024.0


def get_size(paths):
    if type(paths) == str:
        readable, writable = get_access(paths)
        if not readable:
            return ''

        paths = [paths]

    folders = []
    files = []
    string = ''
    quantity = 0
    size = 0

    for x in paths:
        if os.path.isdir(x):
            folders.append(x)

        elif os.path.isfile(x):
            files.append(x)

    for x in folders:
        readable, writable = get_access(x)
        quantity += len(os.listdir(x)) if readable else 0

    for x in files:
        size += os.path.getsize(x)

    if len(folders) and len(files):
        if len(folders) > 1:
            string = '%d %s %d %s' % (
                len(folders), _('folders selecteds, contains'), quantity,
                _('items'))

        else:
            string = '%s %s %d %s' % (
                Dirs()[folders[0]],
                _('selected, contains'), quantity, _('items'))

        if len(files) > 1:
            size_str = get_size_unit(size)
            string += ' ' if string else ''
            string += '%d %s %s' % (
                len(files), 'files selecteds, weight', size_str)

        else:
            size_str = get_size_unit(size)
            string += (', %s ' % _('and')) if string else ''
            string += '%s %s %s' % (Dirs()[files[0]], _('weight'), size_str)

    elif len(folders) and not len(files):
        if len(folders) > 1:
            string = '%d %s %d %s' % (
                len(folders), _('folders selected, contains'), quantity,
                _('items'))

        else:
            string = '%s %d %s' % (_('contains'), quantity, _('items'))

    elif not len(folders) and len(files):
        size_str = get_size_unit(size)
        if len(files) > 1:
            string = '%d %s %s' % (
                len(files), _('files selected, weight'), size_str)
            return string.replace('1 files', 'A file')

        else:
            return size_str

    string = string.replace(_(' 0 items'), _(' any items'))
    string = string.replace(_(' 1 items'), _(' a item'))
    return string


def get_simple_size(path):
    readable, writable = get_access(path)
    if os.path.isfile(path):
        return get_size(path)

    else:
        if readable:
            quantity = len(os.listdir(path))
            return '%d %s' % (
                quantity, _('elements') if quantity != 1 else _('element'))

        else:
            return _('Not readable')


def get_total_size(paths=[]):
    total_size = 0
    folders = []
    files = []
    for path in paths:
        if os.path.isdir(path):
            folders.append(path)

        elif os.path.isfile(path):
            files.append(path)

    for path in files:
        total_size += os.path.getsize(path)

    for path in folders:
        for dirpath, firnames, filenames in os.walk(path):
            for name in filenames:
                path = os.path.join(dirpath, name)
                if os.path.exists(path):
                    total_size += os.path.getsize(path)

    return total_size


def get_type(path):
    unknown = 'application/octet-stream'
    path = path.replace(' ', '\ ')
    mime_type = Gio.content_type_guess(path, data=None)[0]
    if mime_type != unknown:
        return mime_type

    elif mime_type == unknown:
        if os.path.ismount(path):
            return 'inode/mount-point'

        if os.path.isdir(path):
            return 'inode/directory'

    if mime_type == unknown:
        import commands
        return commands.getoutput(
            'file --mime-type %s' % path).split(':')[1][1:]


def get_simple_type(path):
    _type = get_type(path)
    simple_types = {'application/octet-stream': _('Unknown'),
                    'inode/mount-point': _('Folder'),
                    'inode/directory': _('Folder'),
                    'video/x-msvideo': _('Video'),
                    'text/plain': _('Text'),
                    'image/x-ms-bmp': _('Image'),
                    'application/x-gtar': _('File'),
                    'application/zip': _('File')}

    _return = simple_types.get(_type, False) or _type
    if os.path.islink(path):
        return _('Link')

    if _return == _type:
        if 'text' in _return:
            _return = _('Text')

        if 'image' in _return:
            _return = _('Image')

        if 'audio' in _return:
            _return = _('Audio')

    if _return == _type:
        return _('Unknown')

    return _return


def get_created_time(path):
    return time.ctime(os.path.getctime(path))


def get_modified_time(path):
    return time.ctime(os.path.getmtime(path))


def get_simple_modified_time(path):
    return get_modified_time(path)


def get_current_time():
    t = datetime.datetime.now()
    month = ('0' + str(t.month)) if len(str(t.month)) == 1 else t.month
    day = ('0' + str(t.day)) if len(str(t.day)) == 1 else t.day
    return '%d-%s-%sT%s:%s:%s' % (t.year, month, day, t.hour, t.minute, t.second)


def get_mount_space(path):
    df = subprocess.Popen(["df"], stdout=subprocess.PIPE)
    output = df.communicate()[0]

    for info in output.splitlines()[1:]:
        data = info.split()
        device = data[0]
        total_space = data[1]
        used_space = data[2]
        free_space = data[3]
        porcentaje = data[4]
        mount = data[5]

        if clear_path(mount) == clear_path(path):
            return int(total_space), int(used_space), int(free_space)

    return (0, 0, 0)


def get_all_bookmarks():
    path = os.path.expanduser('~/.config/gtk-3.0/bookmarks')
    if not os.path.exists(path):
        return {}

    readable, writable = get_access(path)
    if not readable:
        return {}

    text = open(path, 'r').read()
    bookmarks = {}

    for path in text.splitlines():
        if path.startswith('file:///'):
            path = path[7:]  # 'file://' has 7 characters

        if ' ' in path.split('/')[-1]:
            name = get_name(path)
            path = path[:-len(name) - 1]  # -1 for the space

        else:
            name = get_name(path)

        for representation, tilde in TILDES.items():
            name = name.replace(representation, tilde)

        if not os.path.isdir(clear_path(path)):
            continue

        if not clear_path(path) in Dirs().dirs:
            bookmarks[name] = clear_path(path)

    return bookmarks


def set_default_application(path, app):
    _file = os.path.expanduser('~/.local/share/applications/mimeapps.list')
    if not os.path.exists(_file):
        folder = get_parent_directory(_file)
        if not os.path.exists(folder):
            os.makedirs(folder)

        f = open(_file, 'w')
        f.write('')
        f.close()

    cfg = ConfigParser.ConfigParser()
    cfg.read([_file])

    if not cfg.has_section('Default Applications'):
        return cfg.add_section('Default Applications')

    cfg.set('Default Applications', get_type(path), app)


def get_name(path):
    # In cases where directories ending in '/' (and the directory is managed
    # CExplorer), when directory.split('/')[-1] will return '', but this
    # function returns the correct name.

    name = '/'
    for x in path.split('/'):
        if not x:
            continue

        name = x

    return name


Dirs().mounts = []  # If you add in the __init__, every time you do Dirs(),
                    # the mounts Variable returns to []
