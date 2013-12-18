#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2013
# Lefteris Nikoltsios <lefteris.nikoltsios@gmail.com>, Yannis Siahos <Siahos@cti.gr>
# License GNU GPL version 3 or newer <http://gnu.org/licenses/gpl.html>

from gi.repository import Gtk, Gdk, GObject
from binascii import unhexlify, hexlify
import re
import subprocess
import sys
import uuid
import struct, socket
import dialogs
import dbus


## Define global variables

IP_REG = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([1-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-4])$"
BUS = dbus.SystemBus()
DBUS_SERVICE_NAME = 'org.freedesktop.NetworkManager'


## Define global functions

def string_to_int32(address):
    '''Convert ip to int32'''
    return struct.unpack("I",socket.inet_aton(address))[0]

def int32_to_string(num):
    '''Convert int32 to ip'''
    return socket.inet_ntoa(struct.pack("I",num))

def bits_to_subnet(bits):
    '''Convert bits to subnet mask'''
    try:
        bits=int(bits)
        if bits<=0 or bits>32:
            raise Exception
    except:
        return "255.255.255.255"
    num = ((1L<<bits)-1L)<<(32L-bits)
    return socket.inet_ntoa(struct.pack("!I",num))

def subnet_to_bits(subnet):
    '''Convert mask to bits'''
    return sum([bin(int(x)).count('1') for x in subnet.split('.')])


## Define Network Manager classes

class Network_Manager_DBus(object):
    def __init__(self, object_path, interface_name):
        self.proxy = BUS.get_object(DBUS_SERVICE_NAME, object_path)
        self.interface = dbus.Interface(self.proxy, interface_name)
        try:
            self.properties = self.proxy.GetAll(interface_name, 'org.freedesktop.DBus.Properties')
        except dbus.exceptions.DBusException:
            pass 

class Network_Manager(Network_Manager_DBus):
    def __init__(self):
        self.object_path = '/org/freedesktop/NetworkManager'
        self.interface_name = 'org.freedesktop.NetworkManager'
        super(Network_Manager, self).__init__(self.object_path, self.interface_name)
    
    def get_devices(self):
        return self.interface.GetDevices()

   
class Device(Network_Manager_DBus):
    def __init__(self, device_name):
        self.object_path = device_name
        self.interface_name = 'org.freedesktop.NetworkManager.Device'
        super(Device, self).__init__(self.object_path, self.interface_name)

    def get_properties(self):
        ip4config_path = self.properties['Ip4Config']
        interface = self.properties['Interface']
        driver = self.properties['Driver']
        device_type = self.properties['DeviceType']
        return ip4config_path, interface, driver, device_type
        

class Device_Wired(Network_Manager_DBus):
    def __init__(self, device_name):
        self.object_path = device_name
        self.interface_name = 'org.freedesktop.NetworkManager.Device.Wired'
        super(Device_Wired, self).__init__(self.object_path, self.interface_name)

    def get_properties(self):
        mac = self.properties['HwAddress']
        speed = self.properties['Speed']
        if speed == 0:
            speed = 'Άγνωστη'
        carrier = self.properties['Carrier']
        if carrier == '':
            carrier = 0
        return mac, str(speed), carrier


class IP4_Config(Network_Manager_DBus):
    def __init__(self, ip4config_name):
        self.object_path = ip4config_name
        self.interface_name = 'org.freedesktop.NetworkManager.IP4Config'
        super(IP4_Config, self).__init__(self.object_path, self.interface_name)

    def get_properties(self):
        ip, subnet, route = self.properties['Addresses'][0]
        dnss = self.properties['Nameservers']
        return ip, subnet, route, dnss


class Connection_Settings(Network_Manager_DBus):
    def __init__(self, connection_settings_name):
        self.object_path = connection_settings_name
        self.interface_name = 'org.freedesktop.NetworkManager.Settings.Connection'
        super(Connection_Settings, self).__init__(self.object_path, self.interface_name)

    def get_settings(self):
        return self.interface.GetSettings()


class Settings(Network_Manager_DBus):
    def __init__(self):
        self.object_path = '/org/freedesktop/NetworkManager/Settings'
        self.interface_name = 'org.freedesktop.NetworkManager.Settings'
        super(Settings, self).__init__(self.object_path, self.interface_name)

    def get_list_connections(self):
        return self.interface.ListConnections()


## Define Interface class

