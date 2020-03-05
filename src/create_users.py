# This File is part of the ltsp-manager.
#
# Copyright 2012-2018 by it's authors.
#
# Licensed under GNU General Public License 3.0 or later.
# Some rights reserved. See COPYING, AUTHORS.

import datetime
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gettext import gettext as _

import config
import libuser
import ltsp_shared_folders
import dialogs
import os

class NewUsersDialog:
    def __init__(self, bus, account_manager, parent):
        self.bus = bus
        self.account_manager = account_manager
        # self.system = system
        self.parent = parent
        # self.sf = sf
        self.home = os.path.dirname(os.path.expanduser('~'))

        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/ltsp/ltsp-manager/ui/create_users.ui')
        self.builder.connect_signals(self)
        self.dialog = self.builder.get_object('create_users_dialog')
        self.dialog.set_transient_for(self.parent)
        self.user_tree = self.builder.get_object('user_treeview')
        self.user_store = self.builder.get_object('user_liststore')

        self.roles = {i: config.get_config().parser.get('roles', i) for i in config.get_config().parser.options('roles')}
        self.additional_groups = []

        self.builder.get_object('computers_number_spin').set_value(12)
        # for group in self.roles["student"].split(","):
        #     if group in self.system.groups:
        #         self.additional_groups.append(group)
        self.builder.get_object('groups_template_entry').set_text("{private_group} "+" ".join(self.additional_groups))
        self.dialog.show()

        self.help_dialog = self.builder.get_object('help_dialog')

    @staticmethod
    def replacer(template, values):
        res = template.format(**values)
        return res

    def on_template_changed(self, widget=None):
        classes_str = self.builder.get_object('classes_entry').get_text().strip()
        self.groups = classes_str.split()
        self.computers = self.builder.get_object('computers_number_spin').get_value_as_int()
        self.username_tmpl = self.builder.get_object('username_template_entry').get_text()
        self.name_tmpl = self.builder.get_object('name_template_entry').get_text()
        self.password_tmpl = self.builder.get_object('password_template_entry').get_text()
        button_apply = self.builder.get_object('button_apply')

        # Check the validity of characters in the classes entry#FIXME: libuser
        classes_validity_image = self.builder.get_object('classes_validity_image')
        if not (classes_str.replace(' ', '') + 'foo').isalnum():
            classes_validity_image.set_from_stock(Gtk.STOCK_NO, Gtk.IconSize.SMALL_TOOLBAR)
            button_apply.set_sensitive(False)
            return
        else:
            if self.groups == []:
                self.groups = ['']
            classes_validity_image.set_from_stock(Gtk.STOCK_YES, Gtk.IconSize.SMALL_TOOLBAR)
            button_apply.set_sensitive(True)

        # # Check the validity of characters in the username entry #FIXME: libuser
        # username_validity_image = self.builder.get_object('username_validity_image')
        # if (not self.username_tmpl.replace('{c}', 'a').replace('{0i}',
        #   'a').replace('{i}', 'a').replace('-', '').replace('_', '').isalnum()) or \
        #   (len(self.groups) == 1 and self.computers > 1 and not '{i}' in self.username_tmpl and \
        #   not '{0i}' in self.username_tmpl) or (self.computers == 1 and len(self.groups) > 1 and \
        #   not '{c}' in self.username_tmpl) or (self.computers > 1 and len(self.groups) > 1 and \
        #   (not '{c}' in self.username_tmpl or (not '{0i}' in self.username_tmpl and \
        #   not '{i}' in self.username_tmpl))):
        #
        #     username_validity_image.set_from_stock(Gtk.STOCK_NO, Gtk.IconSize.SMALL_TOOLBAR)
        #     button_apply.set_sensitive(False)
        #     return
        # else:
        #     username_validity_image.set_from_stock(Gtk.STOCK_YES, Gtk.IconSize.SMALL_TOOLBAR)
        #     button_apply.set_sensitive(True)
        self.user_store.clear()

        # Repopulate the store
        for groupn in self.groups:
            for compn in range(1, self.computers+1):
                if len(self.user_store) == 300:
                    break

                replacee = {"group": groupn,
                            "account_number": compn}

                username = self.replacer(self.username_tmpl, replacee)
                replacee["username"] = username
                replacee["private_group"] = username
                fullname = self.replacer(self.name_tmpl, replacee)
                password = self.replacer(self.password_tmpl, replacee)
                self.user_store.append([username, fullname, self.home + username, password])

        users_number = self.computers * len(self.groups)
        self.builder.get_object('users_number_label').set_text(_("The following %d accounts will be created") % users_number)

    def on_button_apply_clicked(self, widget):
        computers = self.builder.get_object('computers_number_spin').get_value_as_int()
        groups_tmpl = self.builder.get_object('groups_template_entry').get_text()
        button_close = self.builder.get_object('button_close')


        total_groups = len(self.groups)
        total_users = self.computers * total_groups

        progress = dialogs.ProgressDialog(_("Creating all users"), total_users + total_groups, self.dialog, on_close=self.on_button_cancel_clicked)

        users_created = 0
        groups_created = 0
        set_gids = []
        set_uids = []

        # Create groups for all the listed classes
        if self.groups != ['']:
            for groupn in self.groups:
                dialogs.wait_gtk()
                group_path = self.account_manager.FindGroupByName(groupn)
                if group_path == "/None":
                    group_path = self.account_manager.CreateGroup(groupn)
                    progress.set_message(_("Creating group %(current)d of %(total)d...")
                        % {"current":groups_created+1, "total":total_groups})
                    # FIXME Show error: if cmd_error[0] and cmd_error[1] != "":
                    #     self.builder.get_object('error_label').set_text(cmd_error[1])
                    #     self.builder.get_object('error_hbox').show()
                    #     button_close.set_sensitive(True)
                    #     return
                groups_created += 1
                progress.set_progress(groups_created)

                # FIXME Add teachers to group
                # if self.builder.get_object('teachers_checkbutton').get_active():
                #     progress.set_message(_("Adding teachers to group {group}").format(group=groupn))
                #     group = self.dbus.get_object()
                #     for user in self.dbus.fin:
                #         dialogs.wait_gtk()
                #         if 'teachers' in user.groups and groupn not in user.groups:
                #             user.groups.append(groupn)
                #             self.system.update_user(user.name, user)

            # Create shared folders
            # if self.builder.get_object('shared_checkbutton').get_active():
            #     for groupn in self.groups:
            #         progress.set_message(_("Adding shares for {group}").format(group=groupn))
            #         dialogs.wait_gtk()
            #         # self.sf.add([groupn])

        # And finally, create the users
        for groupn in self.groups:
            for compn in range(1, self.computers+1):
                dialogs.wait_gtk()
                progress.set_message(_("Creating user {current} of {total}...").format(current=users_created+1, total=total_users))

                replacee = {"group": groupn,
                            "account_number": compn}

                username = self.replacer(self.username_tmpl, replacee)
                replacee["username"] = username
                replacee["private_group"] = username
                password = self.replacer(self.password_tmpl, replacee)
                name = self.replacer(self.name_tmpl, replacee)

                self.account_manager.CreateUser(username, {"fullname":name, "password":password})

                # FIXME add additional groups

                users_created += 1
                progress.set_progress(groups_created + users_created)

        # if cmd_error[0] and cmd_error[1] != "":
        #     self.progress.set_error(cmd_error.strip())
        #     return

    def on_button_cancel_clicked(self, widget=None):
        self.dialog.destroy()
        self.help_dialog.destroy()

    def on_button_help_clicked(self, widget):
        self.help_dialog.show()

    def on_help_close_clicked(self, widget, dummy=None):
        self.help_dialog.hide()
        return True
