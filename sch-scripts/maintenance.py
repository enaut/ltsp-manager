#!/usr/bin/python
# -*- coding:utf-8 -*-
# Copyright (C) 2012 Lefteris Nikoltsios <lefteris.nikoltsios@gmail.com>, Yannis Siahos <Siahos@cti.gr>
# License GNU GPL version 3 or newer <http://gnu.org/licenses/gpl.html>

from gi.repository import Gtk
import apt_pkg
import apt
import os
import gc
import mimetypes
import aptdaemon.client
from aptdaemon.enums import *
from aptdaemon.gtk3widgets import AptErrorDialog, AptProgressDialog
import aptdaemon.errors
import dialogs


class Package:
    def __init__(self, pkg,  cache):
        pkg_cache = cache[pkg]        
        self.name, self.version, self.size, self.desc, self.childs = pkg_cache.shortname, \
        pkg_cache.installed.version, pkg_cache.installed.installed_size, pkg_cache.installed.summary, []

    def do_child(self, child):
        self.childs.append(child)
        self.childs.sort()

class Deb:
    def __init__(self, path):
        self.name, self.mime, self.size, self.desc = os.path.basename(path), \
        mimetypes.guess_type(path)[0], os.path.getsize(path), 'Debian package'
        

class Purge:
    def __init__(self, parent):
        self.parent = parent
        self.cache = apt.Cache() 
        self.cache.open()
        
    def find(self):
        status_path = apt_pkg.config.find_file('Dir::State::status')
        tagf = apt_pkg.TagFile(open(status_path))
        tmp_pkgs = [Package(sect['Package'], self.cache) for sect in tagf if \
                    (sect['Package'].startswith('linux-image-') \
                    or sect['Package'].startswith('linux-headers-')) \
                    and sect['Source'] != 'linux-meta']

        kernels = [pkg for pkg in tmp_pkgs if pkg.name.startswith('linux-image-')]
        headers = [pkg for pkg in tmp_pkgs if pkg.name.startswith('linux-headers-')]

        kernels.sort(cmp=lambda x,y: apt_pkg.version_compare(x.version, y.version), reverse=True)

        variants = []
        self.pkgs = []
        for kernel in kernels:
            version_variant = kernel.name.replace('linux-image-', '')
            version = kernel.version.rpartition('.')[0]
            variant = version_variant.replace(version, '').strip('-')
            if version_variant != os.uname()[2] and variant in variants:
                self.pkgs.append(kernel)
                for header in headers:
                    if header.name.find(version) != -1:
                        kernel.do_child(header) 
                        self.pkgs.append(header) 
            variants.append(variant)
      
        return False if len(self.pkgs) == 0 else True
        
    def run(self):
        if self.find():
            MaintenanceDialog(self)
        else:
            del self.cache
            gc.collect()
            msg = 'Δεν υπάρχουν παλιοί πυρήνες για διαγραφή.'
            dialogs.InfoDialog(msg, 'Ειδοποίηση').showup()
        

class Clean:
    def __init__(self, parent):
        self.parent = parent
        
    def find(self):
        archive_path = apt_pkg.config.find_dir('Dir::Cache::archives')
        self.pkgs = []
        for dir in [archive_path, os.path.join(archive_path, 'partial')]:
            for filename in os.listdir(dir):
                if filename == 'lock':
                    continue
                path = os.path.join(dir, filename)
                if os.path.isfile(path):
                    self.pkgs.append(Deb(path))
        self.pkgs.sort()

        return False if len(self.pkgs) == 0 else True

    def run(self):
        if self.find():
            MaintenanceDialog(self)
        else:
            msg = 'Δεν υπάρχουν πακέτα στην μνήμη για διαγραφή.'
            dialogs.InfoDialog(msg, 'Ειδοποίηση').showup()

