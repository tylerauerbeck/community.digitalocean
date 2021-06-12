#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: digital_ocean_load_balancer
short_description: Manage DigitalOcean load balancers
description:
     - Create and delete a load balancer in DigitalOcean
author: "Tyler Auerbeck (@tylerauerbeck)"
options:
  state:
    description:
      - Indicate desired state of the target.
      - C(present) will create the named droplet; be mindful of the C(unique_name) parameter.
      - C(absent) will delete the named droplet, if it exists.
    default: present
    choices: ['present', 'absent']
    type: str
  id:
    description:
     - Unique ID of load balancer that you want to manage
    type: str
  name:
    description:
     - Human readable name of your load balancer 
    type: str
    required: true
  algorithm:
    description:
      - The load balancing algorithm to be used to direct traffic to the appropriate droplet
      - Can be either C(round_robin) or C(least_connections)
    default: round_robin
    choices: ['round_robin', 'least_connections']
    type: str
  size:
    description:
      - The size of the load balancer. Once created, the size cannot be changed.
      - Can be one of the following: C(lb-small), C(lb-medium), or C(lb-large).
    default: lb-small
    choices: ['lb-small', 'lb-medium', 'lb-large']
    type: str
  region:
    description:
      - The region where the load balancer instance will be created.
      - This should be the slug identifier associated with the region (ex: nyc-1)
    type: str
    required: true
  forwarding_rules:
    description:
      - A list of forwarding rules to be associated with a load balancer
      - At least one forwarding rule is required when creating a new load balancer
    required: true
    type: list
    elements: dict
    suboptions:
      entry_protocol:
        description:
          - The protocol used for traffic to the load balancer
          - Choices are C(https), C(http), C(http2), or C(tcp)
        type: str
        choices: ['https','http','http2','tcp']
        required: true
      entry_port:
        description:
          - Port on which the load balancer will listen
        type: int
        required: true
      target_protocol:
        description:
          - The protocol used from the load balancer to the backend droplets
          - Choices are C(https), C(http), C(http2), or C(tcp)
        choices: ['https','http','http2','tcp']
        required: true
        type: str
      target_port:
        description:
          - Port that the load balancer will send traffic to on the backend droplets
        type: int
        required: true
      certificate_id:
        description:
          - ID of the DigitalOcean certificate that will be used for SSL termination
        type: str
      tls_passthrough:
        description:
          - Whether encrypted traffic will be passed through to the backend droplets
        type: bool
  health_check:
    description:
      - Configuration specifying health check settings for the load balancer
    type: dict
    suboptions:
      protocol:
        description:
        type:
        required:
      port:
        description:
        type:
        required:
      path:
        description:
        type:
      check_interval_seconds:
        description:
        type:
      response_timeout_seconds:
        description:
        type:
      unhealthy_threshold:
        description:
        type:
      healthy_threshold:
        description:
        type:
  sticky_sessions:
    description:
      - TODO
    type: list
    elements: dict
    suboptions:
      - TODO
  unsecure_redirect:
    description:
      - Whether to redirect http requests to https
      - Requests to the load balancer on port 80 will be redirected to 443
    type: bool
  enable_proxy_protocol:
    description:
      - Indicates whether the PROXY protocol should be used to pass information from connecting client requests to the backend service
      - This may required additional configuration on the backend droplets.
    type: bool
  enable_backend_keepalive:
    description:
    - Indicates whether HTTP keepalive connections are maintained to target droplets
    - This may required additional configuration on the backend droplets.
    type: bool
  vpc_uuid:
    description:
      - UUID of the VPC that the load-balancer should be assigned to.
      - If not provided, the load balancer will be assigned to your accounts default VPC
    type: str
  droplet_ids:
    description:
      - List of droplet UUIDs that should be assigned to the load balancer
    type: list
    elements: str
'''


EXAMPLES = r'''
TODO: Examples
'''

RETURN = r'''
# Digital Ocean API info https://developers.digitalocean.com/documentation/v2/#load-balancers
data:
    description: a DigitalOcean Load balancer
    returned: changed
    type: dict
    sample: {
TODO: Sample data
    }
