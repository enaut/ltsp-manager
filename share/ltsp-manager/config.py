import configparser
import os

path = os.path.expanduser('~/.config/ltsp-manager/')
settings_f = os.path.join(path, 'settings')

gui_defaults = {
    'show_system_groups' : False,
    'show_private_groups' : False,
    'visible_user_columns' : 'all',
    'requests_checked_roles' : '',
    'requests_checked_groups' : '' }
# Role names are parsed with config.parser and need to be lowercase.
roles_defaults = {
    "administrator": 'adm,cdrom,dip,epoptes,lpadmin,plugdev,sambashare,sudo,vboxusers,$$teachers',
    "staff": 'adm,cdrom,plugdev,sambashare,vboxusers',
    "student": 'sambashare,vboxusers',
    "teacher": 'adm,cdrom,epoptes,plugdev,sambashare,vboxusers,$$teachers' }
# Used when displaying roles in a UI, but not when saving them in a config.
roles_translations = {
    "administrator": _("Administrator"),
    "staff": _("Staff"),
    "student": _("Student"),
    "teacher": _("Teacher") }

parser = configparser.ConfigParser()

def save():
    f = open(settings_f, 'w')
    parser.write(f)
    f.close()

def setdefaults(overwrite=False):
    if not parser.has_section('GUI'):
        parser.add_section('GUI')
    
    for k, v in gui_defaults.items():
        if overwrite or not parser.has_option('GUI', k):
            parser.set('GUI', k, str(v))
            
    if not parser.has_section('roles'):
        parser.add_section('roles')
    
    for k, v in roles_defaults.items():
        # TODO: new ltsp-manager versions are not able to append groups like
        # 'fuse' to the saved user Roles, so don't read the user settings
        # at all until we reapproach the issue.
        # if overwrite or not parser.has_option('Roles', k):
            parser.set('roles', k, str(v))
    
    
    save()

if not os.path.isdir(path):
    os.makedirs(path)
    
if not os.path.isfile(settings_f):
    setdefaults()

parser.read(settings_f)
setdefaults()


