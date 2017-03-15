#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2012 Fotis Tsamis <ftsamis@gmail.com>
# 2013-2014, Lefteris Nikoltsios <lefteris.nikoltsios@gmail.com>
# 2017, Alkis Georgopoulos <alkisg@gmail.com>
# License GNU GPL version 3 or newer <http://gnu.org/licenses/gpl.html>

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import os
import time
from twisted.internet.protocol import Factory
from twisted.internet import gtk3reactor
gtk3reactor.install()
from twisted.internet import reactor
from twisted.protocols.basic import LineReceiver

import common
import config
import dialogs
import user_form

class Registrations(LineReceiver):
    def __init__(self, connections, requests, gui, system, groups, roles):
        self.connections = connections
        self.requests = requests
        self.gui = gui
        self.system = system
        self.groups = groups
        self.roles = roles
        self.state = 'identify'
        self.ip = None
        self.port = None
        self.id_hostname = None
    
    def connectionMade(self):
        self.ip = self.transport.getPeer().host
        self.port = self.transport.getPeer().port
        self.connections.append(self)
        print "New connection from %s:%s" % (self.ip, self.port)
        
    def connectionLost(self, reason):
        print "Connection with %s:%s was closed." % (self.ip, self.port)
        if self in self.connections:
            del self.connections[self.connections.index(self)]
    
    def booltr(self, b):
        if b:
            return "YES"
        return "NO"
    
    def lineReceived(self, line):
        #print line # DEBUGGING
        cmd = line.split(None, 1)
        if len(cmd) > 1:
            cmd, data = cmd
        else:
            cmd = cmd[0]
            data = None
        
        if self.state == 'identify':
            if cmd == 'ID':
                self.identify(data)
            else:
                print "Error: Expected ID command from %s:%s but instead got %s. Closing connection" % (self.ip, self.port, cmd)
                self.transport.loseConnection()
            return
            
        if line == 'BYE':
            print "%s:%s sent BYE." % (self.ip, self.port)
            self.transport.loseConnection()
        elif cmd == "USER_EXISTS":
            self.sendLine(self.booltr(data in self.system.users))
        elif cmd == "REALNAME_REGEX":
            self.sendLine(".+")
        elif cmd == "USER_REGEX":
            self.sendLine(libuser.NAME_REGEX)
        elif cmd == "PASS_REGEX":
            self.sendLine(".+")
        elif cmd == "GET_ROLES":
            self.sendLine(','.join(self.roles))
        elif cmd == "GET_GROUPS":
            self.sendLine(','.join(self.groups))
        elif cmd == "SEND_DATA":
            try:
                data = data.split('\t')
                realname = data[0]
                username = data[1]
                password = data[2]
                role = None
                if self.roles:
                    role = data[3]
                groups = []
                if self.groups:
                    groups = data[4].split(',') if data[4] else []
                
                # Create a new request
                applicant = Applicant(self.ip, self.id_hostname)
                user = libuser.User(username, rname=realname, password=password, groups=groups)
                #print user # DEBUGGING
                req = Request(time.localtime(), applicant, user, role)
                self.gui.add_request(req)
                
                self.requests.append(req)
                self.sendLine("YES")
            except Exception as e:
                print e
                self.sendLine("NO")
                print "Error receiving data."
        else:
            print "Received invalid command %s from %s:%s" % (cmd, self.ip, self.port)
            
    def identify(self, line):
        self.id_hostname = line
        self.state = 'listen'
        self.sendLine("YES")


class RegistrationsFactory(Factory):
    def __init__(self, gui, system, groups, roles):
        self.connections = []
        self.requests = []
        self.gui = gui
        self.system = system
        self.groups = groups
        self.roles = roles

    def buildProtocol(self, addr):
        return Registrations(self.connections, self.requests, self.gui, self.system, self.groups, self.roles)


class Applicant(object):
    def __init__(self, ip, hostname=None):
        self.ip = ip
        self.hostname = hostname
        
    def __str__(self):
        return '%s (%s)' % (self.hostname, self.ip)


class Request(object):
    def __init__(self, time=None, applicant=None, user=None, role=None, status='pending'):
        if time is None:
            time.localtime()
        else:
            self.time = time
        self.applicant = applicant
        self.user = user
        self.role = role
        self.status = status


