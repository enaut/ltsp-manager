# -*- coding: utf-8 -*-

import csv
import libuser

FIELDS_MAP = {'Όνομα χρήστη': 'name', 'Τελευταία αλλαγή κωδικού': 'lstchg', 'Κύρια ομάδα': 'gid', 'Όνομα κύριας ομάδας' : 'primary_group', 'Κέλυφος': 'shell', 'UID': 'uid', 'Γραφείο': 'office', 'Κρυπτογραφημένος κωδικός': 'password', 'Κωδικός': 'plainpw', 'Λήξη': 'expire', 'Μέγιστη διάρκεια': 'max', 'Προειδοποίηση': 'warn', 'Κατάλογος': 'directory', 'Ελάχιστη διάρκεια': 'min', 'Άλλο': 'other', 'Ομάδες': 'groups', 'Τηλ. γραφείου': 'wphone', 'Ανενεργός': 'inact', 'Ονοματεπώνυμο': 'rname', 'Τηλ. οικίας': 'hphone'}

class CSV:
    def __init__(self):
        self.fields_map = FIELDS_MAP
    
    def parse(self, fname):
        users_dict = csv.DictReader(open(fname))
        users = {}
        groups = {}
        for user_d in users_dict:
            user = libuser.User()
            
            for key, value in user_d.iteritems():
                try:
                    user.__dict__[self.fields_map[key]] = value # FIXME: Here we lose the datatype
                except:
                    pass
            # Try to convert the numbers from string to int
            int_attributes = ['lstchg', 'gid', 'uid', 'expire', 'max', 'warn', 'min', 'inact']
            for attr in int_attributes:
                try:
                    user.__dict__[attr] = int(user.__dict__[attr])
                except ValueError:
                    user.__dict__[attr] = None
            # If plainpw is set, override and update password
            if user.plainpw:
                user.password = libuser.encrypt(user.plainpw)
            
            if user.name:
                users[user.name] = user
                user_groups_string = user.groups
                user.groups = []
                for g in user_groups_string.split(','):
                    pair = g.split(':')
                    if len(pair) == 2:
                        gname, gid = pair
                        try:
                            gid = int(gid)
                        except ValueError:
                            gid = None
                    else: # There is no GID specified for this group
                        gname = g
                        gid = None
                    if gname != '':
                        user.groups.append(gname)
                    
                    # Create Group instances from memberships
                    if gname not in groups:
                        groups[gname] = libuser.Group(gname, gid)
                    groups[gname].members[user.name] = user
                        
                if user.groups == '':
                    user.groups = None
        
        return libuser.Set(users, groups)
            

    def write(self, fname, system, users):
        f = open(fname, 'w')
        writer = csv.DictWriter(f, fieldnames=libuser.CSV_USER_FIELDS)
        writer.writerow(dict((n,n) for n in libuser.CSV_USER_FIELDS))
        for user in users:
            u_dict = dict( (key, user.__dict__[o_key] if user.__dict__[o_key] is not None else '') for key, o_key in self.fields_map.iteritems())
            u_dict['Κωδικός'] = '' # We don't have the plain password
            u_dict['Ομάδες'] = list(u_dict['Ομάδες'])
            # Convert the groups value to a proper gname:gid pairs formatted string
            final_groups = u_dict['Ομάδες']
            final_groups.remove(u_dict['Όνομα κύριας ομάδας'])
            for i, gname in enumerate(final_groups):
                gid = system.groups[gname].gid
                final_groups[i] = ':'.join((final_groups[i], str(gid)))
            u_dict['Ομάδες'] = ','.join(final_groups)
            
            writer.writerow(u_dict)
        f.close()


class passwd():
    # passwd format: username:password (or x):UID:GID:gecos:home:shell
    # shadow format: username:password (or */!):last change:min:max:warn:inact:expire:reserved
    # group format: group_name:password (or x):GID:user_list
    # gshadow format: Not Implemented
    def __init__(self):
        pass
    
    def parse(self, pwd, spwd=None, grp=None):
        new_set = libuser.Set()
        
        with open(pwd) as f:
            reader = csv.reader(f, delimiter=':', quoting=csv.QUOTE_NONE)
            for row in reader:
                u = libuser.User()
                u.name = row[0]
                u.password = row[1]
                u.uid = int(row[2])
                u.gid = int(row[3])
                gecos = row[4].split(',', 4)
                gecos += [''] * (5 - len(gecos)) # Pad with empty strings so we have exactly 5 items
                u.rname, u.office, u.wphone, u.hphone, u.other = gecos
                u.directory = row[5]
                u.shell = row[6]
                new_set.add_user(u)
        
        if spwd:
            with open(spwd) as f:
                reader = csv.reader(f, delimiter=':', quoting=csv.QUOTE_NONE)
                for row in reader:
                    name = row[0]
                    u = new_set.users[name] # The user must exist in passwd
                    u.password = row[1]
                    nums = ['lstchg', 'min', 'max', 'warn', 'inact', 'expire']
                    for i, att in enumerate(nums, 2):
                        try:
                            u.__dict__[att] = int(row[i])
                        except:
                            pass
        
        if grp:
            with open(grp) as f:
                reader = csv.reader(f, delimiter=':', quoting=csv.QUOTE_NONE)
                gids_map = {} # This is only used to set the primary_group User attribute
                for row in reader:
                    g = libuser.Group()
                    g.name = row[0]
                    g.gid = int(row[2])
                    members = row[3].split(',')
                    if members == ['']:
                        members = []
                    g.members = {}
                    for name in members:
                        g.members[name] = new_set.users[name]
                        new_set.users[name].groups.append(g.name)
                    
                    new_set.add_group(g)
                    gids_map[g.gid] = g.name
                
                for u in new_set.users.values():
                    u.primary_group = gids_map[u.gid]
                    if u.primary_group in u.groups:
                        u.groups.remove(u.primary_group)
                    #u.groups.append(u.primary_group)
        
        return new_set
        