class Interface:
    def __init__(self, ip4config_path, device_path, interface, driver, \
                 device_type, mac, speed, carrier):
        self.ip4config_path, self.device_path, self.interface, self.driver, \
        self.device_type, self.mac, self.speed, self.carrier = ip4config_path, device_path, \
        interface, driver, device_type, mac, speed, carrier
        
        self.id = '%s,sch-scripts' %self.interface
        self.interface_connections = []
        self.page = None
        self.conflict = None
        self.connection = None
        self.set_ips()

    def set_ips(self):
        if self.ip4config_path != '/':
            ip4config = IP4_Config(self.ip4config_path) 
            ip, subnet, route, dnss = ip4config.get_properties()
            self.ip = int32_to_string(ip)
            self.subnet = bits_to_subnet(subnet)
            self.route = int32_to_string(route)
            self.dnss = [int32_to_string(x) for x in dnss]
            self.has_active_connection = True 
        else:
            self.ip = 'Δεν βρέθηκε διεύθυνση'
            self.subnet = 'Δεν βρέθηκε διεύθυνση'
            self.route = 'Δεν βρέθηκε διεύθυνση'
            self.dnss = ['Δεν βρέθηκε διεύθυνση', 'Δεν βρέθηκε διεύθυνση', \
                        'Δεν βρέθηκε διεύθυνση']
            self.has_active_connection = False


## Define Page class
   
