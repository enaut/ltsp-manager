# This File is part of the ltsp-manager.
#
# Copyright 2012-2018 by it's authors.
#
# Licensed under GNU General Public License 3.0 or later.
# Some rights reserved. See COPYING, AUTHORS.

"""
New user form.
"""
from gettext import gettext as _
import os
from gi.repository import Gtk
import common
import config
import paths

from user_elements import TextLineEntry, NumberLineEntry, LabelLineEntry, ComboLineEntry, Validators, Updaters


class UserForm():
    """ The form that is responsible for creating or modifying one user. """

    def __init__(self, mode, bus, account_manager, parent):
        self.bus = bus
        self.account_manager = account_manager
        self.user = None
        self.mode = mode
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/ltsp/ltsp-manager/ui/user_form19.ui')

        # states
        self.primary_group = None
        self.show_sys_groups = False
        self.active_from_role = []
        self.roles = {i: config.get_config().parser.get('roles', i).replace('$$teachers', 'teachers') for i in config.get_config().parser.options('roles')}
        self.selected_role = None

        self.dialog = self.builder.get_object('dialog')
        self.dialog.set_transient_for(parent)

        # Has to be first
        self.homedir = TextLineEntry(self, 'homedir_entry', 'homedir_valid', '', Validators.home_validator, Updaters.homedir_updater)
        # User settings general
        self.username = TextLineEntry(self, 'username_entry', 'username_valid', '', Validators.username_validator, Updaters.username_updater)
        self.password = TextLineEntry(self, 'password_entry', 'password_valid', '', Validators.edit_or_something_validator)
        self.gc_name = TextLineEntry(self, 'full_name_entry', 'full_name_valid', '', Validators.no_comma_validator)
        # User settings details
        self.uid_entry = NumberLineEntry(self, 'uid_entry', 'uid_valid', -1, Validators.uid_validator)
        self.shells_combo = self.builder.get_object('shell_combo')
        self.shells_entry = ComboLineEntry(self, 'shell_combo_entry', None, '/bin/bash', Validators.no_validator)
        self.gc_office = TextLineEntry(self, 'office_entry', "office_valid", '', Validators.no_comma_validator)
        self.gc_office_phone = TextLineEntry(self, 'office_phone_entry', "office_phone_valid", '', Validators.no_comma_validator)
        self.gc_home_phone = TextLineEntry(self, 'home_phone_entry', "home_phone_valid", '', Validators.no_comma_validator)
        self.gc_other = TextLineEntry(self, 'other_entry', "other_valid", '', Validators.no_comma_validator)
        self.last_change = NumberLineEntry(self, 'last_change', None, 0, Validators.no_validator)
        self.minimum = NumberLineEntry(self, 'minimum', None, 0, Validators.no_validator)
        self.maximum = NumberLineEntry(self, 'maximum', None, -1, Validators.no_validator)
        self.warn = NumberLineEntry(self, 'warn', None, 0, Validators.no_validator)
        self.inactive = NumberLineEntry(self, 'inactive_spin', None, -1, Validators.no_validator)
        self.expire = NumberLineEntry(self, 'expire', None, -1, Validators.no_validator)
        # Group settings
        self.primary_groupname_label = LabelLineEntry(self, 'primary_groupname', None, _('<create a new group>'), Validators.no_validator)
        self.primary_group_id_label = LabelLineEntry(self, 'primary_group_id', None, _('<new group id>'), Validators.no_validator)
        self.role_combo = self.builder.get_object('role_combo')
        self.groups_tree = self.builder.get_object('groups_treeview')
        self.groups_store = self.builder.get_object('groups_liststore')
        self.groups_filter = self.builder.get_object('groups_filter')
        self.groups_sort = self.builder.get_object('groups_sort')

        self.user_lines = [self.username, self.password, self.homedir, self.gc_name, self.uid_entry,
                           self.shells_entry, self.primary_group_id_label, self.primary_groupname_label]
        self.gcos_lines = [self.gc_name, self.gc_office, self.gc_office_phone, self.gc_home_phone, self.gc_other]
        self.spwd_lines = [self.last_change, self.expire, self.inactive, self.minimum, self.maximum, self.warn]

        self.groups_filter.set_visible_func(self.groups_visible_func)
        self.groups_sort.set_sort_column_id(1, Gtk.SortType.ASCENDING)

        self.load_groups()

        # Fill the shells combobox
        for shell in self.get_valid_shells():
            self.shells_combo.append_text(shell)

        # Fill the roles combobox
        for role, _groups in self.roles.items():
            self.role_combo.append_text(role)

        self.set_apply_sensitivity()

    def load_groups(self):
        """ Fill the groups treeview """
        # object, name, active, activatable, font weight, actually active, gid
        for grouppath in self.account_manager.ListGroups():
            group = self.bus.get_object('io.github.ltsp-manager', grouppath)
            self.groups_store.append([group, group.GetGroupName(), False, True, 400, False, group.GetGID()])

    def set_gcos(self, user):
        """ Set all the Gcos values if something has changed """
        if any([i.changed() for i in self.gcos_lines]):
            user.SetGecos(*[i.get_value() for i in self.gcos_lines])

    def set_spwd(self, user):
        """ Set all the Spwd values if something has changed """
        if any([i.changed() for i in self.spwd_lines]):
            user.SetSpwd(*[i.get_value() for i in self.spwd_lines])

    @staticmethod
    def get_valid_shells():
        """ Get the shells from the file /etc/shells """
        try:
            fil = open(os.path.join(paths.sysconfdir, "shells"))
            shells = [line.strip() for line in fil.readlines() if line.strip()[0] != '#']
            fil.close()
        except FileNotFoundError:
            shells = []

        return shells

    # """ Group memberships """

    def groups_visible_func(self, model, itr, _x):
        """ Set the visibility of groups in the user creation dialog. Do hide for example system groups """
        row = model[itr]
        activatable = row[3]
        group = row[0]
        primary_group = not activatable or group.UsersAreMember([self.username.entry.get_text()])
        show_user_group = self.show_sys_groups or not group.IsSystemGroup()
        show_private_group = config.get_config().parser.getboolean('GUI', 'show_private_groups') or not model[itr][0].IsPrivateGroup()
        return (show_user_group and show_private_group) or primary_group

    def on_show_sys_groups_toggled(self, widget):
        """ react to the show system groups check button """
        self.show_sys_groups = not self.show_sys_groups
        self.groups_filter.refilter()
        if self.show_sys_groups:
            self.groups_sort.set_sort_column_id(6, Gtk.SortType.ASCENDING)
        else:
            self.groups_sort.set_sort_column_id(1, Gtk.SortType.ASCENDING)

    def on_role_combo_changed(self, widget):
        """ React to a role change TODO not working! """
        role = widget.get_active_text()
        self.selected_role = role
        for row in self.active_from_role:
            row[2] = False
        self.active_from_role = []

        if role is not None:
            groups = self.roles[role].split(',')
            for row in self.groups_store:
                if row[0].name in groups:
                    row[2] = True
                    self.active_from_role.append(row)

    def on_group_toggled(self, widget, path):
        """ If the checkbutton of a group row is toggled """
        path = self.groups_sort[path].path
        path = self.groups_sort.convert_path_to_child_path(path)
        path = self.groups_filter.convert_path_to_child_path(path)

        self.groups_store[path][2] = not self.groups_store[path][2]
        self.groups_store[path][5] = not self.groups_store[path][5]

    def on_groups_selection_changed(self, widget):
        """ Make the assign_primary_group_button sensitive if exactly one group is selected as main group"""
        self.builder.get_object('set_primary_button').set_sensitive(len(widget.get_selected_rows()[1]) == 1)

    def on_set_primary_button_clicked(self, widget):
        """ The pathlist will always contain 1 element, I just use
            get_selected_rows here instead of get_selected for extra features
            such as context menu actions which would work with multiple selection """
        _model, pathlist = self.groups_tree.get_selection().get_selected_rows()

        path = self.groups_sort[pathlist[0]].path
        path = self.groups_sort.convert_path_to_child_path(path)
        path = self.groups_filter.convert_path_to_child_path(path)
        row = self.groups_store[path]

        # Mark the group as primary
        self.set_group_primary(row)

        # Set the primary group name and gid entries
        self.primary_groupname_label.entry.set_text(str(row[0].GetGroupName()))
        self.primary_group_id_label.entry.set_text(str(row[0].GetGID()))

    def unset_primary(self):
        """ remove the primary group flag """
        if self.primary_group:
            self.primary_group[2] = self.primary_group[5]
            self.primary_group[3] = True
            self.primary_group[4] = 400
            self.primary_group = None

    def set_group_primary(self, row):
        """ Make a group the primary group of this user """
        # Unset the previous primary group
        self.unset_primary()
        row[2] = True    # Activate this group
        row[3] = False   # Make it non-(de)activatable since it's now primary
        row[4] = 700     # Make the name bold to distinguish it

        # Remember the new primary group
        self.primary_group = row

    # """ General Methods """
    @staticmethod
    def get_icon(check):
        """Return the icon according to the boolean."""
        if check:
            return Gtk.STOCK_YES
        return Gtk.STOCK_NO

    def set_apply_sensitivity(self):
        """ Set the apply button sensitive when all values entered are ok. """
        def icon(x):
            return self.builder.get_object(x).get_stock()[0]

        ids = ['username_valid', 'uid_valid', 'password_valid', 'full_name_valid',
               'office_valid', 'office_phone_valid', 'home_phone_valid', 'other_valid',
               'homedir_valid']
        sensitive = all([icon(x) == self.get_icon(True) for x in ids])
        self.builder.get_object('apply_button').set_sensitive(sensitive)

    def on_dialog_delete_event(self, widget, event):
        """ quit """
        self.dialog.destroy()

    def on_cancel_clicked(self, widget):
        """ quit """
        self.dialog.destroy()


