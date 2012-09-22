#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2012 Lefteris Nikoltsios <lefteris.nikoltsios@gmail.com>
# Copyright (C) 2012 Yannis Siahos <Siahos@cti.gr>
# License GNU GPL version 3 or newer <http://gnu.org/licenses/gpl.html>

from gi.repository import Gtk, Gdk
from binascii import unhexlify
from dbus.mainloop.glib import DBusGMainLoop
import re
import subprocess
import dbus, sys
import uuid
import struct, socket


class Ip_Dialog:
    def __init__(self):
        gladefile = "ip_dialog.ui"
        self.builder = Gtk.Builder()
        self.builder.add_from_file(gladefile)
        self.builder.connect_signals(self)
        self.dialog = self.builder.get_object("dialog1")
        self.address = False
        self.name = False
        self.info = {}
        self.liststore = Gtk.ListStore(str)
        
        """Set glib as mainloop"""        
        DBusGMainLoop(set_as_default=True)
        
        """Connect to dbus and NetworkManager"""        
        self.bus = dbus.SystemBus()
        try:
            self.proxy = self.bus.get_object("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager")
            self.nm_interface = dbus.Interface(self.proxy, "org.freedesktop.NetworkManager")         
            self.signal = self.nm_interface.connect_to_signal("PropertiesChanged", self.NetworkChanged)
            self.Collect_Info(True)
        except dbus.exceptions.DBusException:
            text = "Αδυναμία σύνδεσης στη Διαχείριση Δικτύου"
            secondary_text = "Ο διάλογος θα κλείσει."
            self.Dialog(text, "Σφάλμα", "error", secondary_text)
            sys.exit()
            

    def Ok(self, widget):
        """
        Make the configuration file in /etc/NetworkManager/system-connections
        """
        add = True
        """Update the name from dialog"""
        self.info["name"] = self.name_entry.get_text()
        text = "Θέλετε να συνεχίσετε;"
        secondary_text = """Θα δημιουργηθεί μια νέα σύνδεση με όνομα "%s", θα γίνει επανεκκίνηση της υπηρεσίας Διαχείρισης Δικτύου και επαναδημιουργία των ρυθμίσεων του dnsmasq. Η σύνδεση θα διακοπεί για λίγα δευτερόλεπτα.""" %(self.info["name"])
        response = self.Dialog(text, "Επιβεβαίωση", "question", secondary_text)
        if response == Gtk.ResponseType.YES:
            bytes = [unhexlify(v) for v in self.info["hwaddress"].split(":")]
            s_wired = dbus.Dictionary({'duplex':'full',
                          'mac-address':dbus.Array(bytes, signature=dbus.Signature('y'))})    
            s_con = dbus.Dictionary({'type':'802-3-ethernet',
                        'uuid':str(uuid.uuid4()),
                        'id':self.info["name"]}) 
            address = self.Dotted_Quad_String_To_Int32(self.info["address"])
            prefix = self.info["prefix"] + 'L'
            gateway = self.Dotted_Quad_String_To_Int32(self.info["gateway"])
            addr = dbus.Array([dbus.UInt32(address),
                        dbus.UInt32(prefix),
                        dbus.UInt32(gateway)],
                        signature=dbus.Signature('u')) 
            primary_dns = self.Dotted_Quad_String_To_Int32("127.0.0.1")
            secondary_dns = self.Dotted_Quad_String_To_Int32("194.63.238.4")
            third_dns = self.Dotted_Quad_String_To_Int32("8.8.8.8")            
            dns = dbus.Array([dbus.UInt32(primary_dns),
                       dbus.UInt32(secondary_dns),
                       dbus.UInt32(third_dns)],
                       signature=dbus.Signature('u'))
            s_ip4 = dbus.Dictionary({'method':'manual',
                        'addresses':dbus.Array([addr], signature=dbus.Signature('au')),
                        'dns':dns,
                        'dhcp-send-hostname':'false'})
            s_ip6 = dbus.Dictionary({'method':'ignore'})
            con = dbus.Dictionary({'802-3-ethernet':s_wired,
                      'connection':s_con,
                      'ipv4':s_ip4,
                      'ipv6':s_ip6})
            bus = dbus.SystemBus()
            proxy = bus.get_object("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager/Settings")
            settings = dbus.Interface(proxy, "org.freedesktop.NetworkManager.Settings")
            for setting in settings.ListConnections():
                proxy = bus.get_object("org.freedesktop.NetworkManager", setting)
                connection = dbus.Interface(proxy, "org.freedesktop.NetworkManager.Settings.Connection")
                connection_settings = connection.GetSettings()
                if connection_settings["connection"]["id"] == self.info["name"]:
                    text = "Αυτή η σύνδεση υπάρχει ήδη. Θα θέλατε να ενημερώσετε τις πληροφορίες της;"
                    secondary_text = """Αν επιλέξετε "Όχι" θα πρέπει να αλλάξετε το όνομα της σύνδεσης."""
                    response = self.Dialog(text, "Σύγκρουση", "question", secondary_text)
                    if response == Gtk.ResponseType.YES:
                        connection.Update(con)
                        add = False
                    else:
                        return False
            if add:
                settings.AddConnection(con)

            #Wrong logic but it works
            subprocess.Popen(['sh', '-c',
                'ltsp-config dnsmasq --overwrite && service network-manager restart'])

            
            text = "Η νέα σύνδεση με όνομα %s δημιουργήθηκε" %(self.info["name"])
            secondary_text = "Ο διάλογος θα κλείσει."
            self.Dialog(text, "Ειδοποίηση", "info", secondary_text)
            self.Quit()
        else:
            return False
        

    def Quit(self, widget=None, event=None):
        """
        Close the dialog
        """
        self.signal.remove()
        self.dialog.destroy()
        Gtk.main_quit()
        

    def Collect_Info(self, main_loop):
        """
        Collect devices
        """
        properties = self.proxy.GetAll("org.freedesktop.NetworkManager")
        if properties["NetworkingEnabled"] == 1:
            devices = self.nm_interface.GetDevices()

            for device in devices:
                device_proxy = self.bus.get_object("org.freedesktop.NetworkManager", device)
                device_properties = device_proxy.GetAll("org.freedesktop.NetworkManager.Device")

                if device_properties["DeviceType"] == 1 and device_properties["ActiveConnection"] != "/":
                    if main_loop:
                        address_proxy = self.bus.get_object("org.freedesktop.NetworkManager", device_properties["Ip4Config"])
                        try:
                            address_properties = address_proxy.GetAll("org.freedesktop.NetworkManager.IP4Config") 
                        except dbus.exceptions.DBusException:
                            continue
                    listitem = "Ethernet (" + str(device_properties["Interface"]) + ")"
                    self.liststore.append([listitem])

            if len(self.liststore) != 0:
                interface_entry = self.builder.get_object("entry1")
                interface_entry.connect("changed", self.ComboChanged)
                interface_entry.set_model(self.liststore)
                interface_entry.set_active(0)
                self.dialog.show()
                
            else:
                text = "Αποτυχία σύνδεσης"
                secondary_text = "Πρέπει να είστε συνδεδεμένος σε ένα δίκτυο. Ο διάλογος θα κλείσει."
                self.Dialog(text, "Σφάλμα", "error", secondary_text)
                if main_loop:
                    self.signal.remove()
                    sys.exit()
                else:
                    self.Quit()

        else:
            text = "Αποτυχία δικτύου"
            secondary_text = "Η δικτύωση θα πρέπει να είναι ενεργοποιημένη. Ο διάλογος θα κλείσει."
            self.Dialog(text, "Σφάλμα", "error", secondary_text)
            if main_loop:
                self.signal.remove()
                sys.exit()
            else:
                self.Quit()   
 
        
    def NetworkChanged(self, event):
        """
        Handle NetworkManager changes
        """
        self.liststore.clear()
        self.Collect_Info(False)

            
    def Region(self, widget, event):
        """
        Select all text in an entry
        """
        widget.select_region(0,-1)
        return True

    
    def ComboChanged(self, widget):
        """
        Handle the changes on fields Interface
        """

        """
        This is needed in open/close connections because 
        callback function called by none text in combotext
        """
        if widget.get_active_text() is None:
            return False

        #TODO:Find another way to strip interface
        interface = widget.get_active_text().replace("Ethernet (", "")
        interface = interface.replace(")", "")
        interface = interface.strip()
        device = self.nm_interface.GetDeviceByIpIface(interface)
        self.info["interface"] = interface
        
        device_proxy = self.bus.get_object("org.freedesktop.NetworkManager", device)
        device_properties = device_proxy.GetAll("org.freedesktop.NetworkManager.Device")        
        device_wired_properties = device_proxy.GetAll("org.freedesktop.NetworkManager.Device.Wired")
        

        address_proxy = self.bus.get_object("org.freedesktop.NetworkManager", device_properties["Ip4Config"])
        address_properties = address_proxy.GetAll("org.freedesktop.NetworkManager.IP4Config")
      
        driver = device_properties["Driver"]
        driver_entry = self.builder.get_object("entry3")
        driver_entry.set_text(driver)
        self.info["driver"] = driver 

        hwaddress = device_wired_properties["HwAddress"]
        hwaddress_entry = self.builder.get_object("entry2")
        hwaddress_entry.set_text(hwaddress)
        self.info["hwaddress"] = hwaddress

        speed = str(device_wired_properties["Speed"])
        speed_entry = self.builder.get_object("entry4")
        speed_entry.set_text(speed)
        self.info["speed"] = speed
        
        gateway = self.Int32_To_Dotted_Quad_String(address_properties["Addresses"][0][2])
        gateway_entry = self.builder.get_object("entry9")
        gateway_entry.set_text(gateway)
        self.info["gateway"] = gateway

        self.address_sub = ".".join(self.Int32_To_Dotted_Quad_String(address_properties["Addresses"][0][0]).split(".")[0:3])+"."
        address = self.address_sub+"10"
        address_entry = self.builder.get_object("entry6")
        address_entry.set_text(address)
        address_entry.connect("focus-in-event", self.Region)
        address_entry.connect("changed", self.Changed, "address")
        self.info["address"] = address  
        self.address = True 
        
        subnet = self.Bits_To_Subnet_Mask(address_properties["Addresses"][0][1])
        subnet_entry = self.builder.get_object("entry8")
        subnet_entry.set_text(subnet) 
        self.info["prefix"] = str(address_properties["Addresses"][0][1])
        

        self.page_title_label = self.builder.get_object("label2")
        self.page_title_label.set_label(interface+","+address)
        
        self.name_entry = self.builder.get_object("entry5")
        self.name_entry.set_text(interface+","+address)
        self.name_entry.connect("focus-in-event", self.Region)
        self.name_entry.connect("changed", self.Changed, "name")  
        self.info["name"] = interface+","+address
        self.name = True
        self.Auto_Suggest()

        dns_entry_1 = self.builder.get_object("entry10")
        dns_entry_1.set_text("127.0.0.1")
    
        dns_entry_2 = self.builder.get_object("entry11")
        dns_entry_2.set_text("194.63.238.4")

        dns_entry_3 = self.builder.get_object("entry12")
        dns_entry_3.set_text("8.8.8.8")
        self.Check_Button()           


    def Changed(self, widget, mode):
        """
        Handle the changes on fields IP Address and Name
        """
        if mode == "address":
            reg = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([1-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-4])$"
            new_ip = widget.get_text()
            if new_ip[0:len(".".join(new_ip.split(".")[0:3]))+1] != self.address_sub:
                widget.set_text(self.address_sub)
                widget.set_position(-1)
                new_ip = self.address_sub
            if re.match(reg, new_ip) and new_ip != self.info["gateway"]:
                self.address = True
                self.info["address"] = new_ip
                self.info["name"] = self.info["interface"]+","+widget.get_text()
                self.Auto_Suggest()
                widget.set_icon_from_stock(1, None)
                self.name_entry.set_sensitive(True)  
            else:
                self.address = False
                widget.set_icon_from_stock(1, Gtk.STOCK_DIALOG_WARNING)
                widget.set_icon_tooltip_text(1, "Μη-έγκυρη διεύθυνση IP. Πρέπει να επεξεργαστείτε τη διεύθυνση IP της σύνδεσης")
                self.name_entry.set_sensitive(False)
            if self.name_entry.get_text().startswith("%s,%s" %(self.info["interface"], self.address_sub)):
                self.page_title_label.set_label(self.info["interface"]+","+new_ip)
                self.name_entry.set_text(self.info["interface"]+","+new_ip)
        elif mode == "name":
            new_name = widget.get_text()
            if len(new_name)!=0 and new_name[0]!=" ":
                self.name = True
                self.info["name"] = new_name
                widget.set_icon_from_stock(1, None)
            else: 
                self.name = False          
                widget.set_icon_from_stock(1, Gtk.STOCK_DIALOG_WARNING)
                widget.set_icon_tooltip_text(1, "Μη-έγκυρο όνομα. Πρέπει να επεξεργαστείτε το όνομα της σύνδεσης")
            self.page_title_label.set_label(widget.get_text())
        self.Check_Button()           
        return True
        
     
    def Dialog(self, text, title, kind, secondary_text):
        """
        Define message dialogs
        """
        if kind == "error":
            dialog = Gtk.MessageDialog(self.dialog, Gtk.DialogFlags.MODAL,
                                       Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, text)
        elif kind == "info":
            dialog = Gtk.MessageDialog(self.dialog, Gtk.DialogFlags.MODAL,
                                       Gtk.MessageType.INFO, Gtk.ButtonsType.OK, text)
        elif kind == "question":
            dialog = Gtk.MessageDialog(self.dialog, Gtk.DialogFlags.MODAL,
                                       Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO, text)
        dialog.set_property("secondary-text", secondary_text)    
        dialog.set_title(title)
        response = dialog.run()
        dialog.destroy()
        return response


    def Check_Button(self):
        """
        Make active the button OK
        """
        button = self.builder.get_object("button1")
        if self.address and self.name: 
            button.set_sensitive(True)
        else:
            button.set_sensitive(False)
        return True


    def Auto_Suggest(self):
        """
        Make the auto suggest
        """
        liststore = Gtk.ListStore(str)
        liststore.append([self.info["name"]])
        completion = Gtk.EntryCompletion()
        completion.set_model(liststore)
        completion.set_text_column(0)
        self.name_entry.set_completion(completion)
        return True


    def Dotted_Quad_String_To_Int32(self, address):
        """
        Convert ip to int32
        """
        return struct.unpack("L",socket.inet_aton(address))[0]


    def Int32_To_Dotted_Quad_String(self, num):
        """
        Convert int32 to ip     
        """
        return socket.inet_ntoa(struct.pack("L",num))


    def Bits_To_Subnet_Mask(self, bits):
        """
        Convert bits to subnet mask
        """
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
