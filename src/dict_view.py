""" A normal TreeView that automatically displays data from a dictionary. """

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class DictView(Gtk.TreeView):
    """ A normal TreeView that automatically displays data from a dictionary. """

    def __init__(self, dictionaries, order, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.dictionaries = dictionaries
        self.order = order
        ordered_first_line = [self.dictionaries[0][x] for x in self.order]
        types = [type(x) for _y, x in ordered_first_line]
        self.store = Gtk.ListStore(*types)

        for dic in self.dictionaries:
            self.store.append([dic[x] for x in self.order])

        for x, col in enumerate(self.order):
            renderer = Gtk.CellRendererText()
            renderer.set_property("max-width-chars", 20)
            renderer.set_property("height", 20)
            self.append_column(Gtk.TreeViewColumn(str(col), renderer, text=x))
        self.set_model(self.store)
