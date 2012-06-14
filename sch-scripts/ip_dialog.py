#!/usr/bin/python
# -*- coding: utf-8 -*-

from gi.repository import Gtk, Gdk
from binascii import unhexlify
import re
import subprocess
import dbus
import uuid
import struct, socket


class Ip_Dialog:
    def __init__(self):
        gladefile = "ip_dialog.ui"
        self.address = False
        self.name = False
        self.builder = Gtk.Builder()
        self.builder.add_from_file(gladefile)
        dic = {"on_dialog_destroy":self.Exit,
               "on_ok":self.Ok,
               "on_cancel":self.Cancel}
        self.builder.connect_signals(dic)
        self.dialog = self.builder.get_object("dialog1")
        self.Run_NM_Tools(["nm-tool"])

    def Exit(self, widget, event):
        """
        Otherwise we can user widget.destroy()
        """
        self.dialog.destroy()

    def Ok(self, widget):
        """
        Make the configuration file in /etc/NetworkManager/system-connections
        """
        add = True
        """Update the name from dialog"""
        self.info["name"] = self.name_entry.get_text()
        text = "Θέλετε να συνεχίσετε;"
        secondary_text = """Θα δημιουργηθεί μία νέα σύνδεση με όνομα "%s".""" %(self.info["name"])
        response = self.Dialog(text, "Επιβεβαίωση", "question", secondary_text)
        if response == Gtk.ResponseType.YES:
            bytes = [unhexlify(v) for v in self.info["hwaddress"].split(":")]
            s_wired = dbus.Dictionary({'duplex':'full',
                          'mac-address':dbus.Array(bytes, signature=dbus.Signature('y'))})    
            s_con = dbus.Dictionary({'type':'802-3-ethernet',
                        'uuid':str(uuid.uuid4()),
                        'id':self.info["name"]}) 
            address = str(struct.unpack('L',socket.inet_aton(self.info["address"]))[0]) + 'L'
            prefix = self.info["prefix"] + 'L'
            gateway = str(struct.unpack('L',socket.inet_aton(self.info["gateway"]))[0]) + 'L'
            addr = dbus.Array([dbus.UInt32(address),
                        dbus.UInt32(prefix),
                        dbus.UInt32(gateway)],
                        signature=dbus.Signature('u')) 
            primary_dns = str(struct.unpack('L',socket.inet_aton("127.0.0.1"))[0]) + 'L'
            secondary_dns = str(struct.unpack('L',socket.inet_aton("194.63.238.4"))[0]) + 'L'
            third_dns = str(struct.unpack('L',socket.inet_aton("8.8.8.8"))[0]) + 'L'            
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
            self.dialog.destroy()
        else:
            return False
        

    def Cancel(self, widget):
        """
        Otherwise we can use widget.get_parent() three times to find dialog object
        and then parent.destroy()
        """
        self.dialog.destroy()

    def Run_NM_Tools(self, cmdline):
        """
        Collect connection informations
        """
        self.info = {}
        bool_state = False
        con_state = False
        con_device = False        
        cmdline = [str(s) for s in cmdline]
        p = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        res = p.wait()
        if res == 0:
            response = p.stdout.read().split("\n")
            for item in response:
                if item != "":
                    item = item.split(":")
                    if item[0].strip() == "State" and not bool_state:
                        bool_state = True
                        if (item[1].strip()).find("disconnected") != -1:
                            text = "Αποτυχία σύνδεσης"
                            secondary_text = "Πρέπει να είστε συνδεδεμένος σε ένα δίκτυο. Ο διάλογος θα κλείσει."
                            self.Dialog(text, "Σφάλμα", "error", secondary_text)
                            self.dialog.destroy()
                        else:
                            con_state = True

                    if con_state:
                        if item[0].find("Device") != -1:
                            info = ((item[1].replace("-","")).strip()).split(" ",1)
                            device = info[0]
                            if device != "eth0":
                                text = "Αποτυχία ενσύρματης σύνδεσης"
                                secondary_text = "Πρέπει να ρυθμίσετε μια ενσύρματη σύνδεση. διάλογος θα κλείσει."
                                self.Dialog(text, "Σφάλμα", "error", secondary_text)
                                self.dialog.destroy()
                            else:
                                con_device = True
                                device_entry = self.builder.get_object("entry1")
                                device_entry.set_text("Ethernet ("+device+")") 
                                self.info["device"] = device

            if con_state and con_device: 
                for item in response:
                    if item != "":
                        item = item.split(":")
                        if item[0].strip() == "HW Address":
                            hwaddress = (":".join(item[1:len(item)])).strip()
                            hwaddress_entry = self.builder.get_object("entry2")
                            hwaddress_entry.set_text(hwaddress)
                            self.info["hwaddress"] = hwaddress
                        elif item[0].strip() == "Driver":
                            driver = item[1].strip()
                            driver_entry = self.builder.get_object("entry3")
                            driver_entry.set_text(driver)
                            self.info["driver"] = driver
                        elif item[0].strip() == "Speed":
                            speed = item[1].strip()
                            speed_entry = self.builder.get_object("entry4")
                            speed_entry.set_text(speed)
                            self.info["speed"] = speed
                        elif item[0].strip() == "Address":
                            address = "10.160.31.10"
                            address_entry = self.builder.get_object("entry6")
                            address_entry.set_text(address)
                            address_entry.connect("focus-in-event", self.Region)
                            address_entry.connect("changed", self.Changed, "address")
                            self.info["address"] = address  
                            self.address = True   
                        elif item[0].strip() == "Prefix":
                            reg = "\((.+)\)"
                            prefix = item[1].strip() 
                            subnet_mask = (re.search(reg, prefix)).group(1)
                            prefix = re.sub(reg,"", prefix)
                            prefix_entry = self.builder.get_object("entry8")
                            prefix_entry.set_text(subnet_mask)
                            self.info["prefix"] = prefix.strip()
                        elif item[0].strip() == "Gateway":
                            gateway = item[1].strip()
                            gateway_entry = self.builder.get_object("entry9")
                            gateway_entry.set_text(gateway)
                            self.info["gateway"] = gateway
                self.page_title_label = self.builder.get_object("label2")
                self.page_title_label.set_label(device+","+address)
                self.name_entry = self.builder.get_object("entry5")
                self.name_entry.set_text(device+","+address)
                self.name_entry.connect("focus-in-event", self.Region)
                self.name_entry.connect("changed", self.Changed, "name")  
                self.info["name"] = device+","+address
                self.name = True
                self.Auto_Suggest()
                dns_entry_1 = self.builder.get_object("entry10")
                dns_entry_1.set_text("127.0.0.1")
                dns_entry_2 = self.builder.get_object("entry11")
                dns_entry_2.set_text("194.63.238.4")
                dns_entry_3 = self.builder.get_object("entry12")
                dns_entry_3.set_text("8.8.8.8")
                self.Check_Button()
      
        else:
            text = "Σφάλμα κατά την εκτέλεση του 'nm-tool'"
            secondary_text = p.stderr.read()
            self.Dialog(text, "Σφάλμα", "error", secondary_text)
            self.dialog.destroy()


    def Region(self, widget, event):
        """
        Select all text in an entry
        """
        widget.select_region(0,-1)
        return True


    def Changed(self, widget, mode):
        """
        Handle the changes on fields IP Address and Name
        """
        if mode == "address":
            reg = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([1-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-4])$"
            new_ip = widget.get_text()
            if new_ip[0:10] != "10.160.31.":
                widget.set_text("10.160.31.")
                widget.set_position(-1)
                new_ip = "10.160.31."
            if re.match(reg, new_ip):
                self.address = True
                self.info["address"] = new_ip
                self.info["name"] = self.info["device"]+","+widget.get_text()
                self.Auto_Suggest()
                widget.set_icon_from_stock(1, None)
                self.name_entry.set_sensitive(True)  
            else:
                self.address = False
                widget.set_icon_from_stock(1, Gtk.STOCK_DIALOG_WARNING)
                widget.set_icon_tooltip_text(1, "Μη-έγκυρη διεύθυνση IP. Πρέπει να επεξεργαστείτε τη διεύθυνση IP της σύνδεσης")
                self.name_entry.set_sensitive(False)
            if self.name_entry.get_text().startswith("eth0,10.160.31."):
                self.page_title_label.set_label(self.info["device"]+","+new_ip)
                self.name_entry.set_text(self.info["device"]+","+new_ip)
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
            dialog = Gtk.MessageDialog(self.builder.get_object("dialog1"), Gtk.DialogFlags.MODAL,
                                       Gtk.MessageType.WARNING, Gtk.ButtonsType.OK, text)
        elif kind == "question":
            dialog = Gtk.MessageDialog(self.builder.get_object("dialog1"), Gtk.DialogFlags.MODAL,
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


if __name__ == "__main__":
    interface = Ip_Dialog()
    Gtk.main()