'''

import time
import json
from ansible.module_utils.basic import AnsibleModule, env_fallback
from ansible_collections.community.digitalocean.plugins.module_utils.digital_ocean import DigitalOceanHelper


class DODroplet(object):
    def __init__(self, module):
        self.rest = DigitalOceanHelper(module)
        self.module = module
        self.wait = self.module.params.pop('wait', True)
        self.wait_timeout = self.module.params.pop('wait_timeout', 120)
        self.unique_name = self.module.params.pop('unique_name', False)
        # pop the oauth token so we don't include it in the POST data
        self.module.params.pop('oauth_token')
        self.id = None
        self.name = None
        self.size = None
        self.status = None

    def get_by_id(self, droplet_id):
        if not droplet_id:
            return None
        response = self.rest.get('droplets/{0}'.format(droplet_id))
        json_data = response.json
        if response.status_code == 200:
            droplet = json_data.get('droplet', None)
            if droplet is not None:
                self.id = droplet.get('id', None)
                self.name = droplet.get('name', None)
                self.size = droplet.get('size_slug', None)
                self.status = droplet.get('status', None)
            return json_data
        return None

    def get_by_name(self, droplet_name):
        if not droplet_name:
            return None
        page = 1
        while page is not None:
            response = self.rest.get('droplets?page={0}'.format(page))
            json_data = response.json
            if response.status_code == 200:
                for droplet in json_data['droplets']:
                    if droplet.get('name', None) == droplet_name:
                        self.id = droplet.get('id', None)
                        self.name = droplet.get('name', None)
                        self.size = droplet.get('size_slug', None)
                        self.status = droplet.get('status', None)
                        return {'droplet': droplet}
                if 'links' in json_data and 'pages' in json_data['links'] and 'next' in json_data['links']['pages']:
                    page += 1
                else:
                    page = None
        return None

    def get_addresses(self, data):
        """Expose IP addresses as their own property allowing users extend to additional tasks"""
        _data = data
        for k, v in data.items():
            setattr(self, k, v)
        networks = _data['droplet']['networks']
        for network in networks.get('v4', []):
            if network['type'] == 'public':
                _data['ip_address'] = network['ip_address']
            else:
                _data['private_ipv4_address'] = network['ip_address']
        for network in networks.get('v6', []):
            if network['type'] == 'public':
                _data['ipv6_address'] = network['ip_address']
            else:
                _data['private_ipv6_address'] = network['ip_address']
        return _data

    def get_droplet(self):
        json_data = self.get_by_id(self.module.params['id'])
        if not json_data and self.unique_name:
            json_data = self.get_by_name(self.module.params['name'])
        return json_data

    def resize_droplet(self):
        """API reference: https://developers.digitalocean.com/documentation/v2/#resize-a-droplet (Must be powered off)"""
        if self.status == 'off':
            response = self.rest.post('droplets/{0}/actions'.format(self.id),
                                      data={'type': 'resize', 'disk': self.module.params['resize_disk'], 'size': self.module.params['size']})
            json_data = response.json
            if response.status_code == 201:
                self.module.exit_json(changed=True, msg='Resized Droplet {0} ({1}) from {2} to {3}'.format(
                    self.name, self.id, self.size, self.module.params['size']))
            else:
                self.module.fail_json(msg="Resizing Droplet {0} ({1}) failed [HTTP {2}: {3}]".format(
                    self.name, self.id, response.status_code, response.json.get('message', None)))
        else:
            self.module.fail_json(msg='Droplet must be off prior to resizing (https://developers.digitalocean.com/documentation/v2/#resize-a-droplet)')

    def create(self, state):
        json_data = self.get_droplet()
        droplet_data = None
        if json_data is not None:
            droplet = json_data.get('droplet', None)
            if droplet is not None:
                droplet_size = droplet.get('size_slug', None)
                if droplet_size is not None:
                    if droplet_size != self.module.params['size']:
                        self.resize_droplet()
            droplet_data = self.get_addresses(json_data)
            # If state is active or inactive, ensure requested and desired power states match
            droplet = json_data.get('droplet', None)
            if droplet is not None:
                droplet_id = droplet.get('id', None)
                droplet_status = droplet.get('status', None)
                if droplet_id is not None and droplet_status is not None:
                    if state == 'active' and droplet_status != 'active':
                        power_on_json_data = self.ensure_power_on(droplet_id)
                        self.module.exit_json(changed=True, data=self.get_addresses(power_on_json_data))
                    elif state == 'inactive' and droplet_status != 'off':
                        power_off_json_data = self.ensure_power_off(droplet_id)
                        self.module.exit_json(changed=True, data=self.get_addresses(power_off_json_data))
                    else:
                        self.module.exit_json(changed=False, data=droplet_data)
        if self.module.check_mode:
            self.module.exit_json(changed=True)
        request_params = dict(self.module.params)
        del request_params['id']
        response = self.rest.post('droplets', data=request_params)
        json_data = response.json
        if response.status_code >= 400:
            self.module.fail_json(changed=False, msg=json_data['message'])
        droplet_data = json_data.get("droplet", None)
        if droplet_data is not None:
            droplet_id = droplet_data.get("id", None)
            if droplet_id is not None:
                if self.wait:
                    if state == "active":
                        json_data = self.ensure_power_on(droplet_id)
                    if state == "inactive":
                        json_data = self.ensure_power_off(droplet_id)
                    droplet_data = self.get_addresses(json_data)
                else:
                    if state == "inactive":
                        response = self.rest.post('droplets/{0}/actions'.format(droplet_id), data={'type': 'power_off'})
            else:
                self.module.fail_json(changed=False, msg="Unexpected error, please file a bug")
        else:
            self.module.fail_json(changed=False, msg="Unexpected error, please file a bug")
        self.module.exit_json(changed=True, data=droplet_data)

    def delete(self):
        json_data = self.get_droplet()
        if json_data:
            if self.module.check_mode:
                self.module.exit_json(changed=True)
            response = self.rest.delete('droplets/{0}'.format(json_data['droplet']['id']))
            json_data = response.json
            if response.status_code == 204:
                self.module.exit_json(changed=True, msg='Droplet deleted')
            self.module.fail_json(changed=False, msg='Failed to delete droplet')
        else:
            self.module.exit_json(changed=False, msg='Droplet not found')

    def ensure_power_on(self, droplet_id):
        response = self.rest.post('droplets/{0}/actions'.format(droplet_id), data={'type': 'power_on'})
        end_time = time.monotonic() + self.wait_timeout
        while time.monotonic() < end_time:
            response = self.rest.get('droplets/{0}'.format(droplet_id))
            json_data = response.json
            if json_data['droplet']['status'] == 'active':
                return json_data
            time.sleep(min(10, end_time - time.monotonic()))
        self.module.fail_json(msg='Wait for droplet powering on timeout')

    def ensure_power_off(self, droplet_id):

        # Make sure Droplet is active first
        end_time = time.monotonic() + self.wait_timeout
        while time.monotonic() < end_time:
            response = self.rest.get('droplets/{0}'.format(droplet_id))
            json_data = response.json
            if response.status_code >= 400:
                self.module.fail_json(changed=False, msg=json_data['message'])

            droplet = json_data.get("droplet", None)
            if droplet is None:
                self.module.fail_json(changed=False, msg="Unexpected error, please file a bug (no droplet)")

            droplet_status = droplet.get("status", None)
            if droplet_status is None:
                self.module.fail_json(changed=False, msg="Unexpected error, please file a bug (no status)")

            if droplet_status == "active":
                break

            time.sleep(min(10, end_time - time.monotonic()))

        # Trigger power-off
        response = self.rest.post('droplets/{0}/actions'.format(droplet_id), data={'type': 'power_off'})
        json_data = response.json
        if response.status_code >= 400:
            self.module.fail_json(changed=False, msg=json_data['message'])

        # Save the power-off action
        action = json_data.get("action", None)
        action_id = action.get("id", None)
        if action is None or action_id is None:
            self.module.fail_json(changed=False, msg="Unexpected error, please file a bug (no power-off action or id)")

        # Keep checking till it is done or times out
        end_time = time.monotonic() + self.wait_timeout
        while time.monotonic() < end_time:
            response = self.rest.get('droplets/{0}/actions/{1}'.format(droplet_id, action_id))
            json_data = response.json
            if response.status_code >= 400:
                self.module.fail_json(changed=False, msg=json_data['message'])

            action = json_data.get("action", None)
            action_status = action.get("status", None)
            if action is None or action_status is None:
                self.module.fail_json(changed=False, msg="Unexpected error, please file a bug (no action or status)")

            if action_status == "completed":
                response = self.rest.get('droplets/{0}'.format(droplet_id))
                json_data = response.json
                if response.status_code >= 400:
                    self.module.fail_json(changed=False, msg=json_data['message'])
                return(json_data)

            time.sleep(min(10, end_time - time.monotonic()))

        self.module.fail_json(msg='Wait for droplet powering off timeout')


def core(module):
    state = module.params.pop('state')
    droplet = DODroplet(module)
    if state == 'present' or state == 'active' or state == 'inactive':
        droplet.create(state)
    elif state == 'absent':
        droplet.delete()


def main():
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(choices=['present', 'absent', 'active', 'inactive'], default='present'),
            oauth_token=dict(
                aliases=['API_TOKEN'],
                no_log=True,
                fallback=(env_fallback, ['DO_API_TOKEN', 'DO_API_KEY', 'DO_OAUTH_TOKEN']),
                required=True,
            ),
            name=dict(type='str'),
            size=dict(aliases=['size_id']),
            image=dict(aliases=['image_id']),
            region=dict(aliases=['region_id']),
            ssh_keys=dict(type='list', elements='str', no_log=False),
            private_networking=dict(type='bool', default=False),
            vpc_uuid=dict(type='str'),
            backups=dict(type='bool', default=False),
            monitoring=dict(type='bool', default=False),
            id=dict(aliases=['droplet_id'], type='int'),
            user_data=dict(default=None),
            ipv6=dict(type='bool', default=False),
            volumes=dict(type='list', elements='str'),
            tags=dict(type='list', elements='str'),
            wait=dict(type='bool', default=True),
            wait_timeout=dict(default=120, type='int'),
            unique_name=dict(type='bool', default=False),
            resize_disk=dict(type='bool', default=False),
        ),
        required_one_of=(
            ['id', 'name'],
        ),
        required_if=([
            ('state', 'present', ['name', 'size', 'image', 'region']),
            ('state', 'active', ['name', 'size', 'image', 'region']),
            ('state', 'inactive', ['name', 'size', 'image', 'region']),
        ]),
        supports_check_mode=True,
    )

    core(module)


if __name__ == '__main__':
    main()
