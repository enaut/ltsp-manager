# These paths are configured by the install script in paths.ini
import os
python = "/usr/bin/python3"
version = "18.04.2"
localedir = "/usr/share/locale/"
datadir = "/usr/share/"
pkgdatadir = os.path.abspath(os.path.dirname(__file__))
bindir = "/usr/bin/"
sbindir = "/usr/sbin/"
scriptsdir = "/usr/share/ltsp-manager/scripts/"
sysconfdir = "/etc/"

PATH_PREFIX = "/io/github/Ltsp/Manager"
ACCOUNTMANAGER_PATH = PATH_PREFIX + "/AccountManager"
USER_PREFIX = ACCOUNTMANAGER_PATH + "/Users"
GROUP_PREFIX = ACCOUNTMANAGER_PATH + "/Groups"

try:
    with open(os.path.join(pkgdatadir, 'paths.ini')) as f:
        exec(f.read())
except FileNotFoundError:
    pass