class NewUserDialog(UserForm):
    """ The Dialog that prompts for a new user. """

    def __init__(self, bus, account_manager, parent=None):
        super().__init__('new', bus, account_manager, parent=parent)
        self.builder.connect_signals(self)

        # Set some defaults
        self.last_change.set_initial_value(common.days_since_epoch())
        self.set_apply_sensitivity()

        self.dialog.show()

    def on_apply_clicked(self, widget):
        """ Actions that happen when the user confirms his entries """
        params = {}
        if self.homedir.changed():
            params["home"] = self.homedir.get_value()
        if self.gc_name.changed():
            params["fullname"] = self.gc_name.get_value()
        if self.uid_entry.changed():
            params["uid"] = str(self.uid_entry.get_value())
        if self.primary_group_id_label.changed():
            params["gid"] = str(self.primary_group_id_label.get_value())
        user_path = self.account_manager.CreateUser(self.username.get_value(), params)
        user = self.bus.get_object('io.github.ltsp-manager', user_path)
        self.set_gcos(user)
        self.set_spwd(user)

        self.dialog.destroy()


class EditUserDialog(UserForm):
    """ The Dialog that edits a user. """

    def __init__(self, bus, account_manager, user, parent=None):
        super().__init__('edit', bus, account_manager, parent=parent)
        self.user = user
        self.builder.connect_signals(self)

        username = user.GetUsername()
        self.username.set_initial_value(username)
        self.uid_entry.set_initial_value(user.GetUID())
        self.homedir.set_initial_value(user.GetHomeDir())
        self.shells_entry.set_initial_value(user.GetShell())
        rname, office, offphon, homphon, other = user.GetGecos()
        self.gc_name.set_initial_value(rname)
        self.gc_office.set_initial_value(office)
        self.gc_office_phone.set_initial_value(offphon)
        self.gc_home_phone.set_initial_value(homphon)
        self.gc_other.set_initial_value(other)
        lstchg, umin, umax, warn, inact, expire = user.GetSpwd()
        self.last_change.set_initial_value(lstchg)
        self.minimum.set_initial_value(umin)
        self.maximum.set_initial_value(umax)
        self.warn.set_initial_value(warn)
        self.inactive.set_initial_value(inact)
        self.expire.set_initial_value(expire)
        # self.builder.get_object('locked_account_check').set_active(self.system.user_is_locked(user))
        self.main_group_path = user.GetMainGroup()
        self.main_group = self.bus.get_object('io.github.ltsp-manager', self.main_group_path)
        self.primary_groupname_label.set_initial_value(self.main_group.GetGroupName())
        self.primary_group_id_label.set_initial_value(str(self.main_group.GetGID()))
        # Activate the groups in which the user belongs and mark the primary
        for row in self.groups_store:
            if row[0].UsersAreMember([username]):
                row[2] = True
                row[5] = True
            if self.account_manager.FindGroupByName(row[1]) == self.main_group_path:
                self.primary_group = row
                self.set_group_primary(row)

        self.dialog.show()

    def on_apply_clicked(self, widget):
        """ Actions that happen when the user confirms his entries """
        self.set_gcos(self.user)
        self.set_spwd(self.user)

        if self.username.changed():
            self.user.SetUsername(self.username.get_value())
        if self.uid_entry.changed():
            self.user.SetUID(self.uid_entry.get_value())
        if self.homedir.changed():
            move_files = self.builder.get_object('move_files').get_active()
            self.user.SetHomeDir(self.homedir.get_value(), move_files)
        if self.shells_entry.changed():
            self.user.SetShell(self.shells_entry.get_value())
        if self.password.changed():
            self.user.SetPassword(self.password.get_value())
        if self.primary_group_id_label.changed():
            self.user.SetGID(int(self.primary_group_id_label.get_value()))

        self.dialog.destroy()