class UI:
    def __init__(self, system):
        self.system = system
        self.builder = Gtk.Builder()
        self.builder.add_from_file('signup_server.ui')
        self.builder.connect_signals(self)
        self.requests_list = self.builder.get_object('requests_list')
        self.window = self.builder.get_object('requests_window')
        self.reject_tb = self.builder.get_object('reject_tb')
        self.review_tb = self.builder.get_object('review_tb')
        self.selection = self.builder.get_object('treeview-selection')
        self.roles = {i : config.parser.get('Roles', i).replace('$$teachers', self.system.teachers) for i in config.parser.options('Roles')}
        self.window.show()
    
    def strtime(self, t):
        return time.strftime("%d/%m/%Y %T", t)
    
    def user_autocomplete(self, user):
        if user.directory in [None, '']:
            user.directory = os.path.join(libuser.HOME_PREFIX, user.name)
        if user.uid in [None, '']:
            set_uids = [r[0].user.uid for r in self.requests_list]
            user.uid = libuser.system.get_free_uid(exclude=set_uids)
        if user.gid in [None, '']:
            set_gids = [r[0].user.gid for r in self.requests_list]
            user.gid = libuser.system.get_free_gid(exclude=set_gids)
        if user.primary_group in [None, '']:
            user.primary_group = user.name
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
    
    def add_request(self, request):
        #object time applicant realname username role groups
        self.requests_list.append([request, self.strtime(request.time), 
                                   str(request.applicant), request.user.rname,
                                   request.user.name, str(request.role), 
                                   ','.join(request.user.groups)])
        self.user_autocomplete(request.user)
        # Add the role groups to user.groups but don't show them in the treeview
        if request.role in self.roles:
            groups = self.roles[request.role].split(',')
        else:
            groups = []
        for gr in groups:
            if gr and gr not in request.user.groups and gr in libuser.system.groups:
                request.user.groups.append(gr)
        self.builder.get_object('apply_button').set_sensitive(True)
    
    def update_row(self, row, role=None):
        request = row[0]
        if role is not None:
            request.role = role
        data = [request, self.strtime(request.time), 
                str(request.applicant), request.user.rname,
                request.user.name, str(request.role)]
        for i in range(len(data)):
            row[i] = data[i]
        
        if request.role in self.roles:
            role_groups = self.roles[request.role].split(',')
        else:
            role_groups = []
        row[6] = ','.join([g for g in request.user.groups if g and g not in role_groups])
    
    def get_selected_rows(self):
        paths = self.selection.get_selected_rows()[1]
        selected = [self.requests_list[path] for path in paths]
        return selected
    
    def on_treeview_selection_changed(self, widget):
        cnt = widget.count_selected_rows()
        if cnt > 0:
            self.reject_tb.set_sensitive(True)
            if cnt == 1:
                self.review_tb.set_sensitive(True)
            else:
                self.review_tb.set_sensitive(False)
        else:
            self.reject_tb.set_sensitive(False)
            self.review_tb.set_sensitive(False)
    
    def on_reject_tb_clicked(self, widget):
        selected = self.get_selected_rows()
        msg = "Θέλετε σίγουρα να διαγραφούν τα παρακάτω αιτήματα από τη λίστα;\n\n"
        msg += ', '.join([row[4] for row in selected])
        r = dialogs.AskDialog(msg, "Διαγραφή αιτημάτων").showup()
        if r == Gtk.ResponseType.YES:
            for row in selected:
                self.requests_list.remove(row.iter)
            if len(self.requests_list) == 0:
                self.builder.get_object('apply_button').set_sensitive(False)
            
    def on_review_tb_clicked(self, widget):
        row = self.get_selected_rows()[0] # It should always be only one
        request = row[0]
        cb = lambda role: self.update_row(row, role)
        user_form.ReviewUserDialog(self.system, request.user, request.role, cb)
    
    def on_apply_button_clicked(self, widget):
        requests = [row[0] for row in self.requests_list]
        users = [req.user for req in requests]
        usernames = ', '.join([u.name for u in users])
        r=dialogs.AskDialog("Θα δημιουργηθούν οι παρακάτω χρήστες:\n%s\n\nΣυνέχεια;" % usernames, "Δημιουργία χρηστών").showup()
        if r == Gtk.ResponseType.YES:
            for user in users:
                if user.primary_group not in self.system.groups:
                    self.system.add_group(libuser.Group(user.primary_group, user.gid, {}))
                self.system.add_user(user)
                libuser.system.reload()
                # FIXME: sch-scripts trees won't update
                for counter, row in enumerate(self.requests_list):
                    if row[0].user.name == user.name:
                        self.requests_list.remove(self.requests_list.get_iter(counter))
            if len(self.requests_list) == 0:
                self.builder.get_object('apply_button').set_sensitive(False)
    
    def on_close_button_clicked(self, widget):    
        if len(self.requests_list):
            r=dialogs.AskDialog("Θέλετε σίγουρα να τερματίσετε την εφαρμογή αιτήσεων; Όλες οι εκκρεμείς αιτήσεις θα χαθούν.", "Επιβεβαίωση").showup()
            if r == Gtk.ResponseType.YES:
                reactor.stop()
        else:
            reactor.stop()
    
    def on_window_delete_event(self, widget, event):
        reactor.stop()
    

