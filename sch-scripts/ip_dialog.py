#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2012 Lefteris Nikoltsios <lefteris.nikoltsios@gmail.com>, Yannis Siahos <Siahos@cti.gr>
# License GNU GPL version 3 or newer <http://gnu.org/licenses/gpl.html>

from gi.repository import Gtk
from binascii import unhexlify, hexlify
from dbus.mainloop.glib import DBusGMainLoop
import re
import subprocess
import dbus, sys
import uuid
import struct, socket
import dialogs

class Ip_Dialog:
    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file('ip_dialog.ui')
        self.builder.connect_signals(self)

        self.dialog = self.builder.get_object('ip_dialog')
        self.connection_title_label = self.builder.get_object('connection_title_label')
        self.assignment_entry = self.builder.get_object('assignment_entry')
        self.name_entry = self.builder.get_object('name_entry')
        self.interface_entry = self.builder.get_object('interface_entry')
        self.mac_entry = self.builder.get_object('mac_entry')
        self.driver_entry = self.builder.get_object('driver_entry')
        self.speed_entry = self.builder.get_object('speed_entry')
        self.ip_entry = self.builder.get_object('ip_entry')
        self.subnet_entry = self.builder.get_object('subnet_entry')
        self.gateway_entry = self.builder.get_object('gateway_entry')
        self.dns1_entry = self.builder.get_object('dns1_entry')
        self.dns2_entry = self.builder.get_object('dns2_entry')
        self.dns3_entry = self.builder.get_object('dns3_entry')
        self.label11 = self.builder.get_object('label11')
        self.label12 = self.builder.get_object('label12')
        self.label13 = self.builder.get_object('label13')
        self.ok_button = self.builder.get_object('ok_button')

        self.ip_entry.connect('changed', self.callback_ip_changed)
        self.ip = False
        self.liststore = Gtk.ListStore(str)

        '''Set glib as mainloop'''          
        DBusGMainLoop(set_as_default=True)

        '''Connect to dbus and NetworkManager'''       
        self.bus = dbus.SystemBus()
        try:
            self.nm_proxy = self.bus.get_object('org.freedesktop.NetworkManager', '/org/freedesktop/NetworkManager')
            self.nm_interface = dbus.Interface(self.nm_proxy, 'org.freedesktop.NetworkManager')         
            self.nm_interface.connect_to_signal('PropertiesChanged', self.callback_network_changed)
            self.collect_info(True)
        except dbus.exceptions.DBusException:
            msg = 'Αδυναμία σύνδεσης στη Διαχείριση Δικτύου. Ο διάλογος θα κλείσει.'
            dialogs.ErrorDialog( msg, 'Σφάλμα' ).showup()
            sys.exit(0)

    def collect_info(self, main_loop):
        '''Collect devices'''
        nm_properties = self.nm_proxy.GetAll('org.freedesktop.NetworkManager')
        if nm_properties['NetworkingEnabled'] == 1:
            devices = self.nm_interface.GetDevices()
            
            for device in devices:
                device_proxy = self.bus.get_object('org.freedesktop.NetworkManager', device)
                device_properties = device_proxy.GetAll('org.freedesktop.NetworkManager.Device')

                if device_properties['DeviceType'] == 1 and device_properties['ActiveConnection'] != "/":
                    if main_loop:
                        address_proxy = self.bus.get_object('org.freedesktop.NetworkManager', device_properties['Ip4Config'])
                        try:
                            address_properties = address_proxy.GetAll('org.freedesktop.NetworkManager.IP4Config') 
                        except dbus.exceptions.DBusException:
                            continue
                    self.liststore.append(['Ethernet (' + str(device_properties['Interface']) + ')'])

            if len(self.liststore) != 0:
                self.interface_entry.set_model(self.liststore)
                self.interface_entry.set_active(0)
                self.dialog.show()
                
            else:
                msg = 'Πρέπει να είστε συνδεδεμένος σε ένα δίκτυο. Ο διάλογος θα κλείσει.'
                dialogs.ErrorDialog( msg, 'Αποτυχία σύνδεσης' ).showup()
                if main_loop:
                    sys.exit(0)
                else:
                    Gtk.main_quit()
                
        else:
            msg = 'Η δικτύωση θα πρέπει να είναι ενεργοποιημένη. Ο διάλογος θα κλείσει.'
            dialogs.ErrorDialog( msg, 'Αποτυχία δικτύου' ).showup()
            if main_loop:
                sys.exit(0)
            else:
                Gtk.main_quit()  


