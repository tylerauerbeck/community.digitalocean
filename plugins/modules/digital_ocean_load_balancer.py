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
          - Protocol used to send health checks to backend droplets
          - Options are C(http), C(https), or C(tcp)
        type: str
        choices: ['http','https','tcp']
        required: true
      port:
        description:
          - Port used to connect for health checks on backend droplets
        type: int
        required: true
      path:
        description:
          - The path on the backend droplet which health check requests are sent
        type: str
        default: "/"
      check_interval_seconds:
        description:
          - The number of seconds between two consecutive health checks
        type: int
        default: 10
      response_timeout_seconds:
        description:
          - The number of seconds a health check will wait before considering it failed
          - Must be between 3 and 300
        default: 5
        type: int
      unhealthy_threshold:
        description:
          - The number of times a health check must fail before a backend droplet will be considered unhealthy
          - Must be between 2 and 10
        default: 3
        type: int
      healthy_threshold:
        description:
          - The number of times a health check must pass before a backend droplet will be considered healthy
          - Must be between 2 and 10
        default: 5
        type: int
  sticky_sessions:
    description:
      - Configuration specifying how sticky sessions should be used by the load balancer
    type: dict
    suboptions:
      type:
        description:
          - Indicates how and if requests from a client will be persistently served by the same backend droplet 
          - Options are C(cookies) or C(none)
        type: str
        choices: ["cookies","none"]
        default: "none"
      cookie_name:
        description:
          - The name to be used for the cookie sent to the client.
          - This is required when type is C(cookie)
        type: str
        #TODO: Need to tie cookie_name and type together
      cookie_ttl_seconds:
        description:
          - Number of seconds until the cookie set by the load balancer expires 
          - This is required when type is C(cookie)
  redirect_http_to_https:
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


class DOLoadBalancer(object):
    def __init__(self, module):
        self.rest = DigitalOceanHelper(module)
        self.module = module
#        self.wait = self.module.params.pop('wait', True)
#        self.wait_timeout = self.module.params.pop('wait_timeout', 120)
        # pop the oauth token so we don't include it in the POST data
        self.module.params.pop('oauth_token')
        self.id = None
        self.name = None

    def get_by_id(self, lb_id):
        if not lb_id:
            return None
        response = self.rest.get('load_balancers/{0}'.format(lb_id))
        json_data = response.json
        if response.status_code == 200:
            lb = json_data.get('load_balancer', None)
            if lb is not None:
                self.id = lb.get('id', None)
                self.name = lb.get('name', None)
                self.size = lb.get('size', None)
            return json_data
        return None

    def get_by_name(self, lb_name):
        if not lb_name:
            return None
        page = 1
        while page is not None:
            response = self.rest.get('load_balancers?page={0}'.format(page))
            json_data = response.json
            if response.status_code == 200:
                for lb in json_data['load_balancers']:
                    if lb.get('name', None) == lb_name:
                        self.id = lb.get('id', None)
                        self.name = lb.get('name', None)
                        self.size = lb.get('size', None)
                        return {'load_balancer': lb}
                if 'links' in json_data and 'pages' in json_data['links'] and 'next' in json_data['links']['pages']:
                    page += 1
                else:
                    page = None
        return None

    def get_lb(self):
        json_data = self.get_by_id(self.module.params['id'])
        if not json_data:
            json_data = self.get_by_name(self.module.params['name'])
        return json_data

    def create(self, state):
        json_data = self.get_lb()
        request_params = dict(self.module.params)

        if json_data is not None:
            lb = json_data.get('load_balancer', None)
            if lb is not None:
                lb_size = lb.get('size', None)
                if lb_size is not None:
                    if lb_size != self.module.params['size']:
                        self.module.fail_json(changed=False, msg="Load Balancer sizes cannot be changed after initial creation. Either create a new load-balancer or delete the existing load-balancer before proceeding.")
                response = self.rest.put('load_balancers/{0}'.format(json_data["load_balancer"]["id"]), data=request_params)

                if response.status_code != 200:
                    self.module.fail_json(changed=False, msg=response.json)
                self.module.exit_json(changed=True, data=response.json)
        else:
            response = self.rest.post('load_balancers', data=self.module.params)  

            if response.status_code != 202:
                self.module.fail_json(changed=False, msg=response.json)
            self.module.exit_json(changed=True, data=response.json)

    def delete(self):
        json_data = self.get_lb()
        if json_data:
            if self.module.check_mode:
                self.module.exit_json(changed=True)
            response = self.rest.delete('droplets/{0}'.format(json_data['droplet']['id']))
            if response.status_code == 204:
                self.module.exit_json(changed=True, msg='Load-balancer deleted')
            self.module.fail_json(changed=False, msg='Failed to delete load-balancer')
        else:
            self.module.exit_json(changed=False, msg='Load-balancer not found')

def core(module):
    state = module.params.pop('state')
    lb = DOLoadBalancer(module)
    if state == 'present':
        lb.create(state)
    elif state == 'absent':
        lb.delete()

forwarding_rule_argspec = dict(
    entry_protocol=dict(type='str',required=True,choices=["http","https","http2","tcp"]),
    entry_port=dict(type='int', required=True),
    target_protocol=dict(type='str', required=True,choices=["http","https","http2","tcp"]),
    target_port=dict(type='int',required=True),
    certificate_id=dict(type='str',default=""),
    tls_passthrough=dict(type='bool',default=False),
)

sticky_argspec = dict(
    type=dict(type='str',required=True,choices=['none','cookie']),
    cookie_name=dict(type='str'),
    cookie_ttl_seconds=dict(type='int'),
    required_if=[
        ('type','cookie', ['cookie_name',"cookie_ttl_seconds"])
    ]
)

health_check_argspec = dict(
    protocol=dict(type='str',required=True,choices=['http','https','tcp']),
    port=dict(type='int',required=True),
    path=dict(type='str',default="/"),
    check_interval_seconds=dict(type='int',default=10),
    response_timeout_seconds=dict(type='int',default=5),
    unhealthy_threshold=dict(type='int',default=3),
    healthy_threshold=dict(type='int',default=5)
)

def main():
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(choices=['present', 'absent'], default='present'),
            oauth_token=dict(
                aliases=['API_TOKEN'],
                no_log=True,
                fallback=(env_fallback, ['DO_API_TOKEN', 'DO_API_KEY', 'DO_OAUTH_TOKEN']),
                required=True,
            ),
            name=dict(type='str',required=True),
            size=dict(type='str',choices=['lb-small','lb-medium','lb-large'],default="lb-small"),
            algorithm=dict(type='str',choices=['round_robin','least_connections'],default="round_robin"),
            region=dict(type='str',required=True),
            forwarding_rules=dict(type="list",elements="dict",required=True,options=forwarding_rule_argspec),
            health_check=dict(type='dict',options=health_check_argspec),
            redirect_http_to_https=dict(type='bool',default=False),
            enable_proxy_protocol=dict(type='bool'),
            enable_backend_keepalive=dict(type='bool'),
            sticky_sessions=dict(type='dict',options=sticky_argspec),
            vpc_uuid=dict(type='str'),
            droplet_ids=dict(type='list',elements='dict'),
            id=dict(aliases=['droplet_id'], type='int'),
        ),
        required_one_of=(
            ['id', 'name'],
        ),
#        required_if=([
#            ('state', 'present', ['name', 'size', 'image', 'region']),
#        ]),
#        supports_check_mode=True,
    )

    core(module)


if __name__ == '__main__':
    main()
