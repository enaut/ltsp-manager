#-*- coding: utf-8 -*-
import ConfigParser
import os

path = os.path.expanduser('~/.config/sch-scripts/')
settings_f = os.path.join(path, 'settings')

gui_defaults = {'show_system_groups' : False,
                'show_private_groups' : False,
                'visible_user_columns' : 'all',
                'requests_checked_roles' : '',
                'requests_checked_groups' : ''
               }
roles_defaults = {
                  'Καθηγητής' : 'adm,sambashare,plugdev,vboxusers,cdrom,epoptes,$$teachers',
                  'Διαχειριστής' : 'adm,sudo,sambashare,plugdev,vboxusers,cdrom,lpadmin,epoptes,$$teachers,dip',
                  'Μαθητής' : 'sambashare,vboxusers',
                  'Προσωπικό' : 'adm,sambashare,plugdev,vboxusers,cdrom'
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
        if overwrite or not parser.has_option('Roles', k):
            parser.set('Roles', k, str(v))
    
    
    save()

if not os.path.isdir(path):
    os.makedirs(path)
    
if not os.path.isfile(settings_f):
    setdefaults()

parser.read(settings_f)
setdefaults()