class Page:
    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file('ip_dialog.ui')
        self.grid = self.builder.get_object('grid')
        self.method_lstore = self.builder.get_object('method_lstore')
        self.method_entry = self.builder.get_object('method_entry')
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
        
    def fill_entries(self, interface):
        self.id_entry.set_text(interface.id)
        self.interface_entry.set_text('Ethernet (%s)' %interface.interface)
        self.mac_entry.set_text(interface.mac)
        self.driver_entry.set_text(interface.driver)
        self.speed_entry.set_text(interface.speed)       
        self.ip_entry.set_text(interface.ip)
        self.subnet_entry.set_text(interface.subnet)
        self.route_entry.set_text(interface.route)
        if len(interface.dnss) >= 1:
            self.dns1_entry.set_visible(True)
            self.dns1_lbl.set_visible(True)
            self.dns1_entry.set_text(interface.dnss[0])
        else:
            self.dns1_entry.set_visible(False)
            self.dns1_lbl.set_visible(False)
        if len(interface.dnss) >= 2:
            self.dns2_entry.set_visible(True)
            self.dns2_lbl.set_visible(True)
            self.dns2_entry.set_text(interface.dnss[1])
        else:
            self.dns2_entry.set_visible(False)
            self.dns2_lbl.set_visible(False)
        if len(interface.dnss) >= 3:
            self.dns3_entry.set_visible(True)
            self.dns3_lbl.set_visible(True)
            self.dns3_entry.set_text(interface.dnss[2])
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
        self.interfaces = []
        self.timeout = 0
        self.ts_dns = ['127.0.0.1', '194.63.238.4', '8.8.8.8']
        self.ltsp_ips = ['192.168.67.1', '255.255.255.0', '0.0.0.0']
        self.builder = Gtk.Builder()
        self.builder.add_from_file('ip_dialog.ui')
        self.builder.connect_signals(self)
        self.main_dlg = self.builder.get_object('main_dlg')
        self.main_dlg_notebook = self.builder.get_object('main_dlg_notebook')
        self.main_dlg.set_transient_for(parent)
        
        try:
            self.nm = Network_Manager()
        except dbus.exceptions.DBusException:
            msg = 'Αδυναμία σύνδεσης στη Διαχείριση Δικτύου.'
            dialogs.ErrorDialog(msg, 'Σφάλμα').showup()
            return
        self.settings = Settings()
        device_paths = self.nm.get_devices()
        if len(device_paths) == 0:
            msg = 'Δεν υπάρχει διαθέσιμη διεπαφή.'
            dialogs.ErrorDialog( msg, 'Σφάλμα' ).showup()
            return  
        for device_path in device_paths:
            device = Device(device_path)
            ip4config_path, interface, driver, device_type = device.get_properties()
            if device_type == 1:
                devicewired = Device_Wired(device_path)
                mac, speed, carrier = devicewired.get_properties()
                interface = Interface(ip4config_path, device_path, interface, \
                                        driver, device_type, mac, speed, carrier)
                self.interfaces.append(interface)
        if len(self.interfaces) == 0:
            msg = 'Δεν υπάρχει διαθέσιμη ενσύρματη διεπαφή.'
            dialogs.ErrorDialog( msg, 'Σφάλμα' ).showup()
            return  
        self.interfaces.sort(key=lambda interface: interface.interface)                     
        for interface in self.interfaces:
            self.populate_pages(interface) 
        self.set_default()          
        self.main_dlg.show()
     
    def populate_pages(self, interface):       
        page = Page()
        interface.page = page
        page.ip_entry.connect('changed', self.on_ip_entry_changed, interface)
        page.method_entry.connect('changed', self.on_method_entry_changed, interface)
        page.fill_entries(interface)
        if Gdk.Screen.get_default().get_height() <= 768:
            scrolledwindow = Gtk.ScrolledWindow()
            scrolledwindow.add_with_viewport(page.grid)
            scrolledwindow.show()
            self.main_dlg_notebook.append_page(scrolledwindow, Gtk.Label('Ethernet (%s)' \
                                               %interface.interface))
            self.main_dlg_notebook.set_tab_reorderable(scrolledwindow, True) 
        else:
            self.main_dlg_notebook.append_page(page.grid, Gtk.Label('Ethernet (%s)' \
                                               %interface.interface))
            self.main_dlg_notebook.set_tab_reorderable(page.grid, True) 

    def set_default(self):
        #By default active is 3
        carrier_connect = [interface.page for interface in self.interfaces \
                           if interface.carrier == 1]
        if len(carrier_connect) == 0:
            self.interfaces[0].page.method_entry.set_active(1)
            self.main_dlg_notebook.reorder_child(self.interfaces[0].page.grid, 0) 
        else:
            if carrier_connect[0].ip_entry.get_text().startswith('10.'):
                carrier_connect[0].method_entry.set_active(2)
            else:
                carrier_connect[0].method_entry.set_active(1)
            self.main_dlg_notebook.reorder_child(carrier_connect[0].grid, 0)

        if len(self.interfaces) < 2:
            for interface in self.interfaces:
                interface.page.method_entry.get_model()[3][1] = False
                
        self.main_dlg_notebook.set_current_page(0) 
        
    def watch_nm(self, interest_interfaces):
        self.timeout += 1000
        break_bool = True
        for interface in interest_interfaces:
            if interface.carrier != 1:
                continue
            #TODO: Change it (do not create new instances)   
            device = Device(interface.device_path)
            ip4config_path, interface, driver, device_type = device.get_properties()
            if ip4config_path == '/':
                break_bool = False
        
        if break_bool:
            p = subprocess.Popen(['sh', '-c', 'ltsp-config dnsmasq --overwrite'])
            p.wait()
            msg = 'Η δημιουργία των συνδέσεων καθώς και η επαναδημιουργία του ' \
                  'αρχείου ρυθμίσεων του dnsmasq έγινε επιτυχώς.'
            dialogs.InfoDialog(msg, 'Επιτυχία').showup()
            self.main_dlg.destroy() 
            return False
        elif not break_bool and self.timeout == 30000:
            msg = 'Η δημιουργία των συνδέσεων έγινε επιτυχώς αλλά η επαναδημιουργία του ' \
                  'αρχείου dnsmasq απέτυχε καθώς οι συνδέσεις δεν ενεργοποιήθηκαν.'
            dialogs.ErrorDialog(msg, 'Σφάλμα').showup()
            self.main_dlg.destroy()
            return False
        return True          
        
    def check_button(self):
        check_ip = True
        check_method = False
        for interface in self.interfaces:
            if interface.page is None:
                continue
            ip = interface.page.ip_entry.get_text()
            method = interface.page.method_entry.get_active()
            if not re.match(IP_REG, ip) and ip != 'Δεν βρέθηκε διεύθυνση':
                check_ip = False
            if method != 3:
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

        if reset_ltsp_method:
            for l_interface in self.interfaces:
                l_interface.page.method_entry.get_model()[3][1] = True         
        if interface.page.method_entry.get_active() == 0:
            interface.page.ip_entry.set_sensitive(False)
            interface.page.auto_checkbutton.set_sensitive(True)
            interface.set_ips()
            interface.page.fill_entries(interface)
        elif interface.page.method_entry.get_active() == 1:
            interface.page.ip_entry.set_sensitive(False)
            interface.page.auto_checkbutton.set_sensitive(True)
            interface.set_ips()
            interface.dnss = [dns for dns in self.ts_dns]
            interface.page.fill_entries(interface)
        elif interface.page.method_entry.get_active() == 2:
            interface.page.ip_entry.set_sensitive(True)
            interface.page.auto_checkbutton.set_sensitive(True)
            connection_settings_paths = self.settings.get_list_connections()
            if interface.page.ip_entry.get_text().startswith('10.'): 
                for counter, connection_settings_path in enumerate(connection_settings_paths):
                    connection_settings = Connection_Settings(connection_settings_path)
                    connection_settings_id = connection_settings.get_settings()['connection']['id']
                    try:
                        connection_settings_method = connection_settings.get_settings()['ipv4']['method']
                    except KeyError:
                        connection_settings_method = None
                    if connection_settings_id == interface.id and \
                       connection_settings_method == dbus.String('manual'):
                        break
                    elif counter == len(connection_settings_paths) - 1:
                        interface.ip = '.'.join(interface.page.ip_entry.get_text().split('.')[0:3])+'.10'
            interface.dnss = [dns for dns in self.ts_dns]
            interface.page.fill_entries(interface)
        elif interface.page.method_entry.get_active() == 3:
            interface.page.ip_entry.set_sensitive(False)
            interface.page.auto_checkbutton.set_sensitive(True)
            interface.ip, interface.subnet, interface.route = self.ltsp_ips
            interface.dnss = [dns for dns in self.ts_dns]
            interface.page.fill_entries(interface)
            for l_interface in self.interfaces:
                if l_interface != interface:
                    l_interface.page.method_entry.get_model()[3][1] = False
        elif interface.page.method_entry.get_active() == 4:
            interface.page.ip_entry.set_sensitive(False)
            interface.page.auto_checkbutton.set_sensitive(False)
            interface.set_ips()
            interface.page.fill_entries(interface)
        self.check_button()
        

    def on_ip_entry_changed(self, ip_entry, interface):
        if interface.page.ip_entry.get_text() != 'Δεν βρέθηκε διεύθυνση':
            ip = interface.page.ip_entry.get_text()
            sub_ip = '.'.join(interface.ip.split('.')[0:3])+'.'
            if re.match(IP_REG, ip) and ip != interface.page.route_entry.get_text():
                interface.page.ip_entry.set_icon_from_stock(1, None)               
            else:
                interface.page.ip_entry.set_position(-1)
                if ip != interface.page.route_entry.get_text():
                    interface.page.ip_entry.set_text(sub_ip)
                interface.page.ip_entry.set_icon_from_stock(1, Gtk.STOCK_DIALOG_WARNING)
                interface.page.ip_entry.set_icon_tooltip_text(1, '%s' \
                    %'Μη-έγκυρη διεύθυνση IP. θα πρέπει να είναι της μορφής x.y.z.w όπου ' \
                     'x, y, z, w παίρνουν τιμές μεταξύ του 1 και 254.')
            self.check_button()

    def on_ip_dialog_response(self, main_dlg, response):
        if response != Gtk.ResponseType.OK:
            self.main_dlg.destroy()
            return

        dnsmasq_via_carrier = False
        dnsmasq_via_autoconnect = False
        new_connections = []
        replace_connections = []
        interest_interfaces = [interface for interface in self.interfaces \
                           if interface.page.method_entry.get_active()!=4]

        for interface in interest_interfaces:
            bytes = [unhexlify(v) for v in interface.mac.split(":")]
            ethernet = dbus.Dictionary({'duplex':'full',
                                'mac-address':dbus.Array(bytes, signature=dbus.Signature('y'))}) 
            if interface.page.auto_checkbutton.get_active():   
                connection = dbus.Dictionary({'type':'802-3-ethernet',
                                'uuid':str(uuid.uuid4()),
                                'id':interface.id})
            else:
                connection = dbus.Dictionary({'type':'802-3-ethernet',
                                'uuid':str(uuid.uuid4()),
                                'id':interface.id,
                                 'autoconnect':dbus.String('false')})
            ipv6 = dbus.Dictionary({'method':'ignore'})
            if interface.page.method_entry.get_active() == 0:
                ipv4 = dbus.Dictionary({'method':'auto'})
            elif interface.page.method_entry.get_active() == 1:
                dns = dbus.Array([dbus.UInt32(string_to_int32(self.ts_dns[0])),
                                dbus.UInt32(string_to_int32(self.ts_dns[1])),
                                dbus.UInt32(string_to_int32(self.ts_dns[2]))],
                                signature=dbus.Signature('u'))
                ipv4 = dbus.Dictionary({'method':'auto',
                                'dns':dns,
                                'ignore-auto-dns':1})
            elif interface.page.method_entry.get_active() == 2 or \
                    interface.page.method_entry.get_active() == 3: 
                ip = string_to_int32(interface.page.ip_entry.get_text().strip())
                subnet = subnet_to_bits(interface.page.subnet_entry.get_text().strip())
                route = string_to_int32(interface.page.route_entry.get_text().strip())
                addresses = dbus.Array([dbus.UInt32(ip),
                                dbus.UInt32(subnet),
                                dbus.UInt32(route)],
                                signature=dbus.Signature('u'))
                dns = dbus.Array([dbus.UInt32(string_to_int32(self.ts_dns[0])),
                                dbus.UInt32(string_to_int32(self.ts_dns[1])),
                                dbus.UInt32(string_to_int32(self.ts_dns[2]))],
                                signature=dbus.Signature('u'))
                ipv4 = dbus.Dictionary({'method':'manual',
                                'addresses':dbus.Array([addresses],
                                                        signature=dbus.Signature('au')),
                                'dns':dns,
                                'dhcp-send-hostname':'false'})
           
            conn = dbus.Dictionary({'802-3-ethernet':ethernet,
                                'connection':connection,
                                'ipv4':ipv4,
                                'ipv6':ipv6})
            interface.connection = conn
            new_connections.append(interface)

            
            connection_settings_paths = self.settings.get_list_connections() 
            for connection_settings_path in connection_settings_paths:
                connection_settings = Connection_Settings(connection_settings_path)
                connection_settings_id = connection_settings.get_settings()['connection']['id']
                if connection_settings_id == interface.id:
                    interface.conflict = connection_settings
                    replace_connections.append(interface)
                    new_connections.remove(interface)
                try:
                    connection_settings_mac = ':'.join([hexlify(chr(v)) for v in \
                 connection_settings.get_settings()['802-3-ethernet']['mac-address']]).upper()
                except KeyError:
                    continue
                if interface.mac == connection_settings_mac and \
                   interface.id != connection_settings_id and \
                   interface.page.auto_checkbutton.get_active():
                    interface.interface_connections.append(connection_settings) 

        title = 'Είστε σίγουροι ότι θέλετε να συνεχίσετε;'
        msg = 'Πρόκειται '
        if len(new_connections) > 0:
            msg += 'να δημιουργήσετε '
        
            if len(new_connections) == 1: 
                msg += 'τη σύνδεση: \n\n'
            else:
                msg += 'τις συνδέσεις: \n\n'
            
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
            msg += 'να ενημερώσετε '
        
            if len(replace_connections) == 1: 
                msg += 'τη σύνδεση: \n\n'
            else:
                msg += 'τις συνδέσεις: \n\n'
        
            for interface in replace_connections:
                if interface.carrier == 1:
                    dnsmasq_via_carrier = True
                if interface.page.auto_checkbutton.get_active():
                    dnsmasq_via_autoconnect = True
                msg += '<b>%s</b> (%s)\n' %(str(interface.id), \
                    interface.page.method_lstore[interface.page.method_entry.get_active()][0]) 
        if dnsmasq_via_carrier and dnsmasq_via_autoconnect:
            msg += '\nκαι να επαναδημιουργήσετε το αρχείο ρυθμίσεων του dnsmasq;'
        elif not dnsmasq_via_carrier and dnsmasq_via_autoconnect:
            msg += '\n<b>Προσοχή:</b> Η επαναδημιουργία του αρχείου ρυθμίσεων του dnsmasq δεν ' \
                   'είναι δυνατή καθώς σε καμία διεπαφή δεν είναι συνδεδεμένο το καλώδιο.'
        
        ask_dialog = dialogs.AskDialog(title, 'Επιβεβαίωση')
        ask_dialog.format_secondary_markup(msg)
        ask_dialog.set_transient_for(self.main_dlg)
        if ask_dialog.showup() != Gtk.ResponseType.YES:    
            return
        
        self.main_dlg.hide()
        for interface in interest_interfaces:
            if interface.conflict is not None:
                interface.conflict.interface.Update(interface.connection)
                if interface.carrier == 1 and interface.page.auto_checkbutton.get_active():
                    self.nm.interface.ActivateConnection(interface.conflict.object_path, \
                        interface.device_path, '/')
            else:
                object_path = self.settings.interface.AddConnection(interface.connection)
                if interface.carrier == 1 and interface.page.auto_checkbutton.get_active():
                    self.nm.interface.ActivateConnection(object_path, interface.device_path, '/')
            
        
            for connection_settings in interface.interface_connections:
                settings = connection_settings.get_settings()
                settings['connection'][dbus.String('autoconnect')] = dbus.String('false')
                connection_settings.interface.Update(settings)

        if dnsmasq_via_carrier and dnsmasq_via_autoconnect:
            GObject.timeout_add(1000, self.watch_nm, interest_interfaces)
        else:
            msg = 'Η δημιουργία των συνδέσεων έγινε επιτυχώς.'
            dialogs.InfoDialog(msg, 'Επιτυχία').showup()
            self.main_dlg.destroy() 
