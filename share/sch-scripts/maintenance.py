#!/usr/bin/python
#-*- coding: utf-8 -*-
# Copyright (C) 2013 Lefteris Nikoltsios <lefteris.nikoltsios@gmail.com>
# 2017, Alkis Georgopoulos <alkisg@gmail.com>
# License GNU GPL version 3 or newer <http://gnu.org/licenses/gpl.html>

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import apt
import aptdaemon.client
from aptdaemon.enums import *
import aptdaemon.errors
from aptdaemon.gtk3widgets import AptErrorDialog, AptProgressDialog
import apt_pkg
import gc
import mimetypes
import os

import dialogs

class Package:
    def __init__(self, src,  cache=None):
        if cache is None:
            self.name, self.sum, self.size, self.desc, self.childs = os.path.basename(src), \
            mimetypes.guess_type(src)[0], os.path.getsize(src), 'Debian package', []
        else:
            pkg_cache = cache[src]        
            self.name, self.sum, self.size, self.desc, self.childs = pkg_cache.shortname, \
            pkg_cache.installed.version, pkg_cache.installed.installed_size, \
            pkg_cache.installed.summary, []

    def do_child(self, child):
        self.childs.append(child)
        self.childs.sort()



class MaintenanceDialog(object):
    def __init__(self, parent):
        self.pkgs = []
        self.apt_client = aptdaemon.client.AptClient() 
        self.builder = Gtk.Builder()
        self.builder.add_from_file('maintenance.ui')
        self.builder.connect_signals(self)
        
        '''
        Retrieve main_dlg
        '''
        self.main_dlg = self.builder.get_object('main_dlg')
        self.main_dlg_tview = self.builder.get_object('main_dlg_tview')
        self.main_dlg_tstore = self.builder.get_object('main_dlg_tstore')
        self.main_dlg_lbl_title = self.builder.get_object('main_dlg_lbl_title')
        self.main_dlg_lbl_space = self.builder.get_object('main_dlg_lbl_space')
        self.main_dlg_img_lbl = self.builder.get_object('main_dlg_img_lbl')
        self.main_dlg.set_transient_for(parent)
        self.main_dlg.set_default_response(Gtk.ResponseType.CANCEL)        
        
    def populate_treeview(self):
        tview_pkgs = []
        for ppkg in self.pkgs:
            if ppkg.name.startswith('linux-image'):
                tview_pkgs.append(ppkg)
                desc = '<b>%s</b>\n<small>%s (%s)</small>' %(ppkg.name, ppkg.desc, ppkg.sum)
                size = '%sB' %apt_pkg.size_to_str(ppkg.size)
                piter = self.main_dlg_tstore.append(None, [ppkg, None, desc, size, \
                                                  Gtk.IconSize.LARGE_TOOLBAR, None, None, False])
                for cpkg in ppkg.childs:
                    tview_pkgs.append(cpkg)
                    desc = '<b>%s</b>\n<small>%s (%s)</small>' %(cpkg.name, cpkg.desc, cpkg.sum)
                    size = '%sB' %apt_pkg.size_to_str(cpkg.size)
                    self.main_dlg_tstore.append(piter, [cpkg, None, desc, size, \
                                                Gtk.IconSize.SMALL_TOOLBAR, None, None, False]) 
        for ppkg in self.pkgs:
            if ppkg not in tview_pkgs:
                desc = '<b>%s</b>\n<small>%s (%s)</small>' %(ppkg.name, ppkg.desc, ppkg.sum)
                size = '%sB' %apt_pkg.size_to_str(ppkg.size)
                piter = self.main_dlg_tstore.append(None, [ppkg, None, desc, size, \
                                                  Gtk.IconSize.LARGE_TOOLBAR, None, None, False])
                        
    '''
    AptDeamon Callbacks
    '''
    def on_reply(self, trans):
        self.main_dlg.hide()
        trans.connect('finished', self.on_trans_finished)
        self.prog_dlg = AptProgressDialog(trans, None, True, False)
        self.prog_dlg.connect('response', self.on_prog_dlg_response)
        self.prog_dlg_cancel = self.prog_dlg.get_action_area().get_children()[0]
        self.prog_dlg.get_action_area().remove(self.prog_dlg_cancel)
        self.prog_dlg.add_button(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        self.prog_dlg.set_response_sensitive(Gtk.ResponseType.CLOSE, False)
        self.prog_dlg.run(False, False, True, lambda: True, self.on_error)

    def on_error(self, error):
        try:
            raise error
        except aptdaemon.errors.NotAuthorizedError:
            # Silently ignore auth failures
            return
        except aptdaemon.errors.TransactionFailed as error:
            pass
        except Exception as error:
            error = aptdaemon.errors.TransactionFailed(ERROR_UNKNOWN, str(error))
        self.error_dlg = AptErrorDialog(error, None)
        self.error_dlg.set_title('Σφάλμα')
        self.error_dlg.run()

    def on_trans_finished(self, trans, status):
        self.prog_dlg.expander.terminal.show()
        self.prog_dlg.expander.set_sensitive(True)
        self.prog_dlg.set_response_sensitive(Gtk.ResponseType.CLOSE, True)
        
    def on_prog_dlg_response(self, prog_dlg, response):
        self.prog_dlg.destroy()
        self.main_dlg.destroy() 
       
    '''
    Callbacks
    '''
    def on_main_dlg_pkg_toggle_toggled(self, widget, path):
        self.main_dlg_tstore[path][5] = not self.main_dlg_tstore[path][5]
        if not self.main_dlg_tstore[path][5]:
            self.pkgs.remove(self.main_dlg_tstore[path][0])
            for iter in self.main_dlg_tstore[path].iterchildren():
                self.pkgs.remove(iter[0])
                iter[5] = False   
        else:
            self.pkgs.append(self.main_dlg_tstore[path][0])
            for iter in self.main_dlg_tstore[path].iterchildren():
                self.pkgs.append(iter[0])
                iter[5] = True 
        if len(self.pkgs) != 0:
            self.main_dlg.set_response_sensitive(Gtk.ResponseType.OK, True)
            if len(self.pkgs) == 1:
                self.main_dlg_lbl_space.set_text(
                '%d πακέτο έχει επιλέγει, %sB χώρου στο δίσκο θα ελευθερωθούν.' \
                 %(len(self.pkgs), apt_pkg.size_to_str(sum(pkg.size for pkg in self.pkgs))))
            else:
                self.main_dlg_lbl_space.set_text(
                '%d πακέτα έχουν επιλέγει, %sB χώρου στο δίσκο θα ελευθερωθούν.' \
                 %(len(self.pkgs), apt_pkg.size_to_str(sum(pkg.size for pkg in self.pkgs))))    
        else:
            self.main_dlg.set_response_sensitive(Gtk.ResponseType.OK, False)
            self.main_dlg_lbl_space.set_text('Δεν έχετε επιλέξει κάποιο πυρήνα προς αφαίρεση.')



class Purge(MaintenanceDialog):
    def __init__(self, parent):
        super(Purge, self).__init__(parent)
        self.cache = apt.Cache()
        self.cache.open()
        self.main_dlg.set_title('Αφαίρεση παλιών πυρήνων...')
        self.main_dlg_lbl_title.set_markup(
                '<b><big>Βρέθηκαν οι παρακάτω παλιοί πυρήνες στο σύστημα\n\n</big></b>' \
                'Μπορείτε να επιλέξετε αυτούς που επιθυμείτε να αφαιρεθούν.')
        self.main_dlg_img_lbl.set_from_icon_name('applications-other', Gtk.IconSize.SMALL_TOOLBAR)
        self.main_dlg_img_lbl.set_pixel_size(-1)
        if not self.find():
            self.clear_cache()
            dialogs.InfoDialog('Δεν βρέθηκαν παλιοί πυρήνες για διαγραφή.', 'Ειδοποίηση').showup() 
            return

        if len(self.pkgs) == 1:
            self.main_dlg_lbl_space.set_text(
            '%d πακέτο έχει επιλέγει, %sB χώρου στο δίσκο θα ελευθερωθούν.' \
             %(len(self.pkgs), apt_pkg.size_to_str(sum(pkg.size for pkg in self.pkgs))))
        else:
            self.main_dlg_lbl_space.set_text(
            '%d πακέτα έχουν επιλέγει, %sB χώρου στο δίσκο θα ελευθερωθούν.' \
             %(len(self.pkgs), apt_pkg.size_to_str(sum(pkg.size for pkg in self.pkgs))))
        self.populate_treeview()
        self.main_dlg.show_all()             

    def find(self):
        status_path = apt_pkg.config.find_file('Dir::State::status')
        tagf = apt_pkg.TagFile(open(status_path))
        tmp_pkgs = [Package(sect['Package'], self.cache) for sect in tagf if \
                    (sect['Package'].startswith('linux-image-') \
                    or sect['Package'].startswith('linux-headers-')) \
                    and sect['Source'] != 'linux-meta']

        kernels = [pkg for pkg in tmp_pkgs if pkg.name.startswith('linux-image-')]
        headers = [pkg for pkg in tmp_pkgs if pkg.name.startswith('linux-headers-')]

        kernels.sort(cmp=lambda x,y: apt_pkg.version_compare(x.sum, y.sum), reverse=True)
        
        variants = []
        for kernel in kernels:
            version_variant = kernel.name.replace('linux-image-', '')
            version = kernel.sum.rpartition('.')[0]
            variant = version_variant.replace(version, '').strip('-')
            if version_variant != os.uname()[2] and variant in variants:
                self.pkgs.append(kernel)
                for header in headers:
                    if header.name.find(version) != -1:
                        kernel.do_child(header) 
                        self.pkgs.append(header) 
            variants.append(variant)
        return True if len(self.pkgs) != 0 else False
    
    def populate_treeview(self):
        super(Purge, self).populate_treeview()  
        for piter in self.main_dlg_tstore:
            piter[1], piter[5], piter[6], piter[7] = 'applications-other', True, True, True
            for iter in piter.iterchildren():
                iter[1], iter[5], iter[6], iter[7] = 'applications-other', True, False, True                      
            
    def clear_cache(self):
        del self.cache
        gc.collect()

    '''
    Callbacks
    '''
    def on_main_dlg_response(self, main_dlg, response):
        if response != Gtk.ResponseType.OK:
            self.clear_cache()
            self.main_dlg.destroy()
            return

        msg = 'Είστε σίγουροι ότι θέλετε να προχωρήσετε στην αφαίρεση των επιλεγμένων πυρήνων;'
        ask_dlg = dialogs.AskDialog(msg, 'Επιβεβαίωση')
        ask_dlg.set_transient_for(self.main_dlg) 
        if ask_dlg.showup() != Gtk.ResponseType.YES:
            return
            
        pkgs = [pkg.name for pkg in self.pkgs]
        self.apt_client.commit_packages(None, None, None, pkgs, None, None, False, \
                                            self.on_reply, self.on_error)

    def on_prog_dlg_response(self, prog_dlg, response):
        self.clear_cache()
        super(Purge, self).on_prog_dlg_response(prog_dlg, response)
        

class Clean(MaintenanceDialog):
    def __init__(self, parent):
        super(Clean, self).__init__(parent)
        self.main_dlg.set_title('Καθαρισμός μνήμης πακέτων...')
        self.main_dlg_lbl_title.set_markup(
                '<b><big>Βρέθηκαν τα παρακάτω αρχεία στην μνήμη\n</big></b>')
        self.main_dlg_img_lbl.set_from_icon_name('package-x-generic', Gtk.IconSize.SMALL_TOOLBAR)
        self.main_dlg_img_lbl.set_pixel_size(-1)
        if not self.find():
            dialogs.InfoDialog('Δεν υπάρχουν αρχεία στην μνήμη πακέτων για διαγραφή.', 'Ειδοποίηση').showup() 
            return

        if len(self.pkgs) == 1:
            self.main_dlg_lbl_space.set_markup(
                '%s αρχείο βρέθηκε, %sB χώρου στο δίσκο θα ελευθερωθούν.' \
                %(str(len(self.pkgs)), apt_pkg.size_to_str(sum(pkg.size for pkg in self.pkgs))))
        else:
            self.main_dlg_lbl_space.set_markup(
                '%s αρχεία βρέθηκαν, %sB χώρου στο δίσκο θα ελευθερωθούν.' \
                %(str(len(self.pkgs)), apt_pkg.size_to_str(sum(pkg.size for pkg in self.pkgs))))
        self.populate_treeview() 
        self.main_dlg.show_all()   
                
    def find(self):
        archive_path = apt_pkg.config.find_dir('Dir::Cache::archives')
        for dir in [archive_path, os.path.join(archive_path, 'partial')]:
            for filename in os.listdir(dir):
                if filename == 'lock':
                    continue
                path = os.path.join(dir, filename)
                if os.path.isfile(path):
                    self.pkgs.append(Package(path))
        self.pkgs.sort(key=lambda x: x.name)
        return True if len(self.pkgs) != 0 else False
             
    def populate_treeview(self):
        super(Clean, self).populate_treeview()
        for row in self.main_dlg_tstore:
            row[1] = 'package-x-generic'
        self.main_dlg_tview.get_columns()[0].set_title('Αρχείο')             
            

    '''
    Callbacks
    '''
    def on_main_dlg_response(self, main_dlg, response):
        if response != Gtk.ResponseType.OK:
            self.main_dlg.destroy()
            return

        msg = 'Είστε σίγουροι ότι θέλετε να προχωρήσετε στον καθαρισμό της μνήμης πακέτων;'
        ask_dlg = dialogs.AskDialog(msg, 'Επιβεβαίωση')
        ask_dlg.set_transient_for(self.main_dlg) 
        if ask_dlg.showup() != Gtk.ResponseType.YES:
            return
        
        pkgs = [pkg.name for pkg in self.pkgs]
        self.apt_client.clean(False, self.on_reply, self.on_error)


class AutoRemove(MaintenanceDialog):
    def __init__(self, parent):
        super(AutoRemove, self).__init__(parent)
        self.cache = apt.Cache()
        self.cache.open()
        self.main_dlg.set_title('Διαγραφή ορφανών πακέτων...')
        self.main_dlg_lbl_title.set_markup(
                '<b><big>Βρέθηκαν τα παρακάτω ορφανά πακέτα στο σύστημα\n</big></b>')
        self.main_dlg_img_lbl.set_from_icon_name('applications-other', Gtk.IconSize.SMALL_TOOLBAR)
        self.main_dlg_img_lbl.set_pixel_size(-1)
        if not self.find():
            self.clear_cache()
            dialogs.InfoDialog('Δεν υπάρχουν ορφανά πακέτα για διαγραφή.', 'Ειδοποίηση').showup()
            return

        if len(self.pkgs) == 1:
            self.main_dlg_lbl_space.set_markup(
                '%s πακέτο βρέθηκε, %sB χώρου στο δίσκο θα ελευθερωθούν.' \
                %(str(len(self.pkgs)), apt_pkg.size_to_str(sum(pkg.size for pkg in self.pkgs))))
        else:
            self.main_dlg_lbl_space.set_markup(
                '%s πακέτα βρέθηκαν, %sB χώρου στο δίσκο θα ελευθερωθούν.' \
                %(str(len(self.pkgs)), apt_pkg.size_to_str(sum(pkg.size for pkg in self.pkgs))))
        self.populate_treeview()
        self.main_dlg.show_all()
    
    def find(self):
        status_path = apt_pkg.config.find_file('Dir::State::status')
        tagf = apt_pkg.TagFile(open(status_path))
        self.pkgs = [Package(sect['Package'], self.cache) for sect in tagf if \
                     self.cache[sect['Package']].is_auto_removable]
        self.pkgs.sort(key=lambda x: x.name)
        return True if len(self.pkgs) != 0 else False   

    def populate_treeview(self):
        super(AutoRemove, self).populate_treeview()
        for row in self.main_dlg_tstore:
            row[1] = 'applications-other'      
            
    def clear_cache(self):
        del self.cache
        gc.collect()

    '''
    Callbacks
    '''
    def on_main_dlg_response(self, main_dlg, response):
        if response != Gtk.ResponseType.OK:
            self.clear_cache()
            self.main_dlg.destroy()
            return

        msg = 'Είστε σίγουροι ότι θέλετε να προχωρήσετε στην αφαίρεση των ορφανών πακέτων;'
        ask_dlg = dialogs.AskDialog(msg, 'Επιβεβαίωση')
        ask_dlg.set_transient_for(self.main_dlg) 
        if ask_dlg.showup() != Gtk.ResponseType.YES:
            return
            
        pkgs = [pkg.name for pkg in self.pkgs]
        self.apt_client.commit_packages(None, None, None, pkgs, None, None, False, \
                                            self.on_reply, self.on_error)

    def on_prog_dlg_response(self, prog_dlg, response):
        self.clear_cache()
        super(AutoRemove, self).on_prog_dlg_response(prog_dlg, response)

