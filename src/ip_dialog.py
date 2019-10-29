# This File is part of the ltsp-manager.
#
# Copyright 2012-2018 by it's authors.
#
# Licensed under GNU General Public License 3.0 or later.
# Some rights reserved. See COPYING, AUTHORS.

"""
Connection information and creation dialog.
"""

from gi.repository import Gtk, Gdk, GObject
from binascii import unhexlify, hexlify
import re
import uuid
import struct, socket
import dialogs
import dbus
import common
import parsers

## Define global variables

IP_REG = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([1-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-4])$"
BUS = dbus.SystemBus()
DBUS_SERVICE_NAME = 'org.freedesktop.NetworkManager'
MSG_PC_CONFLICT_IP = _("The address {0} is already is use by another workstation. Please enter another one.")
MSG_ROUTE_CONFLICT_IP = _("The address {0} is already in use as the default gateway. Please enter another one.")
MSG_WRONG_REGEX_IP = _("Invalid IP address. It must be in the form x.y.z.w, where x, y, z, w are between 1 and 255.")
MSG_ERROR_CONNECT_NM = _("Could not connect to Network Manager")
MSG_NO_DEVICES = _("No device available")
MSG_NO_WIRED_DEVICES = _("No wired devices available")
MSG_TITLE_SUBNET = _("The subnet has changed.")
MSG_SUBNET = _("The subnet has changed for device <b>{0}</b>. The dialog will suggest a new method according to the new values that were received from the router.")
MSG_SUBNET_PLURAL = _("The subnet has changed for devices <b>{0}</b>. The dialog will suggest a new method according to the new values that were received from the router.")
MSG_TITLE_CONNECTIONS_CREATE = _("The connections were successfully created.")
MSG_TITLE_DNSMASQ_RESTART_FAIL = _("Failure while restarting dnsmasq.")
MSG_SUGGEST_HOSTNAME = _("It is suggested to change your hostname to <b>{0}</b>") + "\n\n"
MSG_DNSMASQ_RESTART_SUCCESS = _("Successfully created network connections and restarted dnsmasq.")
MSG_DNSMASQ_RESTART_FAIL_ENABLE = _("Successfully created network connections, but failed while restarting dnsmasq because the connections were not activated.")
MSG_DNSMASQ_RESTART_FAIL = _("Successfully created network connections, but failed while restarting dnsmasq.")

TITLE_ERROR = _("Error")
TITLE_INFO = _("Information")
TITLE_SUCCESS = _("Success")

## Define global functions

def string_to_int32(address):
    """
    Convert ip to int32
    """
    return struct.unpack("I",socket.inet_aton(address))[0]


def int32_to_string(num):
    """
    Convert int32 to ip
    """
    return socket.inet_ntoa(struct.pack("I",num))


def bits_to_subnet(bits):
    """
    Convert bits to subnet mask
    """
    try:
        bits=int(bits)
        if bits<=0 or bits>32:
            raise Exception
    except:
        return "255.255.255.255"
    num = ((1<<bits)-1)<<(32-bits)
    return socket.inet_ntoa(struct.pack("!I",num))


def subnet_to_bits(subnet):
    """
    Convert mask to bits
    """
    return sum([bin(int(x)).count('1') for x in subnet.split('.')])


## Define Network Manager classes

class Network_Manager_DBus(object):
    def __init__(self, object_path, interface_name):
        """
        Return NetworkManager DBus
        """
        self.proxy = BUS.get_object(DBUS_SERVICE_NAME, object_path)
        self.interface = dbus.Interface(self.proxy, interface_name)
        try:
            self.properties = self.interface.get_dbus_method('GetAll', dbus_interface='org.freedesktop.DBus.Properties')(interface_name)
        except dbus.exceptions.DBusException:
            pass


class Network_Manager(Network_Manager_DBus):
    def __init__(self):
        """
        Return NetworkManager interface from NetworkManager object
        """
        self.object_path = '/org/freedesktop/NetworkManager'
        self.interface_name = 'org.freedesktop.NetworkManager'
        super(Network_Manager, self).__init__(self.object_path, self.interface_name)

    def get_devices(self):
        """
        Return Device object
        """
        return self.interface.GetDevices()

    def get_active_connections(self):
        """
        Return current active connections
        """
        return self.properties['ActiveConnections']

    def get_active_connections_settings_path(self):
        """
        Return Settings path of the active connections
        """
        active_connections_settings_path = []
        for active_conenction in self.get_active_connections():
            activeconnection = ActiveConnection(active_conenction)
            active_connections_settings_path.append(str(activeconnection.get_properties()))

        return active_connections_settings_path