## Main Callbacks

    def on_interface_entry_changed(self, widget):
        '''Handle the changes on field Interface'''

        '''
        This is needed in open/close connections because 
        callback function called by none text in combotext
        '''
        if widget.get_active_text() is None:
            return False

        #TODO:Find another way to strip interface
        interface = widget.get_active_text().replace('Ethernet (', "")
        interface = interface.replace(')', "")
        interface = interface.strip()
        self.interface = interface
        device = self.nm_interface.GetDeviceByIpIface(self.interface)
        
        device_proxy = self.bus.get_object('org.freedesktop.NetworkManager', device)
        device_properties = device_proxy.GetAll('org.freedesktop.NetworkManager.Device')        
        device_wired_properties = device_proxy.GetAll('org.freedesktop.NetworkManager.Device.Wired')

        address_proxy = self.bus.get_object('org.freedesktop.NetworkManager', device_properties['Ip4Config'])
        address_properties = address_proxy.GetAll('org.freedesktop.NetworkManager.IP4Config')
      
        driver = device_properties['Driver']
        mac = device_wired_properties['HwAddress']
        speed = str(device_wired_properties['Speed'])
        ip = self.int32_to_dotted_quad_string(address_properties['Addresses'][0][0])
        self.subnet = address_properties['Addresses'][0][1]
        subnet = self.bits_to_subnet_mask(address_properties['Addresses'][0][1])
        gateway = self.int32_to_dotted_quad_string(address_properties['Addresses'][0][2])
        self.default_dnss = ['127.0.0.1', '194.63.238.4', '8.8.8.8']
        self.dhcp_dnss= []
        for i in range(len(address_properties['Nameservers'])):       
            self.dhcp_dnss.append(self.int32_to_dotted_quad_string(address_properties['Nameservers'][i]))
        
        self.ip_sub = ".".join(self.int32_to_dotted_quad_string(address_properties['Addresses'][0][0]).split('.')[0:3])+'.'
        if ip.split('.')[0] != '10':
            self.assignment_entry.set_active(1)
        else:
            self.assignment_entry.set_active(2)
            ip = self.ip_sub+'10'      

        '''Fill entries'''
        self.connection_title_label.set_label(self.interface+',sch-scripts')
        self.name_entry.set_text(interface + ',sch-scripts')
        self.driver_entry.set_text(driver)
        self.mac_entry.set_text(mac)
        self.speed_entry.set_text(speed)
        self.ip_entry.set_text(ip)
        self.subnet_entry.set_text(subnet)

        label10 = self.builder.get_object('label10')
        self.gateway_entry.set_text(gateway)
        
        if gateway != '0.0.0.0':
            label10.set_visible(True)
            self.gateway_entry.set_visible(True)
        else:
            label10.set_visible(False)
            self.gateway_entry.set_visible(False)

        self.fill_dns()

        self.ip = True
        self.check_button() 

    def on_assignment_entry_changed(self, widget):
        '''Handle the changes on field Method'''
        if self.assignment_entry.get_active() != 2:
            self.ip_entry.set_sensitive(False) 
        else:
            self.ip_entry.set_sensitive(True)
        self.fill_dns()
 
    def on_ok_button_clicked(self, widget):
        '''Make the configuration file in /etc/NetworkManager/system-connections'''
        add_new_connection = True

        '''Read values from dialog'''
        name = self.name_entry.get_text().strip()
        interface = self.interface
        mac = self.mac_entry.get_text().strip()
        driver = self.driver_entry.get_text().strip()
        speed = self.speed_entry.get_text().strip()
        ip = self.dotted_quad_string_to_int32(self.ip_entry.get_text().strip())
        subnet = str(self.subnet) + 'L'
        if self.gateway_entry.get_visible():
            gateway = self.dotted_quad_string_to_int32(self.gateway_entry.get_text().strip())
        if self.dns1_entry.get_visible():
            dns1 = self.dotted_quad_string_to_int32(self.dns1_entry.get_text().strip())
        if self.dns2_entry.get_visible():
            dns2 = self.dotted_quad_string_to_int32(self.dns2_entry.get_text().strip())
        if self.dns1_entry.get_visible():
            dns3 = self.dotted_quad_string_to_int32(self.dns3_entry.get_text().strip())

        msg = '''Θα δημιουργηθεί μια νέα σύνδεση με όνομα '%s' και θα γίνει επαναδημιουργία των ρυθμίσεων του dnsmasq.''' %(name)
        response = dialogs.AskDialog( msg, 'Θέλετε να συνεχίσετε;' ).showup()
        if response == Gtk.ResponseType.YES:
            bytes = [unhexlify(v) for v in mac.split(":")]
            s_wired = dbus.Dictionary({'duplex':'full',
                                'mac-address':dbus.Array(bytes, signature=dbus.Signature('y'))})    
            s_con = dbus.Dictionary({'type':'802-3-ethernet',
                                'uuid':str(uuid.uuid4()),
                                'id':name})
            s_ip6 = dbus.Dictionary({'method':'ignore'})

            
            if self.assignment_entry.get_active() == 0:
                s_ip4 = dbus.Dictionary({'method':'auto'})
            elif self.assignment_entry.get_active() == 1:
                dns = dbus.Array([dbus.UInt32(dns1),
                                dbus.UInt32(dns2),
                                dbus.UInt32(dns3)],
                                signature=dbus.Signature('u'))
                s_ip4 = dbus.Dictionary({'method':'auto',
                                'dns':dns,
                                'ignore-auto-dns':1})
            elif self.assignment_entry.get_active() == 2: 
                addr = dbus.Array([dbus.UInt32(ip),
                                dbus.UInt32(subnet),
                                dbus.UInt32(gateway)],
                                signature=dbus.Signature('u'))
                dns = dbus.Array([dbus.UInt32(dns1),
                                dbus.UInt32(dns2),
                                dbus.UInt32(dns3)],
                                signature=dbus.Signature('u'))
                s_ip4 = dbus.Dictionary({'method':'manual',
                                'addresses':dbus.Array([addr], signature=dbus.Signature('au')),
                                'dns':dns,
                                'dhcp-send-hostname':'false'})
           
            con = dbus.Dictionary({'802-3-ethernet':s_wired,
                                'connection':s_con,
                                'ipv4':s_ip4,
                                'ipv6':s_ip6})

     
            setting_proxy = self.bus.get_object('org.freedesktop.NetworkManager', '/org/freedesktop/NetworkManager/Settings')
            settings_interface = dbus.Interface(setting_proxy, 'org.freedesktop.NetworkManager.Settings')
            for setting in settings_interface.ListConnections():
                connection_proxy = self.bus.get_object('org.freedesktop.NetworkManager', setting)
                connection_interface = dbus.Interface(connection_proxy, 'org.freedesktop.NetworkManager.Settings.Connection')
                connection_settings = connection_interface.GetSettings()
                print connection_settings
            
                '''For every connection to this eth disable autoconnect'''
                try:
                    if mac == ':'.join([hexlify(chr(v)) for v in connection_settings['802-3-ethernet']['mac-address']]).upper():
                        connection_settings['connection'][dbus.String('autoconnect')] = dbus.String('false') 
                        connection_interface.Update(connection_settings)
                except KeyError:
                    pass


                '''Update connection'''                
                if connection_settings['connection']['id'] == name:
                    connection_interface.Update(con)
                    con = setting
                    add_new_connection = False
                
            
            subprocess.Popen(['sh', '-c', 'ltsp-config dnsmasq --overwrite'])
            msg = 'Η σύνδεση δημιουργήθηκε. Θέλετε να ενεργοποιηθεί τώρα;'
            response = dialogs.AskDialog( msg, 'Ενεργοποιήση καινούριας σύνδεσης' ).showup()
            if response == Gtk.ResponseType.YES:
                device = self.nm_interface.GetDeviceByIpIface(self.interface)
                if add_new_connection:
                    self.nm_interface.AddAndActivateConnection(con, device, '/')
                else:
                    self.nm_interface.ActivateConnection(con, device, '/')
            else:
                if add_new_connection:
                    settings_interface.AddConnection(con)
            Gtk.main_quit()
        else:
            return False     

    def on_cancel_button_clicked(self, widget):
        '''Close dialog on cancel button event'''
        Gtk.main_quit()

    def on_ip_dialog_delete_event(self, widget, event):
        '''Close dialog on exit dialog event'''
        Gtk.main_quit()


