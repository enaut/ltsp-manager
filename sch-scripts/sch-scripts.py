#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2012 Fotis Tsamis <ftsamis@gmail.com>
# License GNU GPL version 3 or newer <http://gnu.org/licenses/gpl.html>

import sys
import subprocess
from gi.repository import Gtk
import libuser
import user_form
import group_form
import dialogs
import export_dialog
import config
import ip_dialog

class Gui:
    def __init__(self):
        self.system = libuser.System()
        self.conf = config.parser
        
        self.builder = Gtk.Builder()
        self.builder.add_from_file('sch-scripts.ui')
        self.builder.connect_signals(self)
        
        self.main_window = self.builder.get_object('main_window')
        self.users_tree = self.builder.get_object('users_treeview')
        self.groups_tree = self.builder.get_object('groups_treeview')
        self.users_sort = self.builder.get_object('users_sort')
        self.groups_sort = self.builder.get_object('groups_sort')
        self.users_filter = self.builder.get_object('users_filter')
        self.groups_filter = self.builder.get_object('groups_filter')
        self.users_model = self.builder.get_object('users_store')
        self.groups_model = self.builder.get_object('groups_store')
        
        self.show_private_groups = False
        self.show_system_groups = False
        self.builder.get_object('show_private_groups_mi').set_active(self.conf.getboolean('GUI', 'show_private_groups'))
        self.builder.get_object('show_system_groups_mi').set_active(self.conf.getboolean('GUI', 'show_system_groups'))
        
        self.users_filter.set_visible_func(self.set_user_visibility)
        self.groups_filter.set_visible_func(self.set_group_visibility)
        
        # Fill the View -> Columns menu with all the columns of the treeview
        view_columns_menu = self.builder.get_object('view_columns_menu')
        users_columns = self.users_tree.get_columns()
        
        visible = self.conf.get('GUI', 'visible_user_columns')
        if visible == 'all':
            visible = [c.get_title() for c in users_columns]
        else:
            visible = visible.split(',')
        for column in users_columns:
            title = column.get_title()
            menuitem = Gtk.CheckMenuItem(title)
            menuitem.connect('toggled', self.on_view_column_toggled, column)
            menuitem.set_active(title in visible)
            view_columns_menu.append(menuitem)
        self.populate_treeviews()
        self.main_window.show_all()
    
    def populate_treeviews(self):
        """Fill the users and groups treeviews from the system"""
        for user in self.system.users.values():
            self.users_model.append([user, user.uid, user.name, user.primary_group, user.rname, user.office, user.wphone, user.hphone, user.other, user.directory, user.shell, user.lstchg, user.min, user.max, user.warn, user.inact, user.expire])
        for group in self.system.groups.values():
            self.groups_model.append([group, group.gid, group.name])
    
    def repopulate_treeviews(self):
        # Preserve the selected groups and users
        groups_selection = self.groups_tree.get_selection()
        users_selection = self.users_tree.get_selection()
        selected_groups = [i.name for i in self.get_selected_groups()]
        selected_users = [i.name for i in self.get_selected_users()]
        
        # Clear and refill the treeviews
        self.users_model.clear()
        self.groups_model.clear()
        self.system.reload()
        self.populate_treeviews()
        
        # Reselect the previously selected groups and users, if possible
        groups_iters = dict((row[0].name, row.iter) for row in self.groups_sort)
        for gname in selected_groups:
            if gname in groups_iters:
                groups_selection.select_iter(groups_iters[gname])
        users_iters = dict((row[0].name, row.iter) for row in self.users_sort)
        for uname in selected_users:
            if uname in users_iters:
                users_selection.select_iter(users_iters[uname])
    
    def set_user_visibility(self, model, rowiter, options):
        user = model[rowiter][0]
        selected = self.get_selected_groups()
        # FIXME: The list comprehension here costs
        return (len(selected) == 0 and (self.show_system_groups or not user.is_system_user())) \
                or user in [u for g in selected for u in g.members.values()]
    
    def set_group_visibility(self, model, rowiter, options):
        group = model[rowiter][0]
        return (self.show_private_groups or not group.is_private()) and (self.show_system_groups or group.is_user_group())
    
    def on_import_csv_activate(self, widget):
        pass
    
    def on_export_csv_activate(self, widget):
        users = self.get_selected_users()
        if len(users) == 0:
            if self.show_system_groups:
                users = self.system.users.values()
            else:
                users = [u for u in self.system.users.values() if not u.is_system_user()]
        export_dialog.ExportDialog(self.system, users)
    
    def on_groups_selection_changed(self, selection):
        self.users_filter.refilter()
        edit_mi = self.builder.get_object('edit_group_mi')
        delete_mi = self.builder.get_object('delete_group_mi')
        rows = selection.count_selected_rows()
        if rows == 0:
            edit_mi.set_sensitive(False)
            delete_mi.set_sensitive(False)
        elif rows == 1:    
            edit_mi.set_sensitive(True)
            edit_mi.set_label('Επεξεργασία ομάδας...')
            delete_mi.set_label('Διαγραφή ομάδας...')
            delete_mi.set_sensitive(True)
        else:
            edit_mi.set_sensitive(False)
            delete_mi.set_label('Διαγραφή ομάδων...')
            delete_mi.set_sensitive(True)
    
    def on_users_selection_changed(self, selection):
        edit_mi = self.builder.get_object('edit_user_mi')
        delete_mi = self.builder.get_object('delete_user_mi')
        remove_mi = self.builder.get_object('remove_user_mi')
        rows = selection.count_selected_rows()
        if rows == 0:
            edit_mi.set_sensitive(False)
            delete_mi.set_sensitive(False)
            remove_mi.set_sensitive(False)
        else:
            if self.groups_tree.get_selection().count_selected_rows() > 0:
                remove_mi.set_sensitive(True)
            else:
                remove_mi.set_sensitive(False)

            delete_mi.set_sensitive(True)
            
            if rows == 1:    
                edit_mi.set_sensitive(True)
                edit_mi.set_label('Επεξεργασία χρήστη...')
                delete_mi.set_label('Διαγραφή χρήστη...')
            else:
                edit_mi.set_sensitive(False)
                delete_mi.set_label('Διαγραφή χρηστών...')
            
    
    def on_users_tv_button_press_event(self, widget, event):
        clicked = widget.get_path_at_pos(int(event.x), int(event.y))
        
        if event.button == 3:
            menu = self.builder.get_object('users_menu').popup(None, None, None, None, event.button, event.time)
            selection = widget.get_selection()
            selected = selection.get_selected_rows()[1]
            if clicked:
                clicked = clicked[0]
                if clicked not in selected:
                    selection.unselect_all()
                    selection.select_path(clicked)
            else:
                selection.unselect_all()
            return True
    
    def on_groups_tv_button_press_event(self, widget, event):
        clicked = widget.get_path_at_pos(int(event.x), int(event.y))
        
        if event.button == 3:
            menu = self.builder.get_object('groups_menu').popup(None, None, None, None, event.button, event.time)
            selection = widget.get_selection()
            selected = selection.get_selected_rows()[1]
            if clicked:
                clicked = clicked[0]
                if clicked not in selected:
                    selection.unselect_all()
                    selection.select_path(clicked)
            else:
                selection.unselect_all()
            return True
    
    def on_users_treeview_row_activated(self, widget, path, column):
        user_form.EditUserDialog(self.system, widget.get_model()[path][0], self.repopulate_treeviews)
    
    def on_groups_treeview_row_activated(self, widget, path, column):
        group_form.EditGroupDialog(self.system, widget.get_model()[path][0], self.repopulate_treeviews)
    
    def on_main_window_delete_event(self, widget, event):
        self.conf.set('GUI', 'show_private_groups', str(self.show_private_groups))
        self.conf.set('GUI', 'show_system_groups', str(self.show_system_groups))
        visible_cols = [col.get_title() for col in self.users_tree.get_columns() if col.get_visible()]
        self.conf.set('GUI', 'visible_user_columns', ','.join(visible_cols))
        config.save()
        exit()
    
    def on_view_column_toggled(self, checkmenuitem, treeviewcolumn):
        treeviewcolumn.set_property('visible', checkmenuitem.get_active())
    
    def on_show_system_groups_mi_toggled(self, widget):
        self.show_system_groups = not self.show_system_groups
        self.groups_filter.refilter()
        self.users_filter.refilter()
    
    def on_show_private_groups_mi_toggled(self, widget):
        self.show_private_groups = not self.show_private_groups
        self.groups_filter.refilter()
    
    def get_selected_users(self):
        selection = self.users_tree.get_selection()
        paths = selection.get_selected_rows()[1]
        selected = [self.users_sort[path][0] for path in paths]
        return selected
        
    def get_selected_groups(self):
        selection = self.groups_tree.get_selection()
        paths = selection.get_selected_rows()[1]
        selected = [self.groups_sort[path][0] for path in paths]
        return selected
    
    def on_new_user_mi_activate(self, widget):
        user_form.NewUserDialog(self.system, self.repopulate_treeviews)
    
    def on_edit_user_mi_activate(self, widget):
        user_form.EditUserDialog(self.system, self.get_selected_users()[0], self.repopulate_treeviews)
    
    def on_delete_user_mi_activate(self, widget):
        users = self.get_selected_users()
        users_n = len(users)
        if users_n == 1:
            message = "Θέλετε σίγουρα να διαγράψετε τον χρήστη %s;" % users[0].name
        else:
            message = "Θέλετε σίγουρα να διαγράψετε τους παρακάτω %d χρήστες;" % users_n
            message += "\n" + ', '.join([user.name for user in users])
        
        response = dialogs.AskDialog(message).showup()
        if response == Gtk.ResponseType.YES:
            for user in self.get_selected_users():
                self.system.delete_user(user)
            self.repopulate_treeviews()
    
    def on_remove_user_mi_activate(self, widget):
        users = self.get_selected_users()
        groups = self.get_selected_groups()
        users_n = len(users)
        group_names = ', '.join([group.name for group in groups])
        if users_n == 1:
            message = "Θέλετε σίγουρα να αφαιρέσετε τον χρήστη %s από τις επιλεγμένες ομάδες (%s);" % (users[0].name, group_names)
        else:
            message = "Θέλετε σίγουρα να αφαιρέσετε τους παρακάτω %d χρήστες από τις επιλεγμένες ομάδες (%s);" % (users_n, group_names)
            message += "\n" + ', '.join([user.name for user in users])
        
        response = dialogs.AskDialog(message).showup()
        if response == Gtk.ResponseType.YES:
            for user in self.get_selected_users():
                self.system.remove_user_from_groups(user, groups)
            self.repopulate_treeviews()
    
    def on_new_users_mi_activate(self, widget):
        create_users.Create_Users_Dialog()
    
    def on_new_group_mi_activate(self, widget):
        group_form.NewGroupDialog(self.system, self.repopulate_treeviews)
    
    def on_edit_group_mi_activate(self, widget):
        group_form.EditGroupDialog(self.system, self.get_selected_groups()[0], self.repopulate_treeviews)
    
    def on_delete_group_mi_activate(self, widget):
        groups = self.get_selected_groups()
        groups_n = len(groups)
        if groups_n == 1:
            message = "Θέλετε σίγουρα να διαγράψετε την ομάδα %s;" % groups[0].name
        else:
            message = "Θέλετε σίγουρα να διαγράψετε τις παρακάτω %d ομάδες;" % groups_n
            message += "\n" + ', '.join([group.name for group in groups])
        
        response = dialogs.AskDialog(message).showup()
        if response == Gtk.ResponseType.YES:
            for group in self.get_selected_groups():
                self.system.delete_group(group)
            self.repopulate_treeviews()
            
    def on_set_static_ip_activate(self, widget):
        ip_dialog.Ip_Dialog()
    
    def on_publish_ltsp_activate(self, widget):
        subprocess.Popen(['./run-in-terminal', 'ltsp-update-image', '--cleanup', '/'])
    
    def edit_file(self, filename):
        subprocess.Popen(['xdg-open', filename])
        # TODO: Maybe throw an error message if not os.path.isfile(filename)
    
    def on_mi_edit_lts_conf_activate(self, widget):
        self.edit_file('/var/lib/tftpboot/ltsp/i386/lts.conf')
    
    def on_mi_edit_pxelinux_cfg_activate(self, widget):
        self.edit_file('/var/lib/tftpboot/ltsp/i386/pxelinux.cfg/default')
    
    def on_mi_edit_shared_folders_activate(self, widget):
        self.edit_file('/etc/default/shared-folders')
        
    def on_mi_edit_dnsmasq_conf_activate(self, widget):
        self.edit_file('/etc/dnsmasq.d/ltsp-server-dnsmasq.conf')
    
    def on_mi_about_activate(self, widget):
        pass
    
    def run_as_sudo_user(self, cmd):
        NotImplemented #TODO
    
    def open_link(self, link):
        subprocess.Popen(["xdg-open", link])
        #self.run_as_sudo_user('xdg-open ' + link) FIXME: uncomment
    
    def on_mi_lts_conf_manpage_activate(self, widget):
        self.open_link('http://manpages.ubuntu.com/lts.conf')

    def on_mi_forum_activate(self, widget):
        self.open_link('http://alkisg.mysch.gr/steki/index.php?board=67.0')

    def on_mi_irc_activate(self, widget):
        user = os.getenv("USER")
        if user is None:
            user = "sch_scripts_user." # The dot is converted to a random digit
        self.open_link("http://webchat.freenode.net/?nick=" + user + 
            "&channels=ubuntu-gr,ltsp&prompt=1")

    def on_mi_ask_question_activate(self, widget):
        self.open_link('https://answers.launchpad.net/sch-scripts')

    def on_mi_report_bug_activate(self, widget):
        self.open_link('https://bugs.launchpad.net/sch-scripts')

    def on_mi_home_activate(self, widget):
        self.open_link('http://ts.sch.gr/wiki/Linux/LTSP')



