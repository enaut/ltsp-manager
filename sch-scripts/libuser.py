#-*- coding: utf-8 -*-
import pwd
import spwd
import grp
import operator
import csv
import subprocess
import re
import crypt
import random
import common

FIRST_SYSTEM_UID=0
LAST_SYSTEM_UID=999

FIRST_SYSTEM_GID=0
LAST_SYSTEM_GID=999

FIRST_UID=1000
LAST_UID=29999

FIRST_GID=1000
LAST_GID=29999
NAME_REGEX = "^[a-z][-a-z0-9_]*$"
HOME_PREFIX = "/home"

USER_FIELDS = ['UID', 'Όνομα χρήστη', 'Κύρια ομάδα', 'Ονοματεπώνυμο', 'Γραφείο', 
'Τηλ. γραφείου', 'Τηλ. οικίας', 'Άλλο', 'Κατάλογος', 'Κέλυφος', 'Ομάδες',
'Τελευταία αλλαγή κωδικού', 'Ελάχιστη διάρκεια', 'Μέγιστη διάρκεια', 'Προειδοποίηση', 'Ανενεργός', 'Λήξη']
CSV_USER_FIELDS = USER_FIELDS
CSV_USER_FIELDS.extend(['Κρυπτογραφημένος κωδικός', 'Κωδικός'])

class User:
    def __init__(self, name=None, uid=None, gid=None, rname="", office="", wphone="",
                 hphone="", other="", directory=None, shell="/bin/bash", groups=None, lstchg=None,
                 min=0, max=99999, warn=7, inact=-1, expire=-1, password="*", plainpw=None):

        self.name, self.uid, self.gid, self.rname, self.office, self.wphone, self.hphone,\
        self.other, self.directory, self.shell, self.groups, self.lstchg, self.min, self.max, self.warn, \
        self.inact, self.expire, self.password, self.plainpw = name, uid, gid, rname, \
        office, wphone, hphone, other, directory, shell, groups, lstchg, min, max, warn, inact, \
        expire, password, plainpw
        
        if not self.name and self.rname:
            self.name = common.greek_to_latin(rname)
        
        if self.groups is None:
            self.groups = []
            
        if self.gid is not None:
            self.primary_group = grp.getgrgid(self.gid).gr_name
        else:
            self.primary_group = None
            
    def is_system_user(self):
        return not (self.uid >= FIRST_UID and self.uid <= LAST_UID)

class Group:
    def __init__(self, name=None, gid=None, members=None, password=""):
        self.name, self.gid, self.members, self.password = \
            name, gid, members, password
        
        if self.members is None:
            self.members = {}
    
    def is_user_group(self):
        return self.gid >= FIRST_GID and self.gid <= LAST_GID
            
    def is_private(self):
        # A UPG has the same name as the user for which it was created
        # and that user is the only member of the UPG.
        return self.is_user_group() and self.name in self.members and len(self.members) == 1
    

