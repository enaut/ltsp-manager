from gettext import gettext as _
import os
from gi.repository import Gtk
import config

icons = {"ok_hidden": Gtk.STOCK_YES,  # valid but invisible
         "ok_visible": Gtk.STOCK_YES,
         "no": Gtk.STOCK_NO}


class LineEntry():
    """ a general line with validation functions"""

    def __init__(self, user_form, entry_id, valid_icon_id, initial_value, validator, updater=None):
        self.user_form = user_form
        self.validate = validator
        self.updater = updater
        self.entry = self.user_form.builder.get_object(entry_id)
        if valid_icon_id:
            self.valid_icon = self.user_form.builder.get_object(valid_icon_id)
        else:
            self.valid_icon = False
        self.set_initial_value(initial_value)
        try:
            # ignore entries that do not have a changed signal
            self.entry.connect("changed", self.update)
        except TypeError:
            pass

    def valid(self):
        """ validate and set the icons accordingly """
        v = self.validate(self)
        if v is None:
            return True
        if v in ["ok_hidden", "ok_visible"]:
            icon = icons[v]
            tooltip = v
        else:
            icon = icons['no']
            tooltip = v
        self.valid_icon.set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.valid_icon.set_visible(v != "ok_hidden")
        self.valid_icon.set_tooltip_text(tooltip)
        return "ok_" in v

    def update(self, widget):
        """ update the values and icon """
        self.valid()
        self.user_form.set_apply_sensitivity()
        if self.updater:
            self.updater(self)

    def changed(self):
        return self.get_value() != self.initial_value

    def validator(self):
        """A validator returns:
            "ok_hidden" if the value is ok but no icon has to show it eg. if the value has not been changed
            "ok_visible" if the value is ok an the icon should show it.
            "anything else - might be used as errormessage tooltip" if the value is not ok."""
        raise NotImplementedError("This is not implemented")


class TextLineEntry(LineEntry):
    def set_initial_value(self, value):
        """ set the initial or default value """
        self.initial_value = value
        self.entry.set_text(value)
        if value:
            self.entry.set_placeholder_text(value)
        self.update(None)

    def get_value(self):
        return self.entry.get_text()


class NumberLineEntry(LineEntry):
    def set_initial_value(self, value):
        """ set the initial or default value """
        self.initial_value = value
        self.entry.set_value(value)
        self.update(None)

    def get_value(self):
        return self.entry.get_value_as_int()


class LabelLineEntry(LineEntry):
    def set_initial_value(self, value):
        """ set the initial or default value """
        self.initial_value = value
        self.entry.set_text(value)
        self.update(None)

    def get_value(self):
        return self.entry.get_text()

class ComboLineEntry(LineEntry):
    def set_initial_value(self, value):
        """ set the initial or default value """
        self.initial_value = value
        self.entry.set_text(value)
        self.update(None)

    def get_value(self):
        return self.entry.get_text()




class Validators():
    @staticmethod
    def username_validator(line):
        """ validate the username """
        username = line.entry.get_text()
        if line.user_form.mode and (line.user_form.mode == 'new') and username == '':
            return _("Username may not be empty")
        if username == line.initial_value:
            return "ok_hidden"
        valid_name, free_name = line.user_form.account_manager.IsUsernameValidAndFree(username)
        if valid_name and free_name:
            return "ok_visible"
        if username == line.initial_value and username != "":
            return "ok_visible"
        if username == '' and line.initial_value:
            return "ok_hidden"
        else:
            return _("Username is not valid.")

    @staticmethod
    def home_validator(line):
        """ validate the home directory permissions:
                * home is empty
                * home is not existant yet
                * parent is existant
                * home has right uid and gid
                * home matches the old home entry
                """
        home = line.entry.get_text()
        if not home:
            # is empty
            print("is empty")
            return "ok_hidden"
        if line.user_form.mode == "edit" and line.user_form.user and home == line.user_form.user.GetHomeDir():
            # is the old one then it is always ok
            print("is old")
            return "ok_hidden"
        if os.path.isdir(home):
            print(home, "is path")
            # is a directory
            if "primary_group_id_label" in line.user_form.__dict__ and "uid_entry" in line.user_form.__dict__:
                gid = int(line.user_form.primary_group_id_label.get_value())
                uid = line.user_form.uid_entry.get_value()
                path_uid = os.stat(home).st_uid
                path_gid = os.stat(home).st_gid
                if path_uid == uid and path_gid == gid:
                    print("path with uid and gid is good")
                    return "ok_visible"
                else:
                    # has not matching uid and gid
                    return _("This directory belongs to UID %(uid)d and to GID %(gid)d") % {"uid": path_uid, "gid": path_gid}
        else:
            # home is not adirectory
            if not os.path.exists(home):
                print("path is free")
                # and does not exist
                return "ok_visible"
            else:
                print("path is a file")
                # home is a file or someting.
                return _("The home path is not a directory")

        line.user_form.set_apply_sensitivity()

    @staticmethod
    def edit_or_something_validator(line):
        """ Be valid if edit mode is active or something is entered """
        if line.initial_value == line.entry.get_text() and line.entry.get_text() != '':
            return "ok_hidden"
        if line.user_form.mode == 'edit':
            # ? does it work?
            return "ok_visible"
        if len(line.entry.get_text()) > 0:
            return "ok_visible"
        else:
            return _("This may not be empty")

    @staticmethod
    def no_comma_validator(line):
        """ Gecos check for a ',' and ':' character """
        if line.initial_value == line.entry.get_text():
            return "ok_hidden"
        if ',' not in line.entry.get_text() and ':' not in line.entry.get_text():
            return "ok_visible"
        else:
            return _("there can be no : or , in this text")

    @staticmethod
    def uid_validator(line):
        """ Check for a valid uid range """
        if line.initial_value == line.entry.get_value():
            return "ok_hidden"
        if 999 < line.entry.get_value() < 30000:
            valid, free = line.user_form.account_manager.IsUIDValidAndFree(line.entry.get_value_as_int())
            if valid and free:
                return "ok_visible"
        return _("Uids have to be in range 1000 to 30000")

    # @staticmethod
    # def gid_validator(line):
    #     """ Check for a valid uid range """
    #     if line.initial_value == line.entry.get_value():
    #         return "ok_hidden"
    #     if 999 < line.entry.get_value() < 30000:
    #         valid, free = line.user_form.account_manager.IsGIDValidAndFree(line.entry.get_value_as_int())
    #         if valid and not free:
    #             return "ok_visible"
    #         else:
    #             return "The group has to exist already."
    #     return _("Gids have to be in range 1000 to 30000")

    @staticmethod
    def no_validator(line):
        """ do not use the validation icon """
        return None


class Updaters():
    @staticmethod
    def username_updater(line):
        """ updating the home placeholder text after a username change """
        line.user_form.homedir.entry.set_text(os.path.join(config.get_config().parser.get('users', 'home_base_directory'), line.entry.get_text()))
        line.user_form.set_apply_sensitivity()

    @staticmethod
    def homedir_updater(line):
        """ updating the home placeholder text after a username change """
        print("homedirupdated")
        print(line.get_value(), line.valid())
        move_files = line.user_form.builder.get_object('move_files')
        move_files.set_visible(line.changed() and line.valid())

        line.user_form.set_apply_sensitivity()