class ActiveConnection(Network_Manager_DBus):
    def __init__(self, active_connection_name):
        """
        Return Active interface from ActiveConnection/X object
        """
        self.object_path = active_connection_name
        self.interface_name = 'org.freedesktop.NetworkManager.Connection.Active'
        super(ActiveConnection, self).__init__(self.object_path, self.interface_name)

    def get_properties(self):
        """
        Return Active characteristics objects
        """
        connection_settings = self.properties['Connection']
        return connection_settings


class Device(Network_Manager_DBus):
    def __init__(self, device_name):
        """
        Return Device interface from Devices/X object
        """
        self.object_path = device_name
        self.interface_name = 'org.freedesktop.NetworkManager.Device'
        super(Device, self).__init__(self.object_path, self.interface_name)

    def get_properties(self):
        """
        Return Device characteristics objects
        """
        ip4config_path = self.properties['Ip4Config']
        interface = self.properties['Interface']
        driver = self.properties['Driver']
        device_type = self.properties['DeviceType']
        managed = self.properties['Managed']
        return ip4config_path, interface, driver, device_type, managed


class Device_Wired(Network_Manager_DBus):
    def __init__(self, device_name):
        """
        Return WiredDevice interface from Devices/X object
        """
        self.object_path = device_name
        self.interface_name = 'org.freedesktop.NetworkManager.Device.Wired'
        super(Device_Wired, self).__init__(self.object_path, self.interface_name)

    def get_properties(self):
        """
        Return WiredDevice characteristics objectss
        """
        mac = self.properties['HwAddress']
        speed = self.properties['Speed']
        if speed == 0:
            speed = _("Unknown")
        carrier = self.properties['Carrier']
        if carrier == '':
            carrier = 0
        return mac, str(speed), carrier


class IP4_Config(Network_Manager_DBus):
    def __init__(self, ip4config_name):
        """
        Return IP4Config interface from IP4Config/X object
        """
        self.object_path = ip4config_name
        self.interface_name = 'org.freedesktop.NetworkManager.IP4Config'
        super(IP4_Config, self).__init__(self.object_path, self.interface_name)

    def get_properties(self):
        """
        Return ip, subnet, route and dns values
        """
        ip, mask, route = self.properties['Addresses'][0]
        dnss = self.properties['Nameservers']
        return ip, mask, route, dnss


class Settings(Network_Manager_DBus):
    def __init__(self):
        """
        Return Settings interface from Settings object
        """
        self.object_path = '/org/freedesktop/NetworkManager/Settings'
        self.interface_name = 'org.freedesktop.NetworkManager.Settings'
        super(Settings, self).__init__(self.object_path, self.interface_name)

    def get_list_connections(self):
        """
        Return all connection settings (Setting object)
        """
        return self.interface.ListConnections()


class Connection_Settings(Network_Manager_DBus):
    def __init__(self, connection_settings_name):
        """
        Return Connection interface from Setting/X object
        """
        self.object_path = connection_settings_name
        self.interface_name = 'org.freedesktop.NetworkManager.Settings.Connection'
        super(Connection_Settings, self).__init__(self.object_path, self.interface_name)

    def get_settings(self):
        """
        Return connection settings, eg: ipv4, dns, etc
        """
        return self.interface.GetSettings()


## Define Information class

class Info:
    def __init__(self, ip=None, mask=None, route=None, dnss=None):
        self.ip, self.mask, self.route, self.dnss = ip, mask, route, dnss

        # If IP address is not defined then initialize the attributes with a string
        msg = _("No address found")
        if not self.ip:
            self.ip, self.mask, self.route = [msg]*3
            self.dnss = [msg]*3
        self.subnet = None

    def set_values(self, dict=None):
        """
        Set info values
        """
        if dict:
            self.ip = dict['ip']
            self.mask = dict['mask']
            self.route = dict['route']
            self.dnss = dict['dnss']
            self._calculate_subnet()

    def get_values(self, dnss=False):
        """
        Return info as dict
        """
        if dnss:
            return {'ip': self.ip, 'mask': self.mask, 'route': self.route, 'dnss': self.dnss}
        else:
            return {'ip': self.ip, 'mask': self.mask, 'route': self.route}

    def _calculate_subnet(self):
        """
        Calculate subnet
        """
        if self.ip:
            self.subnet = '.'.join(self.ip.split('.')[:3]) + '.0'


## Define Interface class

