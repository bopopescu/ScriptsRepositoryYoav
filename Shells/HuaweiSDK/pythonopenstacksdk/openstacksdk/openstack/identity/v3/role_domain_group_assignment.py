# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from openstack.identity import identity_service
from openstack import resource2 as resource


class RoleDomainGroupAssignment(resource.Resource):
    resource_key = 'role'
    resources_key = 'roles'
    base_path = '/domains/%(domain_id)s/groups/%(group_id)s/roles'
    service = identity_service.IdentityService()

    # capabilities
    allow_list = True

    # Properties
    #: name of the role *Type: string*
    name = resource.Body('name')
    #: The links for the service resource.
    links = resource.Body('links')
    #: The ID of the domain to list assignment from. *Type: string*
    domain_id = resource.URI('domain_id')
    #: The ID of the group to list assignment from. *Type: string*
    group_id = resource.URI('group_id')
