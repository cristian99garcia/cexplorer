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
import re
import time
import ConfigParser
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import GdkPixbuf

DEFAULT_ICON_SIZE = 48
DEFAULT_ITEM_ICON_SIZE = 32

ERROR_NOT_READABLE = 0
ERROR_NOT_UNWRITABLE = 1
ERROR_ALREADY_EXISTS = 2
ERROR_INVALID_NAME = 3

TITLE_ERROR_UNREADABLE = _('Could not be displayed here.')
TITLE_ERROR_UNWRITABLE = _('Could not be set.')
TITLE_ERROR_ALREADY_EXISTS = _('Could not rename.')
TITLE_ERROR_INVALID_NAME = _('Could not rename.')

MSG_UNREADABLE = _('You do not have sufficient permissions to view the content of "@".')
MSG_UNWRITABLE = _('You do not have sufficient permissions to edit "@".')
MSG_ALREADY_EXISTS = _('You can not rename to "@", because already exists.')
MSG_INVALID_NAME = _('"@"" is a invalid name for a file.')

SORT_BY_NAME = 0
SORT_BY_SIZE = 1

HOME_DIR = os.path.expanduser('~')
HOME_NAME = _('Personal folder')
DESKTOP_DIR = GLib.get_user_special_dir(GLib.USER_DIRECTORY_DESKTOP)
DESKTOP_NAME = _('Desktop')
DOCUMENTS_DIR = GLib.get_user_special_dir(GLib.USER_DIRECTORY_DOCUMENTS)
DOCUMENTS_NAME = _('Documents')
DOWNLOADS_DIR = GLib.get_user_special_dir(GLib.USER_DIRECTORY_DOWNLOAD)
DOWNLOADS_NAME = _('Donwloads')
MUSIC_DIR = GLib.get_user_special_dir(GLib.USER_DIRECTORY_MUSIC)
MUSIC_NAME = _('Music')
PICTURES_DIR = GLib.get_user_special_dir(GLib.USER_DIRECTORY_PICTURES)
PICTURES_NAME = _('Pictures')
VIDEOS_DIR = GLib.get_user_special_dir(GLib.USER_DIRECTORY_VIDEOS)
VIDEOS_NAME = _('Videos')
SYSTEM_DIR = '/'
SYSTEM_NAME = _('Equipment')

KEYS = {65293: 'Enter'}