class Interface:
    def __init__(self, ip4config_path, device_path, interface, driver, device_type, mac, speed, carrier):
        """
        Contains all the information about a connection
        """
        self.ip4config_path, self.device_path, self.interface, self.driver, self.device_type, self.mac,\
        self.speed, self.carrier = ip4config_path, device_path, interface, driver, device_type, mac, speed, carrier

        self.id = '%s,ltsp-manager' % self.interface
        self.interface_connections = []
        self.page = None
        self.conflict = None
        self.connection = None
        self.existing_info = None
        self.dhcp_request_info = None
        self.has_active_connection = False
        self._set_ips()

    def __getattr__(self, item):
        # Return first dhcp values and then existing values
        if self.dhcp_request_info.subnet:
            try:
                return getattr(self.dhcp_request_info, item)
            except AttributeError:
                raise AttributeError
        else:
            try:
                return getattr(self.existing_info, item)
            except AttributeError:
                raise AttributeError

    def _set_ips(self):
        self.existing_info = Info()
        if self.ip4config_path != '/':
            ip4config = IP4_Config(self.ip4config_path)
            ip, mask, route, dnss = ip4config.get_properties()
            self.existing_info.set_values({
                'ip': int32_to_string(ip),
                'mask': bits_to_subnet(mask),
                'route': int32_to_string(route),
                'dnss': [int32_to_string(x) for x in dnss]
            })
            self.has_active_connection = True

        self.dhcp_request_info = Info()
        p = common.run_command(['/usr/lib/klibc/bin/ipconfig', '-n', '-t2', self.interface], True)
        while p.poll() is None:
            while Gtk.events_pending():
                Gtk.main_iteration()
        if p.returncode == 0:
            dhcp_parser = parsers.DHCP()
            dhcp_dict = dhcp_parser.parse(self.interface)
            self.has_active_connection = True
            self.dhcp_request_info.set_values(dhcp_dict)


## Define Page class

class Page:
    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/ltsp/ltsp-manager/ui/ip_dialog.ui')
        self.grid = self.builder.get_object('grid')
        self.method_lstore = self.builder.get_object('method_lstore')
        self.method_entry = self.builder.get_object('method_entry')
        self.method_help_url = self.builder.get_object('method_help_url')
        self.id_entry = self.builder.get_object('id_entry')
        self.interface_entry = self.builder.get_object('interface_entry')
        self.mac_entry = self.builder.get_object('mac_entry')
        self.driver_entry = self.builder.get_object('driver_entry')
        self.speed_entry = self.builder.get_object('speed_entry')
        self.ip_entry = self.builder.get_object('ip_entry')
        self.subnet_entry = self.builder.get_object('subnet_entry')
        self.route_entry = self.builder.get_object('route_entry')
        self.dns1_entry = self.builder.get_object('dns1_entry')
        self.dns2_entry = self.builder.get_object('dns2_entry')
        self.dns3_entry = self.builder.get_object('dns3_entry')
        self.ip_lbl = self.builder.get_object('ip_lbl')
        self.subnet_lbl = self.builder.get_object('subnet_lbl')
        self.route_lbl = self.builder.get_object('route_lbl')
        self.dns1_lbl = self.builder.get_object('dns1_lbl')
        self.dns2_lbl = self.builder.get_object('dns2_lbl')
        self.dns3_lbl = self.builder.get_object('dns3_lbl')
        self.auto_checkbutton = self.builder.get_object('auto_checkbutton')

    def fill_entries(self, interface, ip=None, mask=None, route=None, dnss=None):
        self.id_entry.set_text(interface.id)
        self.interface_entry.set_text('Ethernet (%s)' % interface.interface)
        self.mac_entry.set_text(interface.mac)
        self.driver_entry.set_text(interface.driver)
        self.speed_entry.set_text(interface.speed)

        ip = ip if ip else interface.ip
        mask = mask if mask else interface.mask
        route = route if route else interface.route
        dnss = dnss if dnss else interface.dnss

        self.ip_entry.set_text(ip)
        self.subnet_entry.set_text(mask)
        self.route_entry.set_text(route)
        if len(dnss) >= 1:
            self.dns1_entry.set_visible(True)
            self.dns1_lbl.set_visible(True)
            self.dns1_entry.set_text(dnss[0])
        else:
            self.dns1_entry.set_visible(False)
            self.dns1_lbl.set_visible(False)
        if len(dnss) >= 2:
            self.dns2_entry.set_visible(True)
            self.dns2_lbl.set_visible(True)
            self.dns2_entry.set_text(dnss[1])
        else:
            self.dns2_entry.set_visible(False)
            self.dns2_lbl.set_visible(False)
        if len(dnss) >= 3:
            self.dns3_entry.set_visible(True)
            self.dns3_lbl.set_visible(True)
            self.dns3_entry.set_text(dnss[2])
        else:
            self.dns3_entry.set_visible(False)
            self.dns3_lbl.set_visible(False)

        if interface.has_active_connection:
            self.method_entry.get_model()[2][1] = True
        else:
            self.method_entry.get_model()[2][1] = False