class System:
    def __init__(self):
        self.users = {}
        self.groups = {}     
        self.load()
    
    # Group operations
    def add_group(self, group):
        common.run_command(['groupadd', '-g', str(group.gid), group.name])
        for user in group.members.values():
            common.run_command(['usermod', '-a', '-G', group.name, user.name])
    
    def edit_group(self, groupname, group):
        common.run_command(['groupmod', '-g', str(group.gid), '-n', group.name, groupname])
        for user in group.members.values():
            common.run_command(['usermod', '-a', '-G', group.name, user.name])
    
    def delete_group(self, group):
        common.run_command(['groupdel', group.name])
        
    # User operations
    def add_user(self, user, create_home=True):
        cmd = ["useradd"]
        if create_home:
            cmd.extend(['-m', '-d', user.directory])
        cmd.extend(['-g', str(user.gid)])
        cmd.append(user.name)
        common.run_command(cmd)
        self.update_user(user.name, user)
        
    def _strcnv(self, t):
        return [str(i) for i in t]
    
    def update_user(self, username, user):
        # Main values
        cmd = ['usermod']
        cmd.extend(['-d', user.directory])
        cmd.extend(['-g', user.gid])
        cmd.extend(['-G', ','.join(user.groups)])
        cmd.extend(['-l', user.name])
        if user.password is not None:
            cmd.extend(['-p', user.password])
        cmd.extend(['-s', user.shell])
        cmd.extend(['-u', user.uid])
        cmd.append(username)
        
        # Execute usermod
        cmd = self._strcnv(cmd)
        common.run_command(cmd)
        self.user_set_gecos(user)
        self.user_set_pass_options(user)
    
    def user_set_gecos(self, user):
        cmd = ['chfn']
        cmd.extend(['-f', user.rname])
        cmd.extend(['-r', user.office])
        cmd.extend(['-w', user.wphone])
        cmd.extend(['-h', user.hphone])
        cmd.extend(['-o', user.other])
        cmd.append(user.name)
        #Execute chfn
        cmd = self._strcnv(cmd)
        common.run_command(cmd)
    
    def user_set_pass_options(self, user):
        cmd = ['chage']
        cmd.extend(['-d', user.lstchg])
        cmd.extend(['-E', user.expire])
        cmd.extend(['-I', user.inact])
        cmd.extend(['-m', user.min])
        cmd.extend(['-M', user.max])
        cmd.extend(['-W', user.warn])
        cmd.append(user.name)
        # Execute chage
        cmd = self._strcnv(cmd)
        common.run_command(cmd)
    
    def delete_user(self, user):
        common.run_command(['userdel', user.name])
    
    def add_user_to_groups(self, user, groups):
        groups = [gr.name for gr in groups]
        common.run_command(['usermod', '-a', '-G', groups, user.name])
    
    def remove_user_from_groups(self, user, groups):
        groups = [gr.name for gr in groups]
        new_groups = [group for group in user.groups if group not in groups]
        new_groups_str = ','.join(new_groups)
        common.run_command(['usermod', '-G', new_groups_str, user.name])
    
    def lock_user(self, user):
        common.run_command(['usermod', '-L', user.name])
    
    def unlock_user(self, user):
        common.run_command(['usermod', '-U', user.name])
        
    def user_is_locked(self, user):
        return user.password is None or user.password[0] in "!*"
        
    # Generic operations
    def load(self):
        pwds = pwd.getpwall()
        spwds = spwd.getspall()
        sn = {}
        for s in spwds:
            sn[s.sp_nam] = s

        for p in pwds:
            if p.pw_name in sn:
                s = sn[p.pw_name]
            else:
                s = spwd.struct_spwd([None]*9)
            rname, office, wphone, hphone, other = (p.pw_gecos + ",,,,").split(",")[:5]
            u = User(p.pw_name, p.pw_uid, p.pw_gid, rname, office, wphone, hphone,
                other, p.pw_dir, p.pw_shell, [grp.getgrgid(p.pw_gid).gr_name], s.sp_lstchg, s.sp_min, s.sp_max, s.sp_warn, 
                s.sp_inact, s.sp_expire, s.sp_pwd)
            self.users[u.name] = u

        groups = grp.getgrall()
        for group in groups:
            g = Group(group.gr_name, group.gr_gid)
            for member in group.gr_mem:
                if member in self.users:
                    ugroups = self.users[member].groups
                    if group.gr_name not in ugroups:
                        self.users[member].groups.append(group.gr_name)
                    g.members[member] = self.users[member]
            
            self.groups[group.gr_name] = g
        
        for user in self.users.values():
            primary_group = grp.getgrgid(user.gid).gr_name
            if primary_group in self.groups:
                self.groups[primary_group].members[user.name] = user
    
    def reload(self):
        self.users = {}
        self.groups = {}
        self.load()
            
    def get_valid_shells(self):
        try:
            f = open("/etc/shells")
            shells = [line.strip() for line in f.readlines() if line.strip()[0] != '#']
            f.close()
        except:
            shells = []
        
        return shells
    
    def uid_is_valid(self, uid):
        return uid >= FIRST_SYSTEM_UID and uid <= LAST_UID
    
    def gid_is_valid(self, gid):
        return gid >= FIRST_SYSTEM_GID and gid <= LAST_GID
    
    def uid_is_free(self, uid):
        return self.uid_is_valid(uid) and uid not in [user.uid for user in self.users.values()]
    
    def gid_is_free(self, gid):
        return self.gid_is_valid(gid) and gid not in [group.gid for group in self.groups.values()]
    
    def get_free_uids(self, starting=FIRST_UID, ending=LAST_UID):
        used_uids = [user.uid for user in self.users.values()]
        
        free_uids = range(FIRST_UID, LAST_UID+1)
        for uid in used_uids:
            free_uids.remove(uid)
        
        return free_uids
    
    def get_free_uid(self, start=FIRST_UID, end=LAST_UID, reverse=False, ignore=None):
        used_uids = [user.uid for user in self.users.values()]
        
        xr = xrange(start, end+1)
        if reverse:
            xr = reversed(xr)
        
        uid = None
        
        for i in xr:
            if i == ignore or i not in used_uids:
                uid = i
                break
        return uid
    
    def get_free_gid(self, start=FIRST_UID, end=LAST_UID, reverse=False, ignore=None):
        used_gids = [group.gid for group in self.groups.values()]
        
        xr = xrange(start, end+1)
        if reverse:
            xr = reversed(xr)
        
        gid = None
        
        for i in xr:
            if i == ignore or i not in used_gids:
                gid = i
                break
        return gid
    
    def is_valid_name(self, name):
        return re.match(NAME_REGEX, name)
    
    def is_valid_gecos(self, string):
        return ':' not in string
        
    def encrypt(self, plainpw):
        """
        Converts a plain text password to a sha-512 encrypted one.
        """
        alphabet='0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        salt=''.join([ random.choice(alphabet) for i in range(8) ])

        return crypt.crypt(plainpw, "$6$%s$" % salt)

