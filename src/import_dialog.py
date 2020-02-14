# This File is part of the ltsp-manager.
#
# Copyright 2012-2018 by it's authors.
#
# Licensed under GNU General Public License 3.0 or later.
# Some rights reserved. See COPYING, AUTHORS.

"""
Import users from a csv or passwd file
"""

from gettext import gettext as _
import csv

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gio, WebKit2, GLib
import markdown2
import dict_view

# import common
# import user_form
import dialogs


class ImportAssistant():
    """ A multistep user import process. The admin can open a csv file and adjust all the settings to import the file. """

    def __init__(self, bus, account_manager, parent=None):
        super().__init__()
        self.parent = parent
        self.bus = bus
        self.account_manager = account_manager

        self.cancellable = Gio.Cancellable()
        self.raw_data = None

        gladefile = "import_dialog19.ui"
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/ltsp/ltsp-manager/ui/' + gladefile)
        self.dialog = self.builder.get_object('import_assistant')
        self.notebook = self.builder.get_object('import_notebook')
        self.help_box = self.builder.get_object('help_box')
        self.import_list_store = self.builder.get_object("import_list_store")
        self.chooser = self.builder.get_object("import_file_chooser")

        self.values = self.builder.get_object("values")
        self.column = None

        self.format_values = []
        self.format_strings = {}

        # Make the intro WebView for a display of markdown styled help.
        self.intro_web = WebKit2.WebView()
        markdown_text = _("""# GtkTreeSelection

        ein neuer Versuch
        """)
        self.intro_web.load_alternate_html(markdown2.markdown(markdown_text), "/", "/")
        self.intro_web.show_all()
        self.help_box.pack_start(self.intro_web, True, True, 0)

        self.builder.connect_signals(self)
        self.dialog.set_transient_for(self.parent)
        self.dialog.show()
        self.set_sensitive()

    def set_sensitive(self, *_args):
        """Set the buttons sensitive according to a predefined matrix and the current page"""
        cur = self.notebook.get_current_page()

        visibility = [(True, False, True, False, None),  # help
                      (True, False, False, False, None),  # select file
                      (True, False, True, False, None),   # prepare
                      (True, False, True, False, self.load_assign_tab),   # options
                      (True, False, False, True, self.load_import_preview),   # preview
                      (True, False, False, True, None)]  # log
        self.builder.get_object("import_cancel").set_visible(visibility[cur][0])
        self.builder.get_object("import_back").set_visible(visibility[cur][1])
        self.builder.get_object("import_forward").set_sensitive(visibility[cur][2])
        self.builder.get_object("import_apply").set_visible(visibility[cur][3])
        if visibility[cur][4]:
            visibility[cur][4]()

    def on_import_forward_clicked(self, widget):
        """ React to a click on the next button """
        self.notebook.next_page()
        self.set_sensitive()

    def on_import_back_clicked(self, widget):
        """ React to a click on the back button """
        self.notebook.prev_page()
        self.set_sensitive()

    def on_import_apply_clicked(self, widget):
        """ TODO React to a click on the apply button """
        print("apply", self)

    def on_import_cancel_clicked(self, widget):
        """ React to a click on the cancel button """
        self.dialog.destroy()

    def on_import_file_chooser_file_activated(self, widget):
        """ When the user selected a file load it and when done go to the next page """
        file = self.chooser.get_file()
        file.load_contents_async(self.cancellable, self.load_file, None)

    def reset_to_filechooser(self):
        """ Go back to the file choosing dialog. """
        self.cancellable.cancel()
        self.notebook.set_current_page(1)

    def load_file(self, giofile, result, _user_data=None):
        """ When the computer is done loading the file try to decode it with some encodings. """
        try:
            _success, contents, _etag = giofile.load_contents_finish(result)
        except GLib.GError as error:
            if error.code != Gio.IOErrorEnum.CANCELLED:
                # only show error dialog if NOT cancelled
                dialogs.ErrorDialog(str(error)).showup()
            self.reset_to_filechooser()
            return

        encodings = ['UTF-8', 'ISO-8859-15']
        document_encoding = None

        for encoding in encodings:
            try:
                decoded = contents.decode(encoding)
                document_encoding = encoding
                break
            except UnicodeDecodeError:
                pass
        if document_encoding:
            self.raw_data = decoded.splitlines()
            self.on_import_forward_clicked(None)
            self.on_options_preview_update(None)
        else:
            dialogs.ErrorDialog("Wrong character encoding. Expected UTF-8.").showup()
            self.reset_to_filechooser()

    def on_options_preview_update(self, widget, *_args):
        """ Whenever one of the options changed show the preview. """
        csv_extras = {}
        delimiter = self.builder.get_object("delimiter_character_entry").get_text()
        quotechar = self.builder.get_object("quote_character_entry").get_text()
        options_preview = self.builder.get_object("options_preview")
        if delimiter:
            csv_extras['delimiter'] = delimiter
        if quotechar:
            csv_extras['quotechar'] = quotechar

        preview = csv.reader(self.raw_data, **csv_extras)

        if preview:
            first_line = next(preview)
            second_line = next(preview)
            store = Gtk.ListStore(*[type(x) for x in second_line])
            renderer = Gtk.CellRendererText()
            renderer.set_property("max-width-chars", 20)
            renderer.set_property("height", 20)
            # remove all the old columns
            for column in options_preview.get_columns():
                options_preview.remove_column(column)
            if self.builder.get_object("first_line_titles").get_active():
                for x, y in enumerate(first_line):
                    options_preview.append_column(Gtk.TreeViewColumn(str(y), renderer, text=x))
                first_line = second_line
                second_line = next(preview)
            else:
                for x in range(len(first_line)):
                    options_preview.append_column(Gtk.TreeViewColumn(str(x), renderer, text=x))

            try:
                store.append(first_line)
                store.append(second_line)
                line = next(preview, None)
                while line and len(store) < 15:
                    store.append(line)
                    line = next(preview, None)
                self.builder.get_object("csv_options_error").set_visible(False)
                self.builder.get_object("import_forward").set_sensitive(True)
            except ValueError:
                self.builder.get_object("csv_options_error").set_visible(True)
                self.builder.get_object("import_forward").set_sensitive(False)
                return

            options_preview.set_model(store)

    def load_assign_tab(self):
        """ Load the tab where the user can specify which column shoud be used where. """

        # Prepare the values of the dropdown menus
        self.values = Gtk.ListStore(str)
        options_preview = self.builder.get_object("options_preview")
        self.values.append(["Default"])
        for column in options_preview.get_columns():
            self.values.append(["{" + column.get_title() + "}"])

        assign_semantic_treeview = self.builder.get_object("assign_semantic")

        if not self.column:
            cell = self.builder.get_object("combo_cell_render")
            self.column = self.builder.get_object("format_column")
            cell.set_property("model", self.values)
        else:
            self.import_list_store.clear()
            self.column.clear()
        self.import_list_store.append([True, "Username", _("The username is required"), "", False])
        for x in [_("Password"),
                  _("Full name"),
                  _("UID"),
                  _("Home directory"),
                  _("Shell"),
                  _("Office"),
                  _("Office phone"),
                  _("Home phone"),
                  _("Other"),
                  _("Last change"),
                  _("Minimum age"),
                  _("Maximum age"),
                  _("Warning period"),
                  _("Inactive"),
                  _("Expired"),
                  _("Locked"),
                  _("Groups")]:
            self.import_list_store.append([False, x, _("Using defaults for: {}".format(x)), "", True])
        assign_semantic_treeview.show_all()

    def assign_cell_combo_edited(self, widget, path, text):
        """ Update the state of the text entry and also mark the line as active """
        self.import_list_store[path][3] = text
        self.import_list_store[path][0] = bool(text)
        self.builder.get_object("assign_selection").unselect_all()

    def assign_check_button_changed(self, widget, path):
        """ Update the state and remove the text from the entry when neccessary """
        if self.import_list_store[path][0]:
            self.import_list_store[path][3] = ""
        self.import_list_store[path][0] = not widget.get_active()
        self.builder.get_object("assign_selection").unselect_all()

    def on_assign_selection_changed(self, _selection):
        """ Update the preview whenever something changed """
        self.format_values = []
        self.format_strings = {}
        options_preview = self.builder.get_object("options_preview")
        user_preview = self.builder.get_object("user_preview")
        # Get all the column headers.
        for x, row in enumerate(options_preview.get_model()):
            self.format_values.append(dict())
            for i, column in enumerate(options_preview.get_columns()):
                self.format_values[x][column.get_title()] = row[i]
        # Get all the
        for row in self.import_list_store:
            if row[0]:
                self.format_strings[row[1]] = row[3]
        preview = ["Preview:", "The first user:"]
        for key, string in self.format_strings.items():
            preview.append("{}: {}".format(key, string.format(*self.format_values[0].values(), **self.format_values[0])[:20]))
        user_preview.set_text("\n".join(preview))

    def load_import_preview(self):
        """ Loading the preview of all users that are going to be created. """
        import_preview = self.builder.get_object("preview_import")
        order = self.format_strings.keys()
        dictionaries = [self.format_strings[x] for x in order]
        for row in self.format_values:
            values = [row[x] for x in order]
            dictionaries.append({o: self.format_strings[o].format(*values, **row) for o in order})
        import_preview.pack_start(dict_view.DictView(dictionaries, order), True, True, 0)
        import_preview.show_all()
