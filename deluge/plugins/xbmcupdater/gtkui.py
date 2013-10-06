#
# gtkui.py
#
# Copyright (C) 2013 Emil Palm <emil@x86.nu>
#
# Basic plugin template created by:
# Copyright (C) 2008 Martijn Voncken <mvoncken@gmail.com>
# Copyright (C) 2007-2009 Andrew Resch <andrewresch@gmail.com>
# Copyright (C) 2009 Damien Churchill <damoxc@gmail.com>
# Copyright (C) 2010 Pedro Algarvio <pedro@algarvio.me>
#
# Deluge is free software.
#
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# deluge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with deluge.    If not, write to:
# 	The Free Software Foundation, Inc.,
# 	51 Franklin Street, Fifth Floor
# 	Boston, MA  02110-1301, USA.
#
#    In addition, as a special exception, the copyright holders give
#    permission to link the code of portions of this program with the OpenSSL
#    library.
#    You must obey the GNU General Public License in all respects for all of
#    the code used other than OpenSSL. If you modify file(s) with this
#    exception, you may extend this exception to your version of the file(s),
#    but you are not obligated to do so. If you do not wish to do so, delete
#    this exception statement from your version. If you delete this exception
#    statement from all source files in the program, then also delete it here.
#

import gtk
import logging
from deluge.ui.client import client
from deluge.plugins.pluginbase import GtkPluginBase
import deluge.component as component
import deluge.common
from deluge.event import TorrentFinishedEvent

from common import get_resource

log = logging.getLogger(__name__)

class GtkUI(GtkPluginBase):
    def enable(self):
        self.glade = gtk.glade.XML(get_resource("config.glade"))
        component.get("Preferences").add_page("XBMCUpdater", self.glade.get_widget("vbox1"))
        component.get("PluginManager").register_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").register_hook("on_show_prefs", self.on_show_prefs)
        client.register_event_handler("ReplacementAddedEvent", self.on_replacement_added_event)
        client.register_event_handler("ReplacementRemovedEvent", self.on_replacement_removed_event)
        self.load()

    def add_replacement(self, replacement_id, pattern, replacement):
        log.debug("Adding replacement `%s`", replacement_id)
        vbox = self.glade.get_widget("replacements_vbox")
        hbox = gtk.HBox(False, 5)
        hbox.set_name(replacement_id + "_" + pattern)
        pattern_label = gtk.Label(pattern)
        replacement_label = gtk.Label(replacement)
        button = gtk.Button()
        button.set_name("remove_%s" % replacement_id)
        button.connect("clicked", self.on_remove_button_clicked)

        img = gtk.Image()
        img.set_from_stock(gtk.STOCK_REMOVE, gtk.ICON_SIZE_BUTTON)
        button.set_image(img)

        hbox.pack_start(pattern_label, False, False)
        hbox.pack_start(replacement_label, False, False)
        hbox.pack_start(button, False, False)
        hbox.show_all()
        vbox.pack_start(hbox)

    def remove_replacement(self, replacement_id):
        vbox = self.glade.get_widget("replacements_vbox")
        children = vbox.get_children()
        for child in children:
            if child.get_name().split("_")[0] == replacement_id:
                vbox.remove(child)
                break

    def clear_replacements(self):
        vbox = self.glade.get_widget("replacements_vbox")
        children = vbox.get_children()
        for child in children:
            vbox.remove(child)


    def load_replacements(self):
        def on_get_replacements(replacements):
            self.clear_replacements()
            log.debug("on_get_replacements: %s", replacements)
            for _replacement in replacements:
                replacement_id, pattern, replacement = _replacement
                self.add_replacement(replacement_id, pattern, replacement)

        client.xbmcupdater.get_replacements().addCallback(on_get_replacements)

    def on_add_button_clicked(self, *args):
        log.debug("add button clicked")
        pattern = self.glade.get_widget("pattern").get_text()
        replacement = self.glade.get_widget("replacement").get_text()
        client.xbmcupdater.add_replacement(pattern, replacement)
        # torrent_manager = component.get('TorrentManager')
        # for torrent_id in torrent_manager.get_torrent_list():
        #     component.get("EventManager").emit(TorrentFinishedEvent(torrent_id))    

    def load(self):
        self.glade.signal_autoconnect({
            "on_add_button_clicked": self.on_add_button_clicked,
            "on_remove_button_clicked": self.on_remove_button_clicked
        })
        self.load_replacements()

    def disable(self):
        component.get("Preferences").remove_page("XBMCUpdater")
        component.get("PluginManager").deregister_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").deregister_hook("on_show_prefs", self.on_show_prefs)

    def on_apply_prefs(self):
        log.debug("applying prefs for XBMCUpdater")
        config = {
            "xbmc_host":self.glade.get_widget("xbmc_host").get_text(),
            "xbmc_port":self.glade.get_widget("xbmc_port").get_text(),
            "xbmc_user":self.glade.get_widget("xbmc_user").get_text(),
            "xbmc_password":self.glade.get_widget("xbmc_password").get_text(),
        }
        client.xbmcupdater.set_config(config)

    def on_show_prefs(self):
        client.xbmcupdater.get_config().addCallback(self.cb_get_config) 

    
    def on_remove_button_clicked(self, widget, *args):
        replacement_id = widget.get_name().replace("remove_", "")
        client.xbmcupdater.remove_replacement(replacement_id)

    def cb_get_config(self, config):
        "callback for on show_prefs"
        self.glade.get_widget("xbmc_host").set_text(config["xbmc_host"])
        self.glade.get_widget("xbmc_port").set_text(config["xbmc_port"])
        self.glade.get_widget("xbmc_user").set_text(config["xbmc_user"])
        self.glade.get_widget("xbmc_password").set_text(config["xbmc_password"])


    def on_replacement_added_event(self, replacement_id, pattern, replacement):
        log.debug("Adding replacement %s: %s", pattern, replacement)
        self.add_replacement(replacement_id, pattern, replacement)

    def on_replacement_removed_event(self, replacement_id):
        log.debug("Removing replacement %s", replacement_id)
        self.remove_replacement(replacement_id)
