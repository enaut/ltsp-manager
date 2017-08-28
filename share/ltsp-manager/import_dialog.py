#!/usr/bin/python
#-*- coding: utf-8 -*-
# Copyright (C) 2009-2012 Fotis Tsamis <ftsamis@gmail.com>
# 2009-2017, Alkis Georgopoulos <alkisg@gmail.com>
# 2014, Lefteris Nikoltsios <lefteris.nikoltsios@gmail.com>
# License GNU GPL version 3 or newer <http://gnu.org/licenses/gpl.html>

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk
import os
import re
import sys

import common
import dialogs
import libuser
import user_form

# NOTE: User.plainpw overrides the User.password if it's set
class ImportDialog:
    def __init__(self, new_set):
        self.set = new_set
        # Remove the system users from the set
        for u in self.set.users.values():
            if u.uid is not None and u.is_system_user():
                self.set.remove_user(u)
        
        gladefile = "import_dialog.ui"
        self.builder = Gtk.Builder()
        self.builder.add_from_file(gladefile)
        self.dialog = self.builder.get_object('import_dialog')
        
        dic = {"on_dialog_destroy" : self.Exit,
               "on_apply" : self.Apply,
               "on_auto_resolve" : self.ResolveConflicts,
               "on_delete_users_activate" : self.on_delete_users_activate,
               "on_cancel" : self.Cancel}
        
        self.builder.connect_signals(dic) 
        
        self.tree = self.builder.get_object("users_tree")
        self.apply = self.builder.get_object("apply_button")
        self.resolve = self.builder.get_object("resolve_button")
        self.menu = self.builder.get_object("menu")
        
        self.states = {'ok' : Gtk.STOCK_OK, 'error' : Gtk.STOCK_DIALOG_WARNING}
        self.dialog.show_all()
        self.TreeView()
        self.FillTree(self.set)
    
    def TreeView(self):        
        """Make the liststore, the first 20 cells refers to users values,
        the second 20 cells refers to color foreach of first 20 cells, the
        third 20 cells refers to conflicts and the last cell refers to first
        column image.
        """
        types = [str, int, int, str, str, str, str, str, str, str, str, str, 
                                       int, int, int, int, int, int, str, str]
        types.extend([str]*41)
        
        self.list = Gtk.ListStore(*types)
        self.tree.set_model(self.list)
        
        self.tree.connect("button_press_event", self.Click)
        self.tree.connect("key_press_event", self.Delete)
        self.tree.set_has_tooltip(True)
        self.tree.connect("query-tooltip", self.Tooltip)
        self.tree.set_rubber_banding(True)
        
        # Make the columns in the preview treeview
        # First of all append the icon
        col_pixbuf = Gtk.TreeViewColumn(_("Status"), Gtk.CellRendererPixbuf(), stock_id=60)
        col_pixbuf.set_resizable(True)
        col_pixbuf.set_sort_column_id(60)
        self.tree.append_column(col_pixbuf)
        
        for (counter, header) in enumerate(libuser.CSV_USER_FIELDS):
            text_rend = Gtk.CellRendererText()
            text_rend.connect("edited", self.EditedText, self.list, counter)
            col = Gtk.TreeViewColumn(header, text_rend, text=counter, 
                                     foreground=counter+20, editable=True)
            col.set_resizable(True)
            col.set_sort_column_id(counter) 
            self.tree.append_column(col)
        self.tree.get_column(19).set_visible(False)
    
    def FillTree(self, new_set):
        """Fill the preview popup dialog with new users."""
        for u in new_set.users.values():
            self.AutoComplete(u)
            data = [u.name, u.uid, u.gid, u.primary_group, u.rname, u.office, 
                    u.wphone, u.hphone, u.other, u.directory, u.shell, 
                    ",".join(u.groups), u.lstchg, u.min, u.max, u.warn, 
                    u.inact, u.expire, u.password, u.plainpw]
            # Fill the cells with default values
            for i in range(20):    
                data.append("black") # cell's foreground color
            for i in range(20):
                data.append('') # cell's problem or ''
            data.append(self.states['ok']) # row's status
            row = self.list[self.list.append(data)]
            self.SetRowFromObject(row)
        self.DetectConflicts()
        self.CheckIdenticalUsers()
    
    def SetRowFromObject(self, row):
        u = self.set.users[row[0]]
        data = [u.name, u.uid, u.gid, u.primary_group, u.rname, u.office, 
                    u.wphone, u.hphone, u.other, u.directory, u.shell, 
                    ",".join(u.groups), u.lstchg, u.min, u.max, u.warn, 
                    u.inact, u.expire, u.password, u.plainpw]
        for i in range(len(data)):
            row[i] = data[i]
    
    def CheckIdenticalUsers(self, other=libuser.system):
        """Check if there are users in the list that are identical to 
        a user in the system and ask for removal."""
        attrs = ['name', 'uid', 'gid', 'primary_group', 'rname', 'office',
                 'wphone', 'hphone', 'other', 'directory', 'shell', 'min',
                 'max', 'warn', 'inact', 'expire', 'password']
        
        identical = []
        for row in self.list:
            name = row[0]
            u_new = self.set.users[name]
            if name in other.users:
                u_old = other.users[name]
                same = True
                for attr in attrs:
                    if u_new.__dict__[attr] != u_old.__dict__[attr]:
                        same = False
                        break
                if set(u_new.groups+[u_new.primary_group]) != set(u_old.groups):
                    same = False
                if same:
                    identical.append(row.iter)
        if not identical:
            return
        msg = _("The following %s user accounts already exist on the system, with identical information.") 
        msg += "\n\n%s\n\n"
        msg += _("Would you like to remove those accounts from the list, to avoid trying to create them again?")
        msg = msg % (len(identical), ', '.join(self.list[iter_][0] for iter_ in identical))
        resp = dialogs.AskDialog(msg, _("Identical existing accounts were found")).showup()
        if resp == Gtk.ResponseType.YES:
            for iter_ in identical:
                self.RemoveRow(iter_)
            self.DetectConflicts()
        
    
    def AutoComplete(self, user): # TODO: Maybe move me to libuser?
        """Fills the missing information of user, where possible."""
        #TODO: Complete the username from real name, this can't be done now
        # since we are using a dict to store users with username as a key
        #  - Needs design change -
        
        if user.directory in [None, '']:
            user.directory = os.path.join(libuser.HOME_PREFIX, user.name)
        if user.uid in [None, '']:
            set_uids = [user.uid for u in self.set.users.values()]
            user.uid = libuser.system.get_free_uid(exclude=set_uids)
        
        set_gids = [u.gid for u in self.set.users.values()]
        sys_gids = {g.gid : g for g in self.set.groups.values()}
        if user.gid in [None, '']:
            if user.primary_group in [None, '']:
                user.primary_group = user.name
            if user.name in libuser.system.groups:
                user.gid = libuser.system.groups[user.name].gid
            else:
                user.gid = libuser.system.get_free_gid(exclude=set_gids)
        else:
            if user.primary_group in [None, '']:
                if user.gid in sys_gids:
                    user.primary_group = sys_gids[user.gid].name
                else:
                    user.primary_group = user.name
        if user.primary_group in [None, '']:
            allgroups = self.set.groups.values()[:]
            allgroups.extend(libuser.system.groups.values())
            for gr_obj in allgroups:
                if gr_obj.gid == user.gid:
                    user.primary_group = gr_obj.name
                    break
        if user.shell in [None, '']:
            user.shell = '/bin/bash'
        if user.min in [None, '']:
            user.min = 0
        if user.max in [None, '']:
            user.max = 99999
        if user.warn in [None, '']:
            user.warn = 7
        if user.lstchg in [None, '']:
            user.lstchg = common.days_since_epoch()
        if user.inact in [None, '']:
            user.inact = -1
        if user.expire in [None, '']:
            user.expire = -1
        if user.password in [None, '']:
            user.password = '!'
        if user.plainpw is None:
            user.plainpw = ''
    
    def SetRowProps(self, row, col, prob, color=None, state=None):
        row[col+40] = prob
        if color:
            row[col+20] = color
        else:
            if prob == '':
                row[col+20] = 'black'
            else:
                row[col+20] = 'red'
        if state:
            row[60] = self.states[state]
        else:
            if prob == '':
                other = False
                for i in range(20, 40): # Check if there are other problems to set the proper icon
                    if row[i] == 'red':
                        other = True
                        break
                if other:
                    row[60] = self.states['error']
                else:
                    row[60] = self.states['ok']
            else:
                row[60] = self.states['error']
    
    def DetectConflicts(self):
        """Detects and marks the conflicts in the treeview based on the user
        object.
        
        Here we don't check for conflicts with secondary groups as they are
        easily resolvable.
        """
        # All the system users
        sys_users = {'uids' : [], 'gids' : [], 'dirs' : []}
        sys_users['uids'] = [user.uid for user in libuser.system.users.values()]
        sys_users['gids'] = [user.gid for user in libuser.system.users.values()]
        sys_users['dirs'] = [user.directory for user in libuser.system.users.values()]
        # All the users in the new Set
        new_users = {'uids' : [], 'gids' : [], 'dirs' : []}
        new_users['uids'] = [user.uid for user in self.set.users.values()]
        new_users['gids'] = [user.gid for user in self.set.users.values()]
        new_users['dirs'] = [user.directory for user in self.set.users.values()]
        
        passed_users = {'names' : [], 'uids' : [], 'gids' : [], 'dirs' : []}
        errors_found = False
        for row in self.list:
            u = self.set.users[row[0]]
            # Clear the currently marked conflicts, if any
            for cell in range(0, 20):
                self.SetRowProps(row, cell, '')
            
            # FIXME: Possibly not an issue, but problems with system users
            # will override problems with new users.
            # Illegal input problems will *not* be overriden.
            
            # 'char' : Illegal inputted characters/regexp mismatch
            # 'dup' : duplicate (only about the new users)
            # 'con' : conflict (like duplicate but for existing/system users)
            # 'hijack' : special case where the home exists, is not used by a
            #            system user, but its uid:gid pair is different from the
            #            new user's one.
            
            
            # Illegal input checking #FIXME: This should be in a separate function
                                     #and (for later): executed only once, since
                                     #the edit dialog won't allow illegal input
            def invalidate(n):
                self.SetRowProps(row, n, 'char')
            if not libuser.system.name_is_valid(u.name):
                invalidate(0)
            if not libuser.system.uid_is_valid(u.uid):
                invalidate(1)
            if not libuser.system.gid_is_valid(u.gid):
                invalidate(2)
            if not libuser.system.name_is_valid(u.primary_group):
                invalidate(3)
            if not libuser.system.gecos_is_valid(u.rname):
                invalidate(4)
            if not libuser.system.gecos_is_valid(u.office):
                invalidate(5)
            if not libuser.system.gecos_is_valid(u.wphone):
                invalidate(6)
            if not libuser.system.gecos_is_valid(u.hphone):
                invalidate(7)
            if not libuser.system.gecos_is_valid(u.other):
                invalidate(8)
            # Not checking homedir validity
            if not libuser.system.shell_is_valid(u.shell):
                invalidate(10)
            for group in u.groups:
                if not libuser.system.name_is_valid(group):
                    invalidate(11)
                    break
            chage = [u.lstchg, u.min, u.max, u.warn, u.inact, u.expire]
            for n, attr in enumerate(chage, 12):
                if attr > 2147483647 or attr < -1:
                    invalidate(n)
            
            # Duplicate checking (New users)
            if u.name in passed_users['names']:
                self.SetRowProps(row, 0, 'dup')
            if u.uid in passed_users['uids']:
                self.SetRowProps(row, 1, 'dup')
            #if u.gid in passed_users['gids']: # We don't care for > 1 users having the same primary group
            #    self.SetRowProps(row, 2, 'dup')
            if u.directory in passed_users['dirs']:
                self.SetRowProps(row, 9, 'dup')
            
            # Conflict checking (Existing system users)
            if u.name in libuser.system.users:
                self.SetRowProps(row, 0, 'con')
            if u.uid in sys_users['uids']:
                self.SetRowProps(row, 1, 'con')
            # Check if the given GID belongs to the given group name
            if u.primary_group in libuser.system.groups:
                should_be = libuser.system.groups[u.primary_group].gid
                if u.gid != should_be:
                    self.SetRowProps(row, 2, 'mismatch %s' % should_be)
            else:
                if u.gid in sys_users['gids']:
                    should_be = None
                    for g in libuser.system.groups.values():
                        if u.gid == g.gid:
                            should_be = g.name
                            break
                    if should_be != u.primary_group:
                        self.SetRowProps(row, 3, 'mismatch %s' % should_be)
            #if u.gid in sys_users['gids']: # We don't care for > 1 users having the same primary group
            #    self.SetRowProps(row, 2, 'con')
            if u.directory in sys_users['dirs']:
                self.SetRowProps(row, 9, 'con')
            else:
                # Special case, we want to use existing home dirs if they are not already used.
                if os.path.isdir(u.directory) and u.directory not in sys_users['dirs']: 
                    # See if the home and the uid:gid of the user are different
                    #print "Homedir for user %s exists in the FS." % u.name # XXX: Debug
                    dir_stat = os.stat(u.directory)
                    if u.uid != int(dir_stat.st_uid):
                        self.SetRowProps(row, 1, 'hijack')
                        self.SetRowProps(row, 9, 'hijack')
                    if u.gid != dir_stat.st_gid:
                        self.SetRowProps(row, 2, 'hijack')
                        self.SetRowProps(row, 9, 'hijack')
                    #print "\tUser: - %s:%s -" % (u.uid, u.gid) # XXX: Debug
                    #print "\tDir : - %s:%s -" % (dir_stat.st_uid, dir_stat.st_gid) # XXX: Debug
            
            passed_users['names'].append(u.name)
            passed_users['uids'].append(u.uid)
            passed_users['gids'].append(u.gid)
            passed_users['dirs'].append(u.directory)
            
            if row[60] == self.states['error']:
                errors_found = True
        
        self.apply.set_sensitive(not errors_found)
    
    def ResolveConflicts(self, widget=None):
        # All the system users
        sys_users = {'uids' : [], 'gids' : [], 'dirs' : []}
        sys_users['uids'] = [user.uid for user in libuser.system.users.values()]
        sys_users['gids'] = [user.gid for user in libuser.system.users.values()]
        sys_users['dirs'] = [user.directory for user in libuser.system.users.values()]
        # All the users in the new Set
        new_users = {'uids' : [], 'gids' : [], 'dirs' : []}
        new_users['uids'] = [user.uid for user in self.set.users.values()]
        new_users['gids'] = [user.gid for user in self.set.users.values()]
        new_users['dirs'] = [user.directory for user in self.set.users.values()]
        
        log = []
        def log_msg(txt):
            log.append(txt)
            return txt
        def log_uid(u, f, t):
            return log_msg(_("The UID of user \"%(user)s\" was changed from %(old)s to %(new)s.") % {"user":u, "old":f, "new":t})
        def log_gid(u, f, t):
            return log_msg(_("The GID of user \"%(user)s\" was changed from %(old)s to %(new)s.") % {"user":u, "old":f, "new":t})
        def log_home(u, f, t):
            return log_msg(_("The home directory of user \"%(user)s\" was changed from %(old)s to %(new)s.") % {"user":u, "old":f, "new":t})
        def log_group(u, f, t):
            return log_msg(_("The primary group name of user \"%(user)s\" was changed from %(old)s to %(new)s.") % {"user":u, "old":f, "new":t})
        
        for row in self.list:
            if row[60] != self.states['error']:
                continue
            u = self.set.users[row[0]]
            ofs = 40
            
            if row[1+ofs] in ['dup', 'con']:
                new_uid = libuser.system.get_free_uid(exclude=new_users['uids'])
                new_users['uids'].append(new_uid)
                log_uid(u.name, u.uid, new_uid)
                u.uid = new_uid
                self.SetRowProps(row, 1, '')
                
            elif row[1+ofs] == 'hijack':
                dir_uid = os.stat(u.directory).st_uid
                new_users['uids'].append(dir_uid)
                log_uid(u.name, u.uid, dir_uid)
                u.uid = dir_uid
                self.SetRowProps(row, 1, '')
                
            #if row[2+ofs] in ['dup', 'con']:
            #    new_gid = libuser.system.get_free_gid(exclude=new_users['gids'])
            #    new_users['gids'].append(new_gid)
            #    log_gid(u.name, u.gid, new_gid)
            #    u.uid = new_uid
            #    self.SetRowProps(row, 2, '')
            
            if 'mismatch' in row[2+ofs]:
                new_gid = int(row[2+ofs].split()[1])
                new_users['gids'].append(new_gid)
                log_gid(u.name, u.gid, new_gid)
                if u.primary_group in self.set.groups:
                    self.set.groups[u.primary_group].gid = new_gid
                u.gid = new_gid
                self.SetRowProps(row, 2, '')
                
            if row[2+ofs] == 'hijack':
                dir_gid = os.stat(u.directory).st_gid
                new_users['gids'].append(dir_gid)
                log_gid(u.name, u.gid, dir_gid)
                u.gid = dir_gid
                self.SetRowProps(row, 2, '')
                
            if 'mismatch' in row[3+ofs]:
                new_gname = row[3+ofs].split()[1]
                log_group(u.name, u.primary_group, new_gname)
                if new_gname in self.set.groups:
                    if u.name not in self.set.groups[new_gname].members:
                        self.set.groups[new_gname].members[u.name] = u
                else:
                    self.set.groups[new_gname] = libuser.Group(new_gname, u.gid)
                    self.set.groups[new_gname].members[u.name] = u
                if u.primary_group in self.set.groups:
                    if self.set.groups[u.primary_group].members.keys() == [u.name]:
                        del self.set.groups[u.primary_group]
                    else:
                        del self.set.groups[u.primary_group].members[u.name]
                u.primary_group = new_gname
                self.SetRowProps(row, 3, '')
            self.SetRowFromObject(row)
        
        num = len(log)
        if num > 0:
            log_dlg = self.builder.get_object('log_dialog')
            buf = self.builder.get_object('logbuffer')
            buf.set_text('\n'.join(log))
            log_dlg.run()
            log_dlg.hide()
            self.DetectConflicts()
        else:
            dialogs.WarningDialog(_("Some issues remain that could not be resolved automatically")).showup()
    
    def Edit(self, widget, user):
        form = user_form.ReviewUserDialog(libuser.system, user, role='')
        form.dialog.set_transient_for(self.dialog)
        form.dialog.set_modal(True)
    
    def Apply(self, widget):
        text = _("Create the following users?")
        response = dialogs.AskDialog(text, "Confirm").showup()
        if response == Gtk.ResponseType.YES:
            new_groups = {}
            new_gids = [u.gid for u in self.set.users.values()]
            sys_gids = [g.gid for g in libuser.system.groups.values()]
            for u in self.set.users.values():
                if u.primary_group not in libuser.system.groups:
                   if u.primary_group not in new_groups:
                        g_obj = libuser.Group(u.primary_group, u.gid)
                        new_groups[u.primary_group] = g_obj
                   new_groups[u.primary_group].members[u.name] = u
            
            for u in self.set.users.values():
                for g in u.groups:
                    if g not in libuser.system.groups:
                        if g not in new_groups:
                            g_obj = libuser.Group(g)
                            if g in self.set.groups:
                                g_obj.gid = self.set.groups[g].gid
                            if g_obj.gid in new_gids+sys_gids or g_obj.gid is None:
                                g_obj.gid = libuser.system.get_free_gid(exclude=new_gids)
                                new_gids.append(g_obj.gid)
                            new_groups[g] = g_obj
                        new_groups[g].members[u.name] = u
            
            for gr in new_groups.values():
                gr_tmp = libuser.Group(gr.name, gr.gid)
                libuser.system.add_group(gr_tmp)
            for u in self.set.users.values():
                libuser.system.add_user(u)
            for gr in new_groups.values():
                for u in gr.members.values():
                    libuser.system.add_user_to_groups(u, [gr])
            
        else:
            return False
            
        
        parent = ((widget.get_parent()).get_parent()).get_parent()
        parent.destroy()


    def Cancel(self, widget):
        parent = ((widget.get_parent()).get_parent()).get_parent()
        parent.destroy()

    def Exit(self, widget, event):
        widget.destroy()
    
    def Tooltip(self, widget, x, y, keyboard_tip, tooltip):
        if not widget.get_tooltip_context(x, y, keyboard_tip):
            return False
        else:
            keyboard_mode, cellx, celly, model, path, iter = widget.get_tooltip_context(x, y, keyboard_tip)
            row_info = widget.get_path_at_pos(int(cellx), int(celly))
            if row_info is not None:
                col = row_info[1]
                
                if model[path][0+40] == "con" and col.get_title() == _("Username"):
                    tooltip.set_text(_("This username already exists in the system"))
                elif model[path][0+40] == "char" and col.get_title() == "Username":                    
                    tooltip.set_text(_("This is not a valid username"))
                elif model[path][1+40] == "con" and col.get_title() == "UID":
                    tooltip.set_text(_("This UID already exists in the system"))
                elif model[path][1+40] == "dup" and col.get_title() == "UID":
                    tooltip.set_text(_("This UID already exists in this list"))
                elif model[path][1+40] == "hijack" and col.get_title() == "UID":
                    tooltip.set_text(_("This UID does not match the home directory UID"))
                elif model[path][2+40] == "hijack" and col.get_title() == "UID":
                    tooltip.set_text(_("This GID does not match the home directory GID"))
                elif model[path][9+40] == "con" and col.get_title() == "Directory":
                    tooltip.set_text(_("This directory is in use by another user in the system"))
                elif model[path][9+40] == "dup" and col.get_title() == "Directory":
                    tooltip.set_text(_("This directory is in use by another user in the list"))
                elif model[path][9+40] == "hijack" and col.get_title() == "Directory":
                    tooltip.set_text(_("This directory already exists in the system but with a different UID/GID"))
                elif 'mismatch' in model[path][2+40] and col.get_title() == "GID":
                    tooltip.set_text(_("This GID does not belong to the group %s") % model[path][3])
                elif 'mismatch' in model[path][3+40] and col.get_title() == "Primary group":
                    tooltip.set_text(_("The GID for this group is not %s") % model[path][2])
                else:
                    return
                
                widget.set_tooltip_cell(tooltip, path, col, None)
                return True
                     
    def Click(self, treeview, event):
        '''if event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
            selection = treeview.get_selection()
            model, paths = selection.get_selected_rows()
            if len(paths) > 0:
                user = self.set.users[model[paths[0]][0]]
                self.Edit(None, user)''' # TODO: Uncomment me when the Dialog editing can be done
        if event.button == 3 and event.type == Gdk.EventType.BUTTON_PRESS:
            selection = treeview.get_selection()
            model, paths = selection.get_selected_rows()
            if len(paths) > 0:
                self.menu.popup(None, None, None, None, event.button, event.time)
                return True
    
    def on_delete_users_activate(self, widget):
        selection = self.tree.get_selection() 
        model, paths = selection.get_selected_rows()
        iters = [model.get_iter(path) for path in paths]
        for i in iters:
            self.RemoveRow(i)
        self.DetectConflicts()
    
    def EditedText(self, cell, path, new_text, model, col):
        username = model[path][0]
        u = self.set.users[username]
        int_columns = [1,2,12,13,14,15,16,17]
        attrs = ['name', 'uid', 'gid', 'primary_group', 'rname', 'office',
                 'wphone', 'hphone', 'other', 'directory', 'shell', 'groups',
                 'lstchg', 'min', 'max', 'warn', 'inact', 'expire', 'password',
                 'plainpw']
        if col in int_columns:
            try:
                u.__dict__[attrs[col]] = int(new_text)
            except ValueError:
                return
        else:
            if col == 0:
                if new_text in self.set.users:
                    return
                u.name = new_text
                u.directory = '/home/%s' % new_text
                self.set.users[new_text] = self.set.users.pop(username)
                model[path][0] = u.name
            elif col == 11:
                u.groups = new_text.strip().split(',')
            elif col == 19:
                # Set user.password from plainpw
                u.plainpw = new_text
                u.password = libuser.system.encrypt(u.plainpw)
            else:
                u.__dict__[attrs[col]] = new_text
        self.SetRowFromObject(model[path])
        self.DetectConflicts()
        
    def Delete(self, treeview, event):
        if Gdk.keyval_name(event.keyval) == "Delete":
            selection = treeview.get_selection() 
            model, paths = selection.get_selected_rows()
            iters = [model.get_iter(path) for path in paths]
            for i in iters:
                self.RemoveRow(i)
            self.DetectConflicts()

    def RemoveRow(self, iter_):
        username = self.list[iter_][0]
        self.list.remove(iter_)
        self.set.remove_user(self.set.users[username])

if __name__ == "__main__":
    interface = ImportDialog()
    Gtk.main()