## Define Ip_Dialog class

class Ip_Dialog:
    def __init__(self, parent):
        # Init some values
        self.parent = parent
        self.interfaces = []
        self.interfaces_diff_subnet = []
        self.timeout = 0
        self.settings = None
        # TODO: don't use Greek school DNS servers
        self.ts_dns = ['127.0.0.1', '194.63.238.4', '8.8.8.8']
        self.ltsp_ips = dict(ip='192.168.67.1', mask='255.255.255.0', route='0.0.0.0')
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/ltsp/ltsp-manager/ui/ip_dialog.ui')
        self.builder.connect_signals(self)
        self.main_dlg = self.builder.get_object('main_dlg')
        self.main_dlg_grid = self.builder.get_object('main_dlg_grid')
        self.main_dlg_action_area = self.builder.get_object('main_dlg_action_area')
        self.main_dlg_notebook = self.builder.get_object('main_dlg_notebook')
        self.loading_box = self.builder.get_object('loading_box')
        self.main_dlg.set_transient_for(parent)

        # Connect to NetworkManager
        try:
            self.nm = Network_Manager()
        except dbus.exceptions.DBusException:
            error_dialog = dialogs.ErrorDialog(MSG_ERROR_CONNECT_NM, TITLE_ERROR)
            error_dialog.set_transient_for(self.main_dlg)
            error_dialog.showup()
            return

        # Hide some widget and show loading widget until dhcp request finished
        self.main_dlg_action_area.hide()
        self.main_dlg_grid.attach(self.loading_box, 0, 1, 2, 1)
        self.main_dlg.show()

        GObject.idle_add(self.initialize_interfaces)

    def initialize_interfaces(self):
        # Find devices
        self.settings = Settings()
        device_paths = self.nm.get_devices()
        if len(device_paths) == 0:
            dialogs.ErrorDialog(MSG_NO_DEVICES, TITLE_ERROR).showup()
            return
        for device_path in device_paths:
            device = Device(device_path)
            ip4config_path, interface, driver, device_type, managed = device.get_properties()
            if device_type == 1 and managed:
                devicewired = Device_Wired(device_path)
                mac, speed, carrier = devicewired.get_properties()
                interface = Interface(ip4config_path, device_path, interface, \
                                        driver, device_type, mac, speed, carrier)
                self.interfaces.append(interface)
        if len(self.interfaces) == 0:
            dialogs.ErrorDialog(MSG_NO_WIRED_DEVICES, TITLE_ERROR).showup()
            return
        self.interfaces.sort(key=lambda interface: interface.interface)

        # Populate GUI
        for interface in self.interfaces:
            if interface.dhcp_request_info.subnet and interface.existing_info.subnet and \
                            interface.dhcp_request_info.subnet != interface.existing_info.subnet:
                    self.interfaces_diff_subnet.append(interface)
            self.populate_pages(interface)

        # Show all widgets and destroy loading widget. Dialog is ready
        self.main_dlg.set_deletable(True)
        self.main_dlg.show_all()
        self.loading_box.destroy()

        # Set the appropriate method to each device
        self.set_default()

        # If subnet has change alert message which define devices with different subnet
        if len(self.interfaces_diff_subnet) > 0:
            if len(self.interfaces_diff_subnet) > 1:
                msg = MSG_SUBNET_PLURAL.format(', '.join([str(interface.interface)
                                                          for interface in self.interfaces_diff_subnet]))
            else:
                msg = MSG_SUBNET.format(', '.join([str(interface.interface)
                                                   for interface in self.interfaces_diff_subnet]))
            info_dialog = dialogs.InfoDialog(MSG_TITLE_SUBNET, TITLE_INFO)
            info_dialog.format_secondary_markup(msg)
            info_dialog.set_transient_for(self.main_dlg)
            info_dialog.showup()

    def populate_pages(self, interface):
        page = Page()
        interface.page = page
        page.ip_entry.connect('changed', self.on_ip_entry_changed, interface)
        page.method_entry.connect('changed', self.on_method_entry_changed, interface)
        page.fill_entries(interface, **interface.existing_info.get_values(dnss=True))
        if Gdk.Screen.get_default().get_height() <= 768:
            scrolledwindow = Gtk.ScrolledWindow()
            scrolledwindow.add_with_viewport(page.grid)
            scrolledwindow.show()
            self.main_dlg_notebook.append_page(scrolledwindow, Gtk.Label('Ethernet (%s)' % interface.interface))
            self.main_dlg_notebook.set_tab_reorderable(scrolledwindow, True)
        else:
            self.main_dlg_notebook.append_page(page.grid, Gtk.Label('Ethernet (%s)' % interface.interface))
            self.main_dlg_notebook.set_tab_reorderable(page.grid, True)

    def set_default(self):
        # By default active is 4, no creation to all interfaces.
        # We care about the first only, so we purpose one method
        # only for the first interface. All other interfaces
        # maintained to 4.
        carrier_interfaces = [interface for interface in self.interfaces if interface.carrier == 1]
        if len(carrier_interfaces) == 0:
            self.interfaces[0].page.method_entry.set_active(1)
            self.main_dlg_notebook.reorder_child(self.interfaces[0].page.grid, 0)
        else:
            if carrier_interfaces[0].ip.startswith('10.'):
                carrier_interfaces[0].page.method_entry.set_active(2)
            else:
                carrier_interfaces[0].page.method_entry.set_active(1)
            self.main_dlg_notebook.reorder_child(carrier_interfaces[0].page.grid, 0)

        self.main_dlg_notebook.set_current_page(0)

    def watch_nm(self, interest_interfaces, prefered_hostname):
        self.timeout += 1000
        break_bool = True
        for interface in interest_interfaces:
            if interface.carrier != 1:
                continue
            #TODO: Change it (do not create new instances)
            device = Device(interface.device_path)
            ip4config_path, interface, driver, device_type, managed = device.get_properties()
            if ip4config_path == '/':
                break_bool = False

        if break_bool:
            p = common.run_command(['sh', '-c', 'ltsp dnsmasq'], True)
            while p.poll() is None:
                while Gtk.events_pending():
                    Gtk.main_iteration()

            if p.returncode == 0:
                msg = MSG_DNSMASQ_RESTART_SUCCESS
                if prefered_hostname:
                    msg = MSG_SUGGEST_HOSTNAME.format(prefered_hostname) + msg

                success_dialog = dialogs.InfoDialog(MSG_TITLE_CONNECTIONS_CREATE, TITLE_SUCCESS)
                success_dialog.format_secondary_markup(msg)
                success_dialog.set_transient_for(self.main_dlg)
                success_dialog.showup()
                self.main_dlg.destroy()
            else:
                error_dialog = dialogs.ErrorDialog(MSG_TITLE_DNSMASQ_RESTART_FAIL, TITLE_ERROR)
                error_dialog.format_secondary_markup(MSG_DNSMASQ_RESTART_FAIL)
                error_dialog.set_transient_for(self.main_dlg)
                error_dialog.showup()
                self.main_dlg.destroy()
            return False
        elif not break_bool and self.timeout == 30000:
            msg = MSG_DNSMASQ_RESTART_FAIL_ENABLE
            if prefered_hostname:
                msg = MSG_SUGGEST_HOSTNAME.format(prefered_hostname) + msg

            success_dialog = dialogs.InfoDialog(MSG_TITLE_CONNECTIONS_CREATE, TITLE_SUCCESS)
            success_dialog.format_secondary_markup(msg)
            success_dialog.set_transient_for(self.main_dlg)
            success_dialog.showup()
            self.main_dlg.destroy()
            return False
        return True

    def create_update_connections(self, interest_interfaces, prefered_hostname, dnsmasq_via_carrier,
                                  dnsmasq_via_autoconnect):
        for interface in interest_interfaces:
            # Test if static ip exists in network
            # Case which doesn't work: User had set .10 manual and .10 is owned by another pc,
            # arping always fail so we can't catch the conflict.
            if interface.page.method_entry.get_active() == 2 and \
                            interface.carrier == 1 and self.nm.get_active_connections():
                test_ip = interface.page.ip_entry.get_text()
                if test_ip != interface.existing_info.ip:
                    p = common.run_command(['arping', '-f', '-w1', '-I', interface.interface, test_ip], True)
                    while p.poll() is None:
                        while Gtk.events_pending():
                            Gtk.main_iteration()
                    if p.returncode == 0:
                        interface.page.ip_entry.set_icon_from_stock(1, Gtk.STOCK_DIALOG_WARNING)
                        interface.page.ip_entry.set_icon_tooltip_text(1, MSG_PC_CONFLICT_IP.format(test_ip))
                        title = MSG_PC_CONFLICT_IP.format(test_ip)
                        err_dialog = dialogs.ErrorDialog(title, TITLE_ERROR)
                        err_dialog.set_transient_for(self.main_dlg)
                        if err_dialog.showup() != Gtk.ResponseType.OK:
                            self.main_dlg.set_sensitive(True)
                            self.main_dlg.show()
                            return

            if interface.conflict is not None:
                interface.conflict.interface.Update(interface.connection)
                if interface.carrier == 1 and interface.page.auto_checkbutton.get_active():
                    self.nm.interface.ActivateConnection(interface.conflict.object_path, interface.device_path, '/')
            else:
                object_path = self.settings.interface.AddConnection(interface.connection)
                if interface.carrier == 1 and interface.page.auto_checkbutton.get_active():
                    self.nm.interface.ActivateConnection(object_path, interface.device_path, '/')

            for connection_settings in interface.interface_connections:
                settings = connection_settings.get_settings()
                settings['connection'][dbus.String('autoconnect')] = dbus.Boolean('false')
                connection_settings.interface.Update(settings)

        if dnsmasq_via_carrier and dnsmasq_via_autoconnect:
            GObject.timeout_add(1000, self.watch_nm, interest_interfaces, prefered_hostname)
        else:
            success_dialog = dialogs.InfoDialog(MSG_TITLE_CONNECTIONS_CREATE, TITLE_SUCCESS)
            success_dialog.set_transient_for(self.main_dlg)
            success_dialog.showup()
            self.main_dlg.destroy()

    def check_button(self):
        check_ip = True
        check_method = False
        for interface in self.interfaces:
            if interface.page is None:
                continue
            ip = interface.page.ip_entry.get_text()
            method = interface.page.method_entry.get_active()
            if not re.match(IP_REG, ip) and ip != _("No address found"):
                check_ip = False
            if method != 4:
                check_method = True

        if check_ip and check_method:
            self.main_dlg.set_response_sensitive(Gtk.ResponseType.OK, True)
        else:
            self.main_dlg.set_response_sensitive(Gtk.ResponseType.OK, False)