class ReviewUserDialog(UserForm):
    def __init__(self, bus, account_manager, user, role='', callback=None, parent=None):
        super().__init__('new', bus, account_manager, parent=parent)
        # self.callback = callback
        # self.user = user
        # self.selected_role = role
        # self.builder.connect_signals(self)
        #
        # self.username.set_text(user.name)
        # if user.password not in ['!', '*', ''] or user.plainpw:
        #     self.password.set_text('\n'*8)
        #     self.password_repeat.set_text('\n'*8)
        # self.uid_entry.set_text(str(user.uid))
        # self.homedir.set_text(user.directory)
        # self.shells_entry.set_text(user.shell)
        # self.gc_name.set_text(user.rname)
        # self.gc_office.set_text(user.office)
        # self.gc_office_phone.set_text(user.wphone)
        # self.gc_home_phone.set_text(user.hphone)
        # self.gc_other.set_text(user.other)
        # self.last_change.set_value(user.lstchg)
        # self.minimum.set_value(user.min)
        # self.maximum.set_value(user.max)
        # self.warn.set_value(user.warn)
        # self.inactive.set_value(user.inact)
        # self.expire.set_value(user.expire)
        # self.builder.get_object('locked_account_check').set_active(user.password[0] == '!')
        #
        # self.pgroup.set_text(user.primary_group)
        # self.pgid.set_text(str(user.gid))
        # # Activate the groups in which the user belongs and mark the primary
        # for row in self.groups_store:
        #     for gr in user.groups:
        #         if gr == row[0].name:
        #             row[2] = True
        #             row[5] = True
        #     if row[1] == user.primary_group:
        #         self.primary_group = row
        #         self.set_group_primary(row)
        #
        # if role:
        #     for r in self.role_combo.get_model():
        #         if r[0] == role:
        #             self.role_combo.set_active_iter(r.iter)
        #             break
        #
        # self.dialog.show()

    def on_apply_clicked(self, widget):
        pass
        # self.user.rname = self.gc_name.get_text()
        # self.user.uid = int(self.uid_entry.get_text())
        # self.user.office = self.gc_office.get_text()
        # self.user.wphone = self.gc_office_phone.get_text()
        # self.user.hphone = self.gc_home_phone.get_text()
        # self.user.other = self.gc_other.get_text()
        # self.user.directory = self.homedir.get_text()
        # self.user.shell = self.shells_entry.get_text()
        # self.user.lstchg = int(self.last_change.get_value())
        # self.user.min = int(self.minimum.get_value())
        # self.user.max = int(self.maximum.get_value())
        # self.user.warn = int(self.warn.get_value())
        # self.user.inact = int(self.inactive.get_value())
        # self.user.expire = int(self.expire.get_value())
        #
        # self.user.groups = [g[1] for g in self.groups_store if g[2]]
        # self.user.gid = int(self.pgid.get_text())
        # self.user.primary_group = self.pgroup.get_text()
        #
        # if self.builder.get_object('locked_account_check').get_active():
        #     if self.user.password[0] != '!':
        #         self.user.password = '!'+self.user.password
        # self.dialog.destroy()
        # if self.callback:
        #     self.callback(self.selected_role)