class CSV:
    def __init__(self):
        self.fields_map = {'Όνομα χρήστη': 'name', 'Τελευταία αλλαγή κωδικού': 'lstchg', 'Κύρια ομάδα': 'gid', 'Κέλυφος': 'shell', 'UID': 'uid', 'Γραφείο': 'office', 'Κρυπτογραφημένος κωδικός': 'password', 'Κωδικός': 'plainpw', 'Λήξη': 'expire', 'Μέγιστη διάρκεια': 'max', 'Προειδοποίηση': 'warn', 'Κατάλογος': 'directory', 'Ελάχιστη διάρκεια': 'min', 'Άλλο': 'other', 'Ομάδες': 'groups', 'Τηλ. γραφείου': 'wphone', 'Ανενεργός': 'inact', 'Ονοματεπώνυμο': 'rname', 'Τηλ. οικίας': 'hphone'}
    
    def parse(self, fname):
        users_dict = csv.DictReader(open(fname))
        users = {}
        groups = {}
        for user_d in users_dict:
            user = User()
            
            for key, value in user_d.iteritems():
                try:
                    user.__dict__[self.fields_map[key]] = value
                except:
                    pass
            
            if user.name:
                users[user.name] = user
                for g in user.groups.split(','):
                    try:
                        gname, gid = g.split(':')
                    except:
                        gname = g
                        gid = None
                    user.groups.append(gname)
                    
                    # Create Group instances from memberships
                    if gname not in groups:
                        groups[gname] = Group(gname, gid)
                    groups[gname].members.append(user)
                        
                if user.groups == '':
                    user.groups = None
        
        return (users, groups)
            

    def write(self, fname, system, users):
        f = open(fname, 'w')
        writer = csv.DictWriter(f, fieldnames=CSV_USER_FIELDS)
        writer.writerow(dict((n,n) for n in CSV_USER_FIELDS))
        for user in users:
            u_dict = dict( (key, user.__dict__[o_key] if user.__dict__[o_key] is not None else '') for key, o_key in self.fields_map.iteritems())
            u_dict['Κωδικός'] = '' # We don't have the plain password
            u_dict['Ομάδες'] = list(u_dict['Ομάδες'])
            # Convert the groups value to a proper gname:gid pairs format string
            final_groups = u_dict['Ομάδες']
            for i, gname in enumerate(final_groups):
                gid = system.groups[gname].gid
                final_groups[i] = ':'.join((final_groups[i], str(gid)))
            u_dict['Ομάδες'] = ','.join(final_groups)
            
            writer.writerow(u_dict)
        f.close()
    
    

if __name__ == '__main__':
    system = System()
    print "System users:", ', '.join(system.users)
    print "\nSystem groups:", ', '.join(system.groups)
    
    def analytical():
        print "System users:"
        for user in system.users.values():
            print " ", user.name
            print "   ", ", ".join(user.groups)
        print "\nSystem groups:"
        for group in system.groups.values():
            print " ", group.name
            print "   ", ", ".join(group.members.keys())
    
    analytical()