class AutoRemove:
    def __init__(self, parent):
        self.parent = parent
        self.cache = apt.Cache() 
        self.cache.open()
        
    def find(self):
        status_path = apt_pkg.config.find_file('Dir::State::status')
        tagf = apt_pkg.TagFile(open(status_path))
        self.pkgs = [Package(sect['Package'], self.cache) for sect in tagf if \
                     self.cache[sect['Package']].is_auto_removable]
        self.pkgs.sort()

        return False if len(self.pkgs) == 0 else True

    def run(self):
        if self.find():
            MaintenanceDialog(self)
        else:
            del self.cache
            gc.collect()
            msg = 'Δεν υπάρχουν ορφανά πακέτα για διαγραφή.'
            dialogs.InfoDialog(msg, 'Ειδοποίηση').showup()


class MaintenanceDialog:
    def __init__(self, inst):
        self.inst = inst
        self.apt_client = aptdaemon.client.AptClient() 
        
        self.builder = Gtk.Builder()
        self.builder.add_from_file('maintenance.ui')
        self.builder.connect_signals(self)  
        
        '''
        Retrieve main_dlg
        '''
        self.main_dlg = self.builder.get_object('main_dlg')

        self.main_dlg_purge_tview = self.builder.get_object('main_dlg_purge_tview')
        self.main_dlg_auto_tview = self.builder.get_object('main_dlg_auto_tview')
        self.main_dlg_clean_tview = self.builder.get_object('main_dlg_clean_tview')

        self.main_dlg_scrolledwindow = self.builder.get_object('main_dlg_scrolledwindow')

        self.main_dlg_purge_tstore = self.builder.get_object('main_dlg_purge_tstore')
        self.main_dlg_auto_tstore = self.builder.get_object('main_dlg_auto_tstore')
        self.main_dlg_clean_tstore = self.builder.get_object('main_dlg_clean_tstore')

        self.main_dlg_lbl_title = self.builder.get_object('main_dlg_lbl_title')
        self.main_dlg_lbl_space = self.builder.get_object('main_dlg_lbl_space')
        self.main_dlg_img_lbl = self.builder.get_object('main_dlg_img_lbl')

        self.populate_treeview()
        
        self.main_dlg.set_transient_for(self.inst.parent)
        self.main_dlg.set_default_response(Gtk.ResponseType.CANCEL)
        self.main_dlg.show_all()  
            
            
    def populate_treeview(self):
        if isinstance(self.inst, Purge):
            self.main_dlg.set_title('Αφαίρεση παλιών πυρήνων...')
            lbl_title = '<b><big>Βρέθηκαν οι παρακάτω παλιοί πυρήνες στο σύστημα\n\n</big></b>'
            lbl_title += 'Μπορείτε να επιλέξετε αυτούς που επιθυμείτε να αφαιρεθούν.'
            self.main_dlg_lbl_title.set_markup(lbl_title)
            self.main_dlg_img_lbl.set_from_icon_name('applications-other', Gtk.IconSize.SMALL_TOOLBAR)
            self.main_dlg_img_lbl.set_pixel_size(-1)
            self.main_dlg_scrolledwindow.add(self.main_dlg_purge_tview)
            
            for ppkg in self.inst.pkgs:
                if ppkg.name.startswith('linux-image-'):
                    desc = '<b>%s</b> (%s)\n<small>%s</small>' %(ppkg.name, ppkg.version, ppkg.desc )
                    size = '%sB' %apt_pkg.size_to_str(ppkg.size)
                    icon = 'applications-other'
                    piter = self.main_dlg_purge_tstore.append(None, [ppkg, True, icon, desc, size, \
                                                              True, Gtk.IconSize.LARGE_TOOLBAR])
                    if hasattr(ppkg, 'childs'):
                        for cpkg in ppkg.childs:
                            desc = '<b>%s</b> (%s)\n<small>%s</small>' %(cpkg.name, cpkg.version, \
                                                                         cpkg.desc )
                            size = '%sB' %apt_pkg.size_to_str(cpkg.size)
                            icon = 'applications-other'
                            self.main_dlg_purge_tstore.append(piter, [cpkg, True, icon, desc, size, \
                                                              False, Gtk.IconSize.SMALL_TOOLBAR]) 

            self.calc_space()
   

        elif isinstance(self.inst, Clean):
            self.main_dlg.set_title('Καθαρισμός μνήμης πακέτων...')
            lbl_title = '<b><big>Βρέθηκαν τα παρακάτω DEB αρχεία στην μνήμη\n</big></b>'
            self.main_dlg_lbl_title.set_markup(lbl_title)   
            self.main_dlg_img_lbl.set_from_icon_name('package-x-generic', Gtk.IconSize.SMALL_TOOLBAR) 
            self.main_dlg_img_lbl.set_pixel_size(-1)
            self.main_dlg_scrolledwindow.add(self.main_dlg_clean_tview)  
            
            space  = 0
            for pkg in self.inst.pkgs:
                desc = '<b>%s</b>\n<small>%s (%s)</small>' %(pkg.name, pkg.desc, pkg.mime)
                size = '%sB' %apt_pkg.size_to_str(pkg.size)
                icon = 'package-x-generic'
                self.main_dlg_clean_tstore.append(None, [pkg, icon, desc, size, Gtk.IconSize.LARGE_TOOLBAR])
                space += pkg.size
            lbl_space = '%s πακέτα έχουν επιλέγει, %sB χώρου στο δίσκο θα ελευθερωθεί.' \
                                            %(str(len(self.inst.pkgs)), apt_pkg.size_to_str(space))
            self.main_dlg_lbl_space.set_text(lbl_space) 
            
        elif isinstance(self.inst, AutoRemove):
            self.main_dlg.set_title('Διαγραφή ορφανών πακέτων...')
            lbl_title = '<b><big>Βρέθηκαν τα παρακάτω ορφανά πακέτα στο σύστημα\n</big></b>'
            self.main_dlg_lbl_title.set_markup(lbl_title)   
            self.main_dlg_img_lbl.set_from_icon_name('applications-other', Gtk.IconSize.SMALL_TOOLBAR) 
            self.main_dlg_img_lbl.set_pixel_size(-1)
            self.main_dlg_scrolledwindow.add(self.main_dlg_auto_tview)  
            
            space = 0
            for pkg in self.inst.pkgs:
                desc = '<b>%s</b> (%s)\n<small>%s</small>' %(pkg.name, pkg.version, pkg.desc )
                size = '%sB' %apt_pkg.size_to_str(pkg.size)
                icon = 'applications-other'
                self.main_dlg_auto_tstore.append(None, [pkg, icon, desc, size, Gtk.IconSize.LARGE_TOOLBAR])
                space += pkg.size
            lbl_space = '%s πακέτα έχουν επιλέγει, %sB χώρου στο δίσκο θα ελευθερωθεί.' \
                                            %(str(len(self.inst.pkgs)), apt_pkg.size_to_str(space))
            self.main_dlg_lbl_space.set_text(lbl_space)
            
            

    def calc_space(self):
        if len(self.inst.pkgs) == 0:
            self.main_dlg_lbl_space.set_text('Δεν έχετε επιλέξει κάποιο πυρήνα προς αφαίρεση.')
            self.main_dlg.set_response_sensitive(Gtk.ResponseType.OK, False)
        else:
            space = sum(pkg.size for pkg in self.inst.pkgs)
            lbl_space = '%s πακέτα έχουν επιλέγει, %sB χώρου στο δίσκο θα ελευθερωθεί.' \
                                            %(str(len(self.inst.pkgs)), apt_pkg.size_to_str(space))
            self.main_dlg_lbl_space.set_text(lbl_space)
            self.main_dlg.set_response_sensitive(Gtk.ResponseType.OK, True)


    '''
    Callbacks
    '''
    def on_packagetoggle1_toggled(self, widget, path):
        self.main_dlg_purge_tstore[path][1] = not self.main_dlg_purge_tstore[path][1]
        if not self.main_dlg_purge_tstore[path][1]:
            self.inst.pkgs.remove(self.main_dlg_purge_tstore[path][0])
            for iter in self.main_dlg_purge_tstore[path].iterchildren():
                self.inst.pkgs.remove(iter[0])
                iter[1] = False   
        else:
            self.inst.pkgs.append(self.main_dlg_purge_tstore[path][0])
            for iter in self.main_dlg_purge_tstore[path].iterchildren():
                self.inst.pkgs.append(iter[0])
                iter[1] = True 
        self.calc_space()
        

    def on_main_dlg_response(self, main_dlg, reponse):
        if reponse != Gtk.ResponseType.OK:
            if isinstance(self.inst, AutoRemove) or isinstance(self.inst, Purge):
                del self.inst.cache
                gc.collect()
            self.main_dlg.destroy()
            return
        
        pkgs = [pkg.name for pkg in self.inst.pkgs]
        if isinstance(self.inst, Purge):
            self.apt_client.commit_packages(None, None, None, pkgs, None, None, False, \
                                            self.on_reply, self.on_error)
        elif isinstance(self.inst, Clean):
            self.apt_client.clean(False, self.on_reply, self.on_error)
        elif isinstance(self.inst, AutoRemove):
            self.apt_client.commit_packages(None, None, None, pkgs, None, None, False, \
                                            self.on_reply, self.on_error)

    def on_reply(self, trans):
        prog_dlg = ProgressDialog(trans, self.main_dlg, True, False, self.inst)
        prog_dlg.show_all()
        
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
        error_dlg = ErrorDialog(error, self.main_dlg, self.inst)
        error_dlg.show_all()



