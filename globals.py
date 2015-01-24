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
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import GdkPixbuf

DEFAULT_ICON_SIZE = 48
DEFAULT_ITEM_ICON_SIZE = 32

COLOR_UNSELECTED = Gdk.color_parse('#FFFFFF')
COLOR_SELECTED = Gdk.color_parse('#4A90D9')

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
        return name in self.dirs + self.names


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

    def scan(self):
        files = []
        directories = []

        if self.files != self.get_files():
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

        directories.sort()
        files.sort()

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
                return icon_theme.load_icon(name, size, 0)

        else:
            return icon_theme.load_icon(icon, size, 0)

    else:
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
