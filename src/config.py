# This File is part of the ltsp-manager.
#
# Copyright 2012-2018 by it's authors.
#
# Licensed under GNU General Public License 3.0 or later.
# Some rights reserved. See COPYING, AUTHORS.

from gettext import gettext as _
import configparser
import os
import sys

class Config:
    def __init__(self):
        self.path = os.path.expanduser('~/.config/ltsp-manager/')
        self.settings_file = os.path.join(self.path, 'settings')

        self.gui_defaults = {
            'show_system_groups': False,
            'show_private_groups': False,
            'visible_user_columns': 'all',
            'requests_checked_roles': '',
            'requests_checked_groups': ''}
        self.users_defaults = {
            'home_base_directory':'/home'
        }
        # Role names are parsed with config.parser and need to be lowercase.
        self.roles_defaults = {
            "administrator": 'adm,cdrom,dip,epoptes,lpadmin,plugdev,sambashare,sudo,vboxusers,$$teachers',
            "staff": 'adm,cdrom,plugdev,sambashare,vboxusers',
            "student": 'sambashare,vboxusers',
            "teacher": 'adm,cdrom,epoptes,plugdev,sambashare,vboxusers,$$teachers'}
        # Used when displaying roles in a UI, but not when saving them in a config.
        self.roles_translations = {
            "administrator": _("Administrator"),
            "staff": _("Staff"),
            "student": _("Student"),
            "teacher": _("Teacher")}

        self.parser = configparser.ConfigParser()

        if not os.path.isdir(self.path):
            os.makedirs(self.path)

        if not os.path.isfile(self.settings_file):
            self.setdefaults()

        try:
            self.parser.read(self.settings_file)
        except:
            print("could not read config file: ", sys.exc_info())
        self.setdefaults()

    def save(self):
        try:
            with open(self.settings_file, 'w') as f:
                self.parser.write(f)
        except:
            print("could not write config file: ", sys.exc_info()[0])

    def setdefaults(self, overwrite=False):
        if not self.parser.has_section('GUI'):
            self.parser.add_section('GUI')

        for k, v in self.gui_defaults.items():
            if overwrite or not self.parser.has_option('GUI', k):
                self.parser.set('GUI', k, str(v))

        if not self.parser.has_section('roles'):
            self.parser.add_section('roles')

        for k, v in self.roles_defaults.items():
            # TODO: new ltsp-manager versions are not able to append groups like
            # 'fuse' to the saved user Roles, so don't read the user settings
            # at all until we reapproach the issue.
            # if overwrite or not parser.has_option('Roles', k):
            self.parser.set('roles', k, str(v))

        if not self.parser.has_section('users'):
            self.parser.add_section('users')

        for k, v in self.users_defaults.items():
            if overwrite or not self.parser.has_option('users', k):
                self.parser.set('users', k, str(v))

        self.save()


_config_ = None


def get_config():
    global _config_
    if not _config_:
        _config_ = Config()
    return _config_
