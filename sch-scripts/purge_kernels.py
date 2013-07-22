#!/usr/bin/python
# -*- coding:utf-8 -*-
# Copyright (C) 2012 Lefteris Nikoltsios <lefteris.nikoltsios@gmail.com>, Yannis Siahos <Siahos@cti.gr>
# License GNU GPL version 3 or newer <http://gnu.org/licenses/gpl.html>

from gi.repository import Gtk, Gdk, GObject
from apt.progress.base import InstallProgress
import threading, apt, math, re, os, gc
import dialogs

#Initialize threads
GObject.threads_init()
Gdk.threads_init()

class PurgeKernels:
    _instance = None
    def __init__(self, parent=None):
        PurgeKernels._instance = self      
        self.builder = Gtk.Builder()
        self.builder.add_from_file('purge_kernels.ui')
        self.builder.connect_signals(self)
        self.main_dialog = self.builder.get_object('main_dialog')
        self.main_dialog.set_transient_for(parent) 
        self.confirm_dialog = self.builder.get_object('confirm_dialog')
        self.confirm_dialog.set_transient_for(self.main_dialog)
        self.main_treestore = self.builder.get_object('main_treestore')
        self.confirm_treestore = self.builder.get_object('confirm_treestore')
        self.confirm_treeview = self.builder.get_object('confirm_treeview')
        self.confirm_label_2 = self.builder.get_object('confirm_label_2')
        self.confirm_progressbar = self.builder.get_object('confirm_progressbar')
        self.main_purge = self.builder.get_object('main_purge')
        self.main_cancel = self.builder.get_object('main_cancel')
        self.confirm_yes = self.builder.get_object('confirm_yes')
        self.confirm_no = self.builder.get_object('confirm_no')
        self.cache = apt.Cache()
        if not self.populate_treeview():
            self.clean_mem()
            return                
        self.main_dialog.show()

    '''
    Find kernels and headers and add them to the treestore
    '''
    def populate_treeview(self):
        current_kernel = os.uname()[2]
        variants = []
        
        kernels_headers = [i for i in self.cache if (i.shortname.startswith('linux-image-') or i.shortname.startswith('linux-headers-')) and i.is_installed]
        
        kernels = [i for i in kernels_headers if i.shortname.startswith('linux-image-')]
        headers = [i for i in kernels_headers if i.shortname.startswith('linux-headers-')]

        kernels.sort(key= lambda x: x.installed, reverse=True)

        for kernel in kernels:
            version_variant = kernel.shortname.replace('linux-image-', '')
            variant = re.sub(r'([0-9].*[0-9])', '', version_variant).strip('-') 
            version = version_variant.replace(variant, '').strip('-')
            
            if version == "" or variant == "" or kernel.installed.source_name == 'linux-meta':
                continue
            if version_variant != current_kernel and variant in variants:
                size = self.convert_bytes(abs(kernel.installed.installed_size))
                self.main_treestore.append(None, [True, kernel.shortname, size, True, version]) 
            else:
                variants.append(variant)

        if len(self.main_treestore) == 0:
            msg = 'Δεν υπάρχουν παλιοί kernels ή headers για διαγραφή.'
            dialogs.InfoDialog(msg, 'Πληροφορία').showup()
            return False

        for header in headers:
            version_variant = header.shortname.replace('linux-headers-', '')
            variant = re.sub(r'([0-9].*[0-9])', '', version_variant).strip('-') 
            version = version_variant.replace(variant, '').strip('-')

            if version == '' or header.installed.source_name == 'linux-meta':
                continue
            for row in self.main_treestore:
                if version == row[4]:
                    size = self.convert_bytes(abs(header.installed.installed_size)) 
                    self.main_treestore.append(row.iter, [True, header.shortname, size, False, version])
        return True
            
    '''
    Callbacks
    '''
    def on_selecttoggle_toggled(self, widget, path):
        self.main_treestore[path][0] = not self.main_treestore[path][0]
        
        if not self.main_treestore[path][0]:
            for row_child in self.main_treestore[path].iterchildren():
                row_child[0] = False   
        else:
            for row_child in self.main_treestore[path].iterchildren():
                row_child[0] = True 
        
        all_uncheck = True
        for row in self.main_treestore:
            if row[0]:
                all_uncheck = False

        if all_uncheck:
            self.main_purge.set_sensitive(False)
        else:
            self.main_purge.set_sensitive(True)

    def on_main_dialog_delete_event(self, widget, event):
        self.clean_mem()
        self.main_dialog.destroy()

    def on_main_purge_pressed(self, widget):
        self.cache.clear()
        self.confirm_treestore.clear()
        for row_parent in self.main_treestore:
            if row_parent[0]:
                self.cache[row_parent[1]].mark_delete(purge=True)
                row = self.confirm_treestore.append(None, [row_parent[1]])
                for row_child in row_parent.iterchildren():
                    if row_child[0]:
                        self.cache[row_child[1]].mark_delete(purge=True)
                        self.confirm_treestore.append(row, [row_child[1]])
        
        size = self.convert_bytes(abs(self.cache.required_space))
        label = 'Μετά από αυτή τη λειτουργία, %s χώρου στο δίσκο θα ελευθερωθεί.\nΕίστε σίγουροι ότι θέλετε να συνεχίσετε;' %size
        
        self.main_purge.set_sensitive(False)
        self.main_cancel.set_sensitive(False)
        self.confirm_treeview.expand_all()
        self.confirm_label_2.set_label(label) 
        self.confirm_dialog.run()

    def on_main_cancel_pressed(self, widget):
        self.clean_mem()
        self.main_dialog.destroy()

    def on_confirm_dialog_delete_event(self, widget, event):
        self.main_purge.set_sensitive(True)
        self.main_cancel.set_sensitive(True)
        self.confirm_dialog.hide()

    def on_confirm_yes_pressed(self, widget):
        self.confirm_progressbar.set_visible(True)
        self.confirm_yes.set_sensitive(False)
        self.confirm_no.set_sensitive(False)
        threading.Thread(target=self.cache.commit, args=(apt.progress.TextFetchProgress(), MyInstallProgress())).start()

    def on_confirm_no_pressed(self, widget):
        self.main_purge.set_sensitive(True)
        self.main_cancel.set_sensitive(True)
        self.confirm_dialog.hide()

    def convert_bytes(self, bytes):
        bytes = float(bytes)
        tb = math.pow(1000,4)
        gb = math.pow(1000,3)
        mb = math.pow(1000,2)
        if bytes >= tb:
            terabytes = bytes / tb
            size = '%.1fTB' % terabytes
        elif bytes >= gb:
            gigabytes = bytes / gb
            size = '%.1fGB' % gigabytes
        if bytes >= mb:
            megabytes = bytes / mb
            size = '%.1fMB' % megabytes
        elif bytes >= 1000:
            kilobytes = bytes / 1000
            size = '%.1fKB' % kilobytes
        else:
            size = '%.1fB' % bytes

        return size

    def clean_mem(self):
        del self.cache 
        gc.collect()  

