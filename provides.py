# Copyright 2019 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from charms import reactive
import charmhelpers.contrib.network.ip as ch_net_ip


class MySQLRouterProvides(reactive.Endpoint):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ingress_address = ch_net_ip.get_relation_ip(self.endpoint_name)

    def relation_ids(self):
        return [x.relation_id for x in self.relations]

    def set_ingress_address(self):
        for relation in self.relations:
            relation.to_publish_raw["ingress-address"] = self.ingress_address
            relation.to_publish_raw["private-address"] = self.ingress_address

    def available(self):
        for unit in self.all_joined_units:
            # Check for prefixed username
            for key in unit.received.keys():
                if "_username" in key:
                    return True
        return False

    @reactive.when('endpoint.{endpoint_name}.joined')
    def joined(self):
        reactive.clear_flag(self.expand_name('{endpoint_name}.available'))
        reactive.set_flag(self.expand_name('{endpoint_name}.connected'))
        self.set_ingress_address()

    @reactive.when('endpoint.{endpoint_name}.changed')
    def changed(self):
        flags = (
            self.expand_name(
                'endpoint.{endpoint_name}.changed.database'),
            self.expand_name(
                'endpoint.{endpoint_name}.changed.username'),
            self.expand_name(
                'endpoint.{endpoint_name}.changed.hostname'),
        )
        if reactive.all_flags_set(*flags):
            for flag in flags:
                reactive.clear_flag(flag)

        if self.available():
            reactive.set_flag(self.expand_name('{endpoint_name}.available'))
        else:
            reactive.clear_flag(self.expand_name('{endpoint_name}.available'))

    @reactive.when_any('endpoint.{endpoint_name}.broken',
                       'endpoint.{endpoint_name}.departed')
    def departed(self):
        flags = (
            self.expand_name('{endpoint_name}.connected'),
            self.expand_name('{endpoint_name}.available'),
        )
        for flag in flags:
            reactive.clear_flag(flag)

    def set_db_connection_info(
            self, relation_id, db_host, password,
            allowed_units=None, prefix=None):
        """Send database connection information to the client.

        :param relation_id: Relation ID to set connection information on
        :type relation_id: str
        :param db_host: Host IP or hostname for connecting to the DB
        :type db_host: str
        :param password: Password for connecting to the DB
        :type password: str
        :param allowed_units: Space delimited unit names allowed to connect to
                              the DB.
        :type allowed_units: str
        :param prefix: Prefix to use for responses.
        :type prefix: str
        :side effect: Data is set on the relation
        :returns: None, this function is called for its side effect
        :rtype: None
        """
        # No prefix for db_host
        self.relations[relation_id].to_publish["db_host"] = db_host
        if not prefix:
            self.relations[relation_id].to_publish["password"] = password
            self.relations[relation_id].to_publish[
                "allowed_units"] = allowed_units
        else:
            self.relations[relation_id].to_publish[
                "{}_password".format(prefix)] = password
            self.relations[relation_id].to_publish[
                "{}_allowed_units".format(prefix)] = allowed_units
