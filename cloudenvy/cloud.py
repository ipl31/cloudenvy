# vim: tabstop=4 shiftwidth=4 softtabstop=4
import functools
import exceptions
import logging

import novaclient.exceptions
import novaclient.client


def not_found(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except novaclient.exceptions.NotFound:
            return None
    return wrapped


def bad_request(func):
    """decorator to wrap novaclient functions that may return a
    400 'BadRequest' exception when the endpoint is unavailable or
    unable to be resolved.
    """
    #novaclient.exceptions.BadRequest
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except novaclient.exceptions.BadRequest:
            logging.error("Unable to communicate with endpoints: "
                          "Received 400/Bad Request from OpenStack.")
            exit()
    return wrapped


class CloudAPI(object):
    def __init__(self, config):
        self._client = None
        self.config = config
        self.user_config = config['cloudenvy']
        self.project_config = config['project_config']

        # OpenStack Auth Items
        self.user = self.user_config['cloud'].get('os_username', None)
        self.password = self.user_config['cloud'].get('os_password', None)
        self.tenant_name = self.user_config['cloud'].get('os_tenant_name',
                                                         None)
        self.auth_url = self.user_config['cloud'].get('os_auth_url', None)

    @property
    def client(self):
        if not self._client:
            self._client = novaclient.client.Client(
                '2',
                self.user,
                self.password,
                self.tenant_name,
                self.auth_url,
                no_cache=True)
        return self._client

    @bad_request
    def list_servers(self):
        return self.client.servers.list()

    @bad_request
    @not_found
    def find_server(self, name):
        return self.client.servers.find(name=name)

    @bad_request
    @not_found
    def get_server(self, server_id):
        return self.client.servers.get(server_id)

    @bad_request
    def create_server(self, *args, **kwargs):
        return self.client.servers.create(*args, **kwargs)

    @bad_request
    def find_free_ip(self):
        fips = self.client.floating_ips.list()
        for fip in fips:
            if not fip.instance_id:
                return fip.ip
        raise exceptions.NoIPsAvailable()

    @bad_request
    def find_ip(self, server_id):
        fips = self.client.floating_ips.list()
        for fip in fips:
            if fip.instance_id == server_id:
                return fip.ip

    @bad_request
    def assign_ip(self, server, ip):
        server.add_floating_ip(ip)

    @bad_request
    @not_found
    def find_image(self, search_str):
        try:
            # find by name
            image = self.client.images.find(name=search_str)
        except novaclient.exceptions.NotFound:
            try:
                # find by id
                image = self.client.images.get(search_str)
            except novaclient.exceptions.NotFound:
                raise SystemExit('Image `%s` Not Found' % search_str)
        return image

    @bad_request
    @not_found
    def get_image(self, image_id):
        return self.client.images.get(image_id)

    @bad_request
    def snapshot(self, server, name):
        return self.client.servers.create_image(server, name)

    @bad_request
    @not_found
    def find_flavor(self, name):
        return self.client.flavors.find(name=name)

    @bad_request
    @not_found
    def find_security_group(self, name):
        return self.client.security_groups.find(name=name)

    @bad_request
    @not_found
    def create_security_group(self, name):
        return self.client.security_groups.create(name, name)

    def create_security_group_rule(self, security_group, rule):
        return self.client.security_group_rules.create(
            security_group.id, *rule)

    @bad_request
    def allocate_floating_ip(self):
        return self.client.floating_ips.create()

    @bad_request
    @not_found
    def find_keypair(self, name):
        return self.client.keypairs.find(name=name)

    @bad_request
    def create_keypair(self, name, key_data):
        return self.client.keypairs.create(name, public_key=key_data)
