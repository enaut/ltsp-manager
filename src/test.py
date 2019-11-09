
from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)
import dbus
import sys
from nose.tools import assert_raises
import time

s_bus = dbus.SystemBus()
account_manager = s_bus.get_object('io.github.ltsp-manager', '/AccountManager')

input("This will be potentially harmfull to your computer!\nPlease do not continue if you do not know what you do.\n Press [ctrl]+[C] to abort!")

#sys.stderr.write(str(account_manager.ListGroups()))


#proxy = s_bus.get_object('org.freedesktop.PolicyKit1', '/org/freedesktop/PolicyKit1/Authority')
#polkit = dbus.Interface(proxy, dbus_interface='org.freedesktop.PolicyKit1.Authority')


# subject = ('system-bus-name', {'name': s_bus.get_unique_name()})
# action_id = "io.github.ltsp-manager.accountmanager"
# details = {}
# flags = 1
# cancellation_id = ''
# auth = polkit.CheckAuthorization(subject, action_id, details, flags, cancellation_id)
# print(auth)

def g_u(name):
    p = account_manager.FindUserByName(name)
    u = s_bus.get_object('io.github.ltsp-manager', p)
    i = dbus.Interface(u, 'io.github.ltsp.manager.AccountManager')
    return i

def g_p(p):
    u = s_bus.get_object('io.github.ltsp-manager', p)
    i = dbus.Interface(u, 'io.github.ltsp.manager.AccountManager')
    return i

def test_create_user():
    userp = account_manager.CreateUser("testuserin", '')
    user_path = account_manager.FindUserByName("testuserin")
    assert(userp == user_path)
    assert(str(user_path).startswith("/User/"))

def test_is_user_there():
    user = g_u("testuserin")
    assert(str(user.GetMainGroup()).startswith("/Group/"))
    assert("/User/{}".format(user.GetUID()) in account_manager.ListUsers())
    assert("testuserin" == user.GetUsername())

def test_delete_user():
    user = g_u("testuserin")
    delt = user.DeleteUser(True)
    assert(delt)
    assert_raises(dbus.exceptions.DBusException, user.GetUsername)

# def test_list_groups():
#     paths = account_manager.ListUsers()
#     assert(len(paths) > 0)
#     #for path in paths:
#     #    yield func, path


# def func(path):
#     u = g_p(path)
#     if u.IsSystemUser():
#         assert(u.GetUID()<1000)
#     else:
#         assert(u.GetUID()>999)
