#
# core.py
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

import logging, json, urllib2, time, hashlib
from deluge.plugins.pluginbase import CorePluginBase
from deluge.core.rpcserver import export
from deluge.event import DelugeEvent
import deluge.component as component
import deluge.configmanager

DEFAULT_PREFS = {
    "xbmc_host":"localhost",
    "xbmc_port":"8080",
    "xbmc_user":"xbmc",
    "xbmc_password":"xbmc",
    "replacements" : []
}

REPLACEMENT_ID = 0
REPLACEMENT_PATTERN = 1
REPLACEMENT_REPLACEMENT = 2

log = logging.getLogger(__name__)

class ReplacementAddedEvent(DelugeEvent):
    """
    Emitted when a new replacement is added.
    """
    def __init__(self, replacement_id, pattern, replacement):
        self._args = [replacement_id, pattern, replacement]

class ReplacementRemovedEvent(DelugeEvent):
    """
    Emitted when a replacement is removed.
    """
    def __init__(self, replacement_id):
        self._args = [replacement_id]

class Core(CorePluginBase):

    def load(self):
        client.register_event_handler("ReplacementAddedEvent", self.on_command_added_event)

    def enable(self):
        self.config = deluge.configmanager.ConfigManager("xbmcupdater.conf", DEFAULT_PREFS)
        component.get("EventManager").register_event_handler("TorrentFinishedEvent", self._on_torrent_finished)


    def update(self):
        pass

    def _on_torrent_finished(self, torrent_id):
        log.debug("XBMCUpdater Finish torrent: %s" % torrent_id)

        tid = component.get("TorrentManager").torrents[torrent_id]
        tid_status = tid.get_status(["save_path", "move_completed", "name"])
        path = tid_status["save_path"]
        for (replacement_id, pattern, replacement) in self.config["replacements"]:
            if pattern in path:
                path = path.replace(pattern,replacement)
                break

        auth = ""
        user = self.config["xbmc_user"]
        passwd = self.config["xbmc_password"]

        if len(user) > 0:
            auth += user
            if len(passwd) > 0 :
                auth += (":" + passwd)

        if len(auth) > 0:
            auth += "@"

        url = "http://%s%s:%s/jsonrpc" % (auth,self.config["xbmc_host"],self.config["xbmc_port"])
        data = json.dumps({"jsonrpc":"2.0", "method" : "VideoLibrary.scan", "arguments": { "directory" : path}})
        req = urllib2.Request(url, data, {'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)
        response = f.read()
        f.close()


   ### Exported RPC methods ###
    @export
    def add_replacement(self, pattern, replacement):
        replacement_id = hashlib.sha1(str(time.time())).hexdigest()
        self.config["replacements"].append((replacement_id, pattern, replacement))
        self.config.save()
        component.get("EventManager").emit(ReplacementAddedEvent(replacement_id, pattern, replacement))

    @export
    def get_replacements(self):
        return self.config["replacements"]

    @export
    def remove_replacement(self, replacement_id):
        for replacement in self.config["replacements"]:
            if replacement[REPLACEMENT_ID] == replacement_id:
                self.config["replacements"].remove(replacement)
                component.get("EventManager").emit(ReplacementRemovedEvent(replacement_id))
                break
        self.config.save()

    @export
    def save_command(self, replacement_id, pattern, replacement):
        for i, replacement in enumerate(self.config["replacements"]):
            if command[REPLACEMENT_ID] == replacement_id:
                self.config["replacements"][i] = (replacement_id, pattern, replacement)
                break
        self.config.save()


    @export
    def set_config(self, config):
        """Sets the config dictionary"""
        for key in config.keys():
            self.config[key] = config[key]
        self.config.save()

    @export
    def get_config(self):
        """Returns the config dictionary"""
        return self.config.config