## Callbacks

    def callback_ip_changed(self, widget):
        '''Handle the changes on fields IP Address and Name'''
        if self.assignment_entry.get_active() == 2:
            reg = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([1-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-4])$"
            new_ip = widget.get_text()
            if new_ip[0:len(".".join(new_ip.split(".")[0:3]))+1] != self.ip_sub:
                widget.set_text(self.ip_sub)
                widget.set_position(-1)
                new_ip = self.ip_sub
            if re.match(reg, new_ip) and new_ip != self.gateway_entry.get_text():
                self.ip = True
                widget.set_icon_from_stock(1, None) 
            else:
                self.ip = False
                widget.set_icon_from_stock(1, Gtk.STOCK_DIALOG_WARNING)
                widget.set_icon_tooltip_text(1, 'Μη-έγκυρη διεύθυνση IP. Πρέπει να επεξεργαστείτε τη διεύθυνση IP της σύνδεσης.')
            self.check_button()           
            return True
    
    def callback_network_changed(self, event):
        '''Handle NetworkManager changes'''
        self.dialog.hide()
        self.liststore.clear()
        self.collect_info(False)
        return True


## Useful functions

    def fill_dns(self):
        '''Fill dns entries'''
        if self.assignment_entry.get_active() != 0:
            self.dns1_entry.set_text(self.default_dnss[0])
            self.dns1_entry.set_visible(True)
            self.label11.set_visible(True)
            self.dns2_entry.set_text(self.default_dnss[1])
            self.dns2_entry.set_visible(True)
            self.label12.set_visible(True)
            self.dns3_entry.set_text(self.default_dnss[2])
            self.dns3_entry.set_visible(True)
            self.label13.set_visible(True)
        else:
            try:
                self.dns1_entry.set_text(self.dhcp_dnss[0])
            except:
                self.dns1_entry.set_visible(False)
                self.label11.set_visible(False)

            try:
                self.dns2_entry.set_text(self.dhcp_dnss[1])
            except:
                self.dns2_entry.set_visible(False)
                self.label12.set_visible(False)
            
            try:
                self.dns3_entry.set_text(self.dhcp_dnss[2])
            except:
                self.dns3_entry.set_visible(False)
                self.label13.set_visible(False)
        return True
    
    def check_button(self):
        '''Make active the button OK'''
        if self.ip: 
            self.ok_button.set_sensitive(True)
        else:
            self.ok_button.set_sensitive(False)
        return True


    def dotted_quad_string_to_int32(self, address):
        '''Convert ip to int32'''
        return struct.unpack("L",socket.inet_aton(address))[0]

   
    def int32_to_dotted_quad_string(self, num):
        '''Convert int32 to ip'''
        return socket.inet_ntoa(struct.pack("L",num))


    def bits_to_subnet_mask(self, bits):
        '''Convert bits to subnet mask'''
        try:
            bits=int(bits)
            if bits<=0 or bits>32:
                raise Exception
        except:
            return "255.255.255.255"
        num = ((1L<<bits)-1L)<<(32L-bits)
        return socket.inet_ntoa(struct.pack("!L",num))
    

if __name__ == '__main__':
    ip_dialog = Ip_Dialog()
    Gtk.main()  