class ProgressDialog(AptProgressDialog):
    def __init__(self, trans, parent, terminal, debconf, inst):
        AptProgressDialog.__init__(self, trans, parent, terminal, debconf)
        self.cancel_pressed = False 
        self.trans = trans
        self.inst = inst

        self.set_title('Εφαρμογή')
        self.connect('response', self._on_response)
        self.set_modal(True)

        self.cancel = self.get_action_area().get_children()[0]
        self.cancel.connect('pressed', self._on_cancel_pressed)
        self.cancel.set_can_default(True)

        self.add_buttons(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE, Gtk.STOCK_REMOVE, Gtk.ResponseType.OK)
        self.get_action_area().reorder_child(self.cancel, 1)

        self.set_response_sensitive(Gtk.ResponseType.CLOSE, False)
        
        self.trans.connect('finished', self._on_finished)

    def _on_cancel_pressed(self, widget):
        self.cancel_pressed = True
        self.set_response_sensitive(Gtk.ResponseType.CLOSE, True)
        self.set_response_sensitive(Gtk.ResponseType.OK, False)

    def _on_response(self, dlg, response):
        if response != Gtk.ResponseType.OK:
            if not self.cancel_pressed:
                if isinstance(self.inst, AutoRemove) or isinstance(self.inst, Purge):
                    del self.inst.cache
                    gc.collect()
                self.get_transient_for().destroy()
            self.destroy()
            return
        if isinstance(self.inst, Purge):
            msg = 'Είστε σίγουροι ότι θέλετε να προχωρήσετε στην αφαίρεση των επιλεγμένων πυρήνων;'
        elif isinstance(self.inst, Clean):
            msg = 'Είστε σίγουροι ότι θέλετε να προχωρήσετε στον καθαρισμό της μνήμης πακέτων;'
        elif isinstance(self.inst, AutoRemove):
            msg = 'Είστε σίγουροι ότι θέλετε να προχωρήσετε στην αφαίρεση των ορφανών πακέτων;'
        ask_dlg = dialogs.AskDialog(msg, 'Επιβεβαίωση')
        ask_dlg.set_transient_for(self)
        if ask_dlg.showup() != Gtk.ResponseType.YES:
            self.cancel.emit('clicked')
            self.cancel.emit('pressed')
            return
        self.set_response_sensitive(Gtk.ResponseType.OK, False)
        self.trans.run(lambda: True, self.on_error )

    def _on_finished(self, trans, status):
        self.expander.terminal.show()
        self.expander.set_sensitive(True)
        self.set_response_sensitive(Gtk.ResponseType.CLOSE, True)

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
        error_dlg = ErrorDialog(error, self)
        error_dlg.show_all()


class ErrorDialog(AptErrorDialog):
    def __init__(self, error, parent, inst=None):
        AptErrorDialog.__init__(self, error, parent) 
        self.inst = inst
        self.set_title('Σφάλμα')
        self.set_modal(True)
        self.connect('response', self._on_response) 

    def _on_response(self, dlg, response):
        if isinstance(self.inst, AutoRemove) or isinstance(self.inst, Purge):
            del self.inst.cache
            gc.collect()
        self.get_transient_for().destroy()
        self.destroy()  