## Callbacks

    def on_method_entry_changed(self, method_entry, interface):
        reset_ltsp_method = True
        for l_interface in self.interfaces:
            if l_interface.page.method_entry.get_active() == 3:
                    reset_ltsp_method = False

        if reset_ltsp_method and len(self.interfaces) >= 2:
            for l_interface in self.interfaces:
                l_interface.page.method_entry.get_model()[3][1] = True

        # Auto. We want always to show the dhcp request values
        if interface.page.method_entry.get_active() == 0:
            interface.page.ip_entry.set_sensitive(False)
            interface.page.auto_checkbutton.set_sensitive(True)
            interface.page.fill_entries(interface, **interface.dhcp_request_info.get_values(dnss=True))
        # Only auto addresses. The same as above
        elif interface.page.method_entry.get_active() == 1:
            interface.page.ip_entry.set_sensitive(False)
            interface.page.auto_checkbutton.set_sensitive(True)
            interface.page.fill_entries(interface, dnss=[dns for dns in self.ts_dns],
                                        **interface.dhcp_request_info.get_values())
        # Manual
        elif interface.page.method_entry.get_active() == 2:
            ip = None
            interface.page.ip_entry.set_sensitive(True)
            interface.page.auto_checkbutton.set_sensitive(True)
            connection_settings_paths = self.settings.get_list_connections()
            # if we want to bring back the settings from any connection we have to remove the following line
            if interface.ip.startswith('10.'):
                if interface.existing_info.subnet and interface.dhcp_request_info.subnet and \
                                interface.existing_info.subnet != interface.dhcp_request_info.subnet:
                    ip = '.'.join(interface.ip.split('.')[0:3])+'.10'
                elif self.nm.get_active_connections():
                    # if ip starts with 10. and we have active connections
                    for counter, connection_settings_path in enumerate(connection_settings_paths):
                        connection_settings = Connection_Settings(connection_settings_path)
                        connection_settings_id = connection_settings.get_settings()['connection']['id']
                        try:
                            connection_settings_method = connection_settings.get_settings()['ipv4']['method']
                        except KeyError:
                            connection_settings_method = None

                        if connection_settings_id == interface.id and \
                                        connection_settings_method == dbus.String('manual') and \
                                        connection_settings_path in self.nm.get_active_connections_settings_path():
                            ip = interface.existing_info.ip
                            break
                        elif counter == len(connection_settings_paths) - 1:
                            ip = '.'.join(interface.ip.split('.')[0:3])+'.10'
                else:
                    # if ip starts with 10. and we don't have active connections load instant .10
                    ip = '.'.join(interface.ip.split('.')[0:3])+'.10'
            interface.page.fill_entries(interface, ip=ip, dnss=[dns for dns in self.ts_dns])
        # Ltsp
        elif interface.page.method_entry.get_active() == 3:
            interface.page.ip_entry.set_sensitive(False)
            interface.page.auto_checkbutton.set_sensitive(True)
            interface.page.fill_entries(interface, dnss=[dns for dns in self.ts_dns], **self.ltsp_ips)
            for l_interface in self.interfaces:
                if l_interface != interface:
                    l_interface.page.method_entry.get_model()[3][1] = False
        # No creation
        elif interface.page.method_entry.get_active() == 4:
            interface.page.ip_entry.set_sensitive(False)
            interface.page.auto_checkbutton.set_sensitive(False)
            interface.page.fill_entries(interface, **interface.existing_info.get_values(dnss=True))
        self.check_button()

    def on_ip_entry_changed(self, ip_entry, interface):
        if interface.page.ip_entry.get_text() != _("No address found"):
            ip = interface.page.ip_entry.get_text()
            sub_ip = '.'.join(interface.ip.split('.')[0:3])+'.'
            if not re.match(IP_REG, ip):
                interface.page.ip_entry.set_position(-1)
                if ip != interface.page.route_entry.get_text():
                    interface.page.ip_entry.set_text(sub_ip)
                interface.page.ip_entry.set_icon_from_stock(1, Gtk.STOCK_DIALOG_WARNING)
                interface.page.ip_entry.set_icon_tooltip_text(1, MSG_WRONG_REGEX_IP)
            elif ip == interface.page.route_entry.get_text():
                interface.page.ip_entry.set_position(-1)
                if ip != interface.page.route_entry.get_text():
                    interface.page.ip_entry.set_text(sub_ip)
                interface.page.ip_entry.set_icon_from_stock(1, Gtk.STOCK_DIALOG_WARNING)
                interface.page.ip_entry.set_icon_tooltip_text(1, MSG_ROUTE_CONFLICT_IP.format(ip))
            else:
                interface.page.ip_entry.set_icon_from_stock(1, None)
            self.check_button()

    def on_ip_dialog_response(self, main_dlg, response):
        if response != Gtk.ResponseType.OK:
            self.main_dlg.destroy()
            return

        dnsmasq_via_carrier = False
        dnsmasq_via_autoconnect = False
        prefered_hostname = None
        new_connections = []
        replace_connections = []
        interest_interfaces = [interface for interface in self.interfaces \
                           if interface.page.method_entry.get_active()!=4]

        for interface in interest_interfaces:
            bytes = [unhexlify(v) for v in interface.mac.split(":")]
            ethernet = dbus.Dictionary({'duplex': 'full',
                                        'mac-address': dbus.Array(bytes, signature=dbus.Signature('y'))})

            connection = dbus.Dictionary({'type': '802-3-ethernet', 'uuid': str(uuid.uuid4()), 'id': interface.id})

            dns = dbus.Array([dbus.UInt32(string_to_int32(self.ts_dns[0])),
                              dbus.UInt32(string_to_int32(self.ts_dns[1])),
                              dbus.UInt32(string_to_int32(self.ts_dns[2]))],
                             signature=dbus.Signature('u'))

            ipv6 = dbus.Dictionary({'method': 'ignore'})

            try:
                # This variables is used only in 2 and 3 method
                ip = string_to_int32(interface.page.ip_entry.get_text().strip())
                subnet = subnet_to_bits(interface.page.subnet_entry.get_text().strip())
                route = string_to_int32(interface.page.route_entry.get_text().strip())

                addresses = dbus.Array([dbus.UInt32(ip),
                                        dbus.UInt32(subnet),
                                        dbus.UInt32(route)],
                                       signature=dbus.Signature('u'))
            except:
                pass

            if not interface.page.auto_checkbutton.get_active():
                connection.update({'autoconnect': dbus.Boolean('false')})

            if interface.page.method_entry.get_active() == 0:
                # Auto
                ipv4 = dbus.Dictionary({'method': 'auto', 'may-fail': 0})
            elif interface.page.method_entry.get_active() == 1:
                # Only auto addresses
                ipv4 = dbus.Dictionary({'method': 'auto', 'may-fail': 0, 'dns': dns, 'ignore-auto-dns': 1})
            elif interface.page.method_entry.get_active() == 2:
                # Manual
                ipv4 = dbus.Dictionary({'method': 'manual', 'dns': dns, 'may-fail': 0,
                                        'dhcp-send-hostname': dbus.Boolean('false'),
                                        'addresses': dbus.Array([addresses], signature=dbus.Signature('au'))})

                if int32_to_string(ip).startswith('10.') and \
                        (int32_to_string(ip).endswith('.10') or int32_to_string(ip).endswith('.11')) and \
                        interface.carrier == 1:
                    # Try to resolve the ip and purpose hostname. We keep info if dns_search endswith sch.gr
                    found, hostname = common.run_command(['dig', '@nic.sch.gr', '+short', '-x', int32_to_string(ip)])
                    if found:
                        hostname = hostname.split('\n')[0].strip('.')
                        dns_search = '.'.join(hostname.split('.')[1:])
                        if dns_search.endswith('sch.gr'):
                            prefered_hostname = hostname.split('.')[0]
                            dns_search = dbus.Array([dns_search], signature=dbus.Signature('s'))
                            ipv4.update({'dns-search': dns_search})
            elif interface.page.method_entry.get_active() == 3:
                # LTSP
                ipv4 = dbus.Dictionary({'method': 'manual', 'dns': dns, 'may-fail': 0,
                                        'dhcp-send-hostname': dbus.Boolean('false'),
                                        'addresses': dbus.Array([addresses], signature=dbus.Signature('au'))})

            conn = dbus.Dictionary({'802-3-ethernet': ethernet, 'connection': connection, 'ipv4': ipv4, 'ipv6': ipv6})
            interface.connection = conn
            new_connections.append(interface)

            connection_settings_paths = self.settings.get_list_connections()
            for connection_settings_path in connection_settings_paths:
                connection_settings = Connection_Settings(connection_settings_path)
                connection_settings_id = connection_settings.get_settings()['connection']['id']
                # If connection with same id found set conflict variable to this existing connection and give to our
                # connection the existing connection uuid
                if connection_settings_id == interface.id:
                    connection_settings_uuid = connection_settings.get_settings()['connection']['uuid']
                    interface.connection['connection']['uuid'] = connection_settings_uuid
                    interface.conflict = connection_settings
                    replace_connections.append(interface)
                    new_connections.remove(interface)
                try:
                    connection_settings_mac = \
                        ':'.join([hexlify(chr(v).encode('utf-8')).decode('utf-8')
                                  for v in connection_settings.get_settings()['802-3-ethernet']['mac-address']]).upper()
                except KeyError:
                    continue
                if interface.mac == connection_settings_mac and interface.id != connection_settings_id and \
                        interface.page.auto_checkbutton.get_active():
                    interface.interface_connections.append(connection_settings)

        title = _("Are you sure you want to continue?")
        msg = ""

        if len(new_connections) > 0:
            if len(new_connections) == 1:
                msg += _("You're about to create the connection:") + "\n\n"
            else:
                msg += _("You're about to create the connections:") + "\n\n"

            for counter, interface in enumerate(new_connections):
                if interface.carrier == 1:
                    dnsmasq_via_carrier = True
                if interface.page.auto_checkbutton.get_active():
                    dnsmasq_via_autoconnect = True
                msg += '<b>%s</b> (%s)\n' %(str(interface.id),
                                            interface.page.method_lstore[interface.page.method_entry.get_active()][0])
                if counter == len(new_connections) -1 and len(replace_connections) != 0:
                    msg += '\n'

        if len(replace_connections) > 0:
            if len(replace_connections) == 1:
                msg += _("You're about to update the connection:") + "\n\n"
            else:
                msg += _("You're about to update the connections:") + "\n\n"

            for interface in replace_connections:
                if interface.carrier == 1:
                    dnsmasq_via_carrier = True
                if interface.page.auto_checkbutton.get_active():
                    dnsmasq_via_autoconnect = True
                msg += '<b>%s</b> (%s)\n' %(str(interface.id),
                                            interface.page.method_lstore[interface.page.method_entry.get_active()][0])

        if dnsmasq_via_carrier and dnsmasq_via_autoconnect:
            msg += "\n" + _("and to recreate the dnsmasq configuration file.")
        elif not dnsmasq_via_carrier and dnsmasq_via_autoconnect:
            msg += "\n" + _("<b>Warning:</b> Recreating the dnsmasq configuration file is impossible because no network cable is attached to any of the available devices.")

        ask_dialog = dialogs.AskDialog(title, _("Confirmation"))
        ask_dialog.format_secondary_markup(msg)
        ask_dialog.set_transient_for(self.main_dlg)
        if ask_dialog.showup() != Gtk.ResponseType.YES:
            return

        # Make window sensitive until popup dialog appears
        self.main_dlg.set_sensitive(False)

        GObject.idle_add(self.create_update_connections, interest_interfaces, prefered_hostname, dnsmasq_via_carrier,
                         dnsmasq_via_autoconnect)
