#-*- coding: utf-8 -*-
import ConfigParser
import os

path = os.path.expanduser('~/.config/ltsp-manager/')
settings_f = os.path.join(path, 'settings')

gui_defaults = {'show_system_groups' : False,
                'show_private_groups' : False,
                'visible_user_columns' : 'all',
                'requests_checked_roles' : '',
                'requests_checked_groups' : ''
               }
roles_defaults = {
                  'Καθηγητής' : 'adm,cdrom,epoptes,fuse,plugdev,sambashare,vboxusers,$$teachers',
                  'Διαχειριστής' : 'adm,cdrom,dip,epoptes,fuse,lpadmin,plugdev,sambashare,sudo,vboxusers,$$teachers',
                  'Μαθητής' : 'fuse,sambashare,vboxusers',
                  'Προσωπικό' : 'adm,cdrom,fuse,plugdev,sambashare,vboxusers'
                 }

parser = ConfigParser.SafeConfigParser()

def save():
    f = open(settings_f, 'w')
    parser.write(f)
    f.close()

def setdefaults(overwrite=False):
    if not parser.has_section('GUI'):
        parser.add_section('GUI')
    
    for k, v in gui_defaults.iteritems():
        if overwrite or not parser.has_option('GUI', k):
            parser.set('GUI', k, str(v))
            
    if not parser.has_section('Roles'):
        parser.add_section('Roles')
    
    for k, v in roles_defaults.iteritems():
        # TODO: new ltsp-manager versions are not able to append groups like
        # 'fuse' to the saved user Roles, so don't read the user settings
        # at all until we reapproach the issue.
        # if overwrite or not parser.has_option('Roles', k):
            parser.set('Roles', k, str(v))
    
    
    save()

if not os.path.isdir(path):
    os.makedirs(path)
    
if not os.path.isfile(settings_f):
    setdefaults()

parser.read(settings_f)
setdefaults()