class Dirs(object):
    """
    A Singleton class, it's possible make a only instance of this class:

    >>> dirs1 = Dirs()
    >>> dirs2 = Dirs()
    >>> print dirs1 == dirs2
    ... True
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
                     SYSTEM_DIR]

        self.names = [HOME_NAME,
                      DESKTOP_NAME,
                      DOCUMENTS_NAME,
                      DOWNLOADS_NAME,
                      MUSIC_NAME,
                      PICTURES_NAME,
                      VIDEOS_NAME,
                      SYSTEM_NAME]

        self.specials_dirs = {HOME_DIR: HOME_NAME,
                              SYSTEM_DIR: SYSTEM_NAME}

        self.symbolic_icons = {HOME_DIR: 'go-home-symbolic',
                               DESKTOP_DIR: 'user-desktop-symbolic',
                               DOCUMENTS_DIR: 'folder-documents-symbolic',
                               DOWNLOADS_DIR: 'folder-download-symbolic',
                               MUSIC_DIR: 'folder-music-symbolic',
                               PICTURES_DIR: 'folder-pictures-symbolic',
                               VIDEOS_DIR: 'folder-videos-symbolic',
                               SYSTEM_DIR: 'drive-harddisk-system-symbolic'}

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Dirs, cls).__new__(cls, *args, **kwargs)

        return cls._instance

    def __getitem__(self, name):
        """
        >>> dirs = Dirs()
        >>> print dirs[HOME_DIR]  # Get directory name a special directory
        ... 'Personal folder'

        >>> print dirs[SYSTEM_DIR]
        ... 'Equipment'

        >>> print dirs['/home/cristian/']  # Get name from another directory
        ... 'cristian'
        """
        if name in self.specials_dirs:
            return self.specials_dirs[name]

        else:
            if name.endswith('.desktop'):
                cfg = ConfigParser.ConfigParser()
                cfg.read([name])

                if cfg.has_option('Desktop Entry', 'Name'):
                    return cfg.get('Desktop Entry', 'Name')

            path, name = os.path.split(name)
            return name if name else path

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

        for x in self.dirs:
            if not x.endswith('/'):
                x += '/'

            if not name.endswith('/'):
                name += '/'

            if name == x:
                return True

        return False

    def get_pixbuf_symbolic(self, path):
        icon_theme = Gtk.IconTheme()
        return icon_theme.load_icon(self.symbolic_icons[path], 16, 0)


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

        GObject.timeout_add(timeout, self.scan)

    def scan(self, force=False):
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
        _files = os.listdir(self.folder)

        for name in _files:
            filename = os.path.join(self.folder, name)

            if (not name.startswith('.') and not name.endswith('~')) or self.show_hidden_files:
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


def get_pixbuf_from_path(path, size=None):
    size = DEFAULT_ICON_SIZE if not size else size
    icon_theme = Gtk.IconTheme()
    gfile = Gio.File.new_for_path(path)
    info = gfile.query_info('standard::icon', Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, None)
    icon = info.get_icon()
    types = icon.get_names()
    pixbuf = None

    if 'text-x-generic' in types:
        types.remove('text-x-generic')

    types.append('text-x-generic')

    if path == '/':
        types.insert(0, 'drive-harddisk')

    if 'image-x-generic' in types:
        return GdkPixbuf.Pixbuf.new_from_file_at_size(path, size, size)

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


def get_size_unity(size):
    if size < 1024:
        return size, 'B'

    elif size >= 1024 and size < 1024 ** 2:
        return size / 1024, 'KB'

    elif size >= 1024 ** 2 and size < 1024 ** 3:
        return size / 1024 / 1024, 'MB'

    elif size >= 1024 ** 3 and size < 1024 ** 4:
        return size / 1024 / 1024 / 1024, 'GB'

    elif size >= 1024 ** 4:
        return size / 1024 / 1024 / 1024 / 1024, 'TB'


def get_size(path):
    if type(path) == str:
        writable, readable = get_access(path)
        if not readable:
            return ''

    if type(path) == list:
        folders = []
        files = []
        string = ''
        quantity = 0
        size = 0

        for x in path:
            if os.path.isdir(x):
                folders.append(x)

            elif os.path.isfile(x):
                files.append(x)

        for x in folders:
            quantity += len(os.listdir(x))

        for x in files:
            size += os.path.getsize(x)

        if len(folders) and len(files):
            if len(folders) > 1:
                string = '%d %s %d %s ' % (len(folders), _('folders selecteds, contains'), quantity, _('items, and'))

            else:
                string = '%s %s %d %s ' % (Dirs()[folders[0]], _('contains'), quantity, _('items, and'))

            if len(files) > 1:
                size, size_str = get_size_unity(size)
                string += '%d %s %d%s' % (len(files), 'files selecteds, weight', size, size_str)

            else:
                size, size_str = get_size_unity(size)
                string += '%s %s %d%s' % (Dirs()[files[0]], _('weight'), size, size_str)

            string = string.replace('0 items', 'any items')
            return string.replace('1 items', 'a item')

        elif len(folders) and not len(files):
            if len(folders) > 1:
                string = '%d %s %d %s' % (len(folders),  _('folders selected, contains'), quantity, _('items'))

            else:
                string = '%s %d %s' % (_('Contains'), quantity, _('items'))

            string = string.replace('0 items', 'any items')
            return string.replace('1 items', 'a item')

        elif not len(folders) and len(files):
            size, size_str = get_size_unity(size)
            if len(files) > 1:
                string = '%d %s %d%s' % (len(files), _('files selected, weight'), size, size_str)
                return string.replace('1 files', 'A file')

            else:
                return '%d%s' % (size, size_str)

    if os.path.isdir(path):
        text = _('Contains @ items').replace('@', str(len(os.listdir(path))))
        text = text.replace('0 items', 'any items')
        return text.replace('1 items', 'a item')

    elif os.path.isfile(path):
        size = os.path.getsize(path)
        size, size_str = get_size_unity(size)

        return 'Size: %d%s' % (size, size_str)


def clear_path(path):
    if not path.endswith('/'):
        path += '/'

    path = path.replace('//', '/')
    path = path.replace('//', '/')

    return path


def get_type(path):
    unknown = 'application/octet-stream'
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
        return commands.getoutput('file --mime-type %s' % path).split(':')[1][1:]


def get_created_time(path):
    return time.ctime(os.path.getctime(path))


def get_modified_time(path):
    return time.ctime(os.path.getmtime(path))
