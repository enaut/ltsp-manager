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