class MyInstallProgress(InstallProgress): 
    def error(self, pkg, errormsg):
        msg = ' '.join(['Στο πακέτο', pkg, 'προέκυψε σφάλμα:', errormsg])
        GObject.idle_add(ErrorDialog(msg, 'Σφάλμα').show)

    def finish_update(self):
        GObject.idle_add(PurgeKernels._instance.confirm_progressbar.set_text, 'Η απεγκατάσταση ολοκληρώθηκε')
        msg = 'Η απεγκατάσταση ολοκληρώθηκε.'
        GObject.idle_add(InfoDialog(msg, 'Ολοκλήρωση').show)
              
    def status_change(self, pkg, percent, status):
        GObject.idle_add(PurgeKernels._instance.confirm_progressbar.set_text, ' '.join([str(int(percent)), '%']))
        GObject.idle_add(PurgeKernels._instance.confirm_progressbar.set_fraction, percent/100)

class InfoDialog(Gtk.MessageDialog):
    def __init__(self, message, title=""):
        super(InfoDialog, self).__init__(type = Gtk.MessageType.INFO,
                                          flags = Gtk.DialogFlags.MODAL,
                                          buttons = Gtk.ButtonsType.CLOSE,
                                          message_format = message)
        self.set_title(title)
        self.set_transient_for(PurgeKernels._instance.confirm_dialog)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.connect('response', self.destroy_dialog)
    
    def destroy_dialog(self, widget, reponse):
        self.destroy()
        PurgeKernels._instance.clean_mem()
        PurgeKernels._instance.confirm_dialog.hide()
        PurgeKernels._instance.main_dialog.destroy()


class ErrorDialog(Gtk.MessageDialog):
    def __init__(self, message, title=""):
        super(ErrorDialog, self).__init__(type = Gtk.MessageType.ERROR,
                                          flags = Gtk.DialogFlags.MODAL,
                                          buttons = Gtk.ButtonsType.CLOSE,
                                          message_format = message)
        self.set_title(title)
        self.set_transient_for(PurgeKernels._instance.confirm_dialog)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.connect('response', self.destroy_dialog)
    
    def destroy_dialog(self, widget, reponse):
        self.destroy()
        PurgeKernels._instance.clean_mem()
        PurgeKernels._instance.confirm_dialog.hide()
        PurgeKernels._instance.main_dialog.destroy()  