# To export a man page:
# help2man -L el -s 8 -o sch-scripts.8 -N ./sch-scripts && man ./sch-scripts.8
def usage():
    print """Χρήση: sch-scripts [ΕΠΙΛΟΓΕΣ]

Παρέχει ένα σύνολο εξαρτήσεων για την αυτοματοποίηση της εγκατάστασης
σχολικών εργαστηρίων και ένα γραφικό περιβάλλον που υποστηρίζει διαχείριση
λογαριασμών χρηστών, δημιουργία εικονικού δίσκου LTSP κ.α.

Πολλά από τα συμπεριλαμβανόμενα βοηθήματα προσανατολίζονται σε LTSP
εγκαταστάσεις, αλλά το πακέτο είναι χρήσιμο και χωρίς LTSP.

Περισσότερες πληροφορίες: http://ts.sch.gr/wiki/Linux/LTSP.

Επιλογές:
    -h, --help     Σελίδα βοήθειας της εφαρμογής.
    -v, --version  Προβολή έκδοσης των sch-scripts.

Αναφορά σφαλμάτων στο https://bugs.launchpad.net/sch-scripts."""


def version():
    print """sch-scripts 12.04
Copyright (C) 2009-2012 Άλκης Γεωργόπουλος <alkisg@gmail.com>, Φώτης Τσάμης <ftsamis@gmail.com>.
Άδεια χρήσης GPLv3+: GNU GPL έκδοσης 3 ή νεότερη <http://gnu.org/licenses/gpl.html>.

Συγγραφή: by Άλκης Γεωργόπουλος <alkisg@gmail.com>, Φώτης Τσάμης <ftsamis@gmail.com>."""

if __name__ == '__main__':
    if len(sys.argv) == 2 and (sys.argv[1] == '-v' or sys.argv[1] == '--version'):
        version()
        sys.exit(0)
    elif len(sys.argv) == 2 and (sys.argv[1] == '-h' or sys.argv[1] == '--help'):
        usage()
        sys.exit(0)
    elif len(sys.argv) >= 2:
        usage()
        sys.exit(1)
    Gui()
    Gtk.main()