def startServer(system, groups, roles):   
    gui = UI(system)
    reactor.listenTCP(790, RegistrationsFactory(gui, system, groups, roles))
    reactor.run()


class SettingsDialog:
    def __init__(self, system):
        self.system = system
        self.builder = Gtk.Builder()
        self.builder.add_from_file('signup_settings.ui')
        self.builder.connect_signals(self)
        self.dlg = self.builder.get_object('dialog')
        self.groups_list = self.builder.get_object('groups_store')
        self.groups_list.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        self.roles_list = self.builder.get_object('roles_store')
        self.roles_list.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        self.check_all_groups = self.builder.get_object('check_all_groups')
        self.check_all_roles = self.builder.get_object('check_all_roles')
        self.all_groups = self.check_all_groups.get_active()
        self.all_roles = self.check_all_roles.get_active()
        self.populate_roles()
        self.populate_groups()
        self.dlg.run()
        self.dlg.destroy()
   
    def populate_roles(self):
         check_list = config.parser.get('GUI', 'requests_checked_roles').split(',')
         for role in config.parser.options('Roles'):
            check = role in check_list
            self.roles_list.append([check, role])
         self.set_header_checkbutton(self.check_all_roles, self.roles_list)
    
    def populate_groups(self):
        check_list = config.parser.get('GUI', 'requests_checked_groups').split(',')
        for group in self.system.groups.values():
            if group.is_user_group() and not group.is_private():
                check = group.name in check_list
                self.groups_list.append([check, group.name])
        self.set_header_checkbutton(self.check_all_groups, self.groups_list)
    
    def get_selected_roles(self):
        return [r[1] for r in self.roles_list if r[0]]
    
    def get_selected_groups(self):
        return [r[1] for r in self.groups_list if r[0]]
    
    def set_header_checkbutton(self, button, store):
        checked = [r[0] for r in store]
        if False in checked:
            if True in checked:
                button.set_inconsistent(True)
            else:
                button.set_inconsistent(False)
                button.set_active(False)
        else:
            button.set_inconsistent(False)
            button.set_active(True)
    
    def on_role_toggled(self, widget, path):
        selected = not self.roles_list[path][0]
        self.roles_list[path][0] = selected
        self.set_header_checkbutton(self.check_all_roles, self.roles_list)
        
    def on_group_toggled(self, widget, path):
        selected = not self.groups_list[path][0]
        self.groups_list[path][0] = selected
        self.set_header_checkbutton(self.check_all_groups, self.groups_list)
    
    def on_check_all_groups_clicked(self, widget):
        active = self.all_groups
        self.check_all_groups.set_inconsistent(False)
        self.check_all_groups.set_active(not active)
        self.all_groups = not active
        for row in self.groups_list:
            row[0] = not active
    
    def on_check_all_roles_clicked(self, widget):
        active = self.all_roles
        self.check_all_roles.set_inconsistent(False)
        self.check_all_roles.set_active(not active)
        self.all_roles = not active
        for row in self.roles_list:
            row[0] = not active
    
    def on_continue_clicked(self, widget):
        self.dlg.hide()
        config.parser.set('GUI', 'requests_checked_groups', ','.join([r[1] for r in self.groups_list if r[0]]))
        config.parser.set('GUI', 'requests_checked_roles', ','.join([r[1] for r in self.roles_list if r[0]]))
        config.save()
        startServer(self.system, self.get_selected_groups(), self.get_selected_roles())
    
    def on_cancel_clicked(self, widget):
        self.dlg.destroy()

    
if __name__ == '__main__':
    import libuser
    SettingsDialog(libuser.system)
