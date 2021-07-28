#!/usr/bin/env python3

# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.

# Note: This class is used to bind different type of controller together.
# Other controller like node, cluster, storageset, service inheriting
# from this class.
import ast
from ha import const
from ha.core.config.config_manager import ConfigManager
from ha.execute import SimpleCommand
from ha.const import BMC_CREDENTIALS
from ha.util.stonith_service import StonithService

class Ipmitool(StonithService):
    """ Tool to manage IPMI-enabled devices """

    def __init__(self):
        """
        Initialize Stonith tool class.
        """
        super(Ipmitool, self).__init__()
        self._confstore = ConfigManager.get_confstore()
        self._execute = SimpleCommand()

    def power_off(self, nodeid: str):
        """
        Power OFF node with nodeid

        Args:
            nodeid (str): Node ID from cluster nodes.
        """
        try:
            bmc_info = self._confstore.get(f"{const.NODE_BMC_INFO_KEY}/node/{nodeid}")
            if bmc_info is not None:
                _, value = bmc_info.popitem()
                bmc_info_dict = ast.literal_eval(value)
                self._execute.run_cmd(f"ipmitool -I lanplus -H {bmc_info_dict[BMC_CREDENTIALS.IPMI_IPADDR.value]} -U {bmc_info_dict[BMC_CREDENTIALS.IPMI_USER.value]} -P {bmc_info_dict[BMC_CREDENTIALS.IPMI_PASSWORD.value]} chassis status")

        except Exception as e:
            raise Exception("Failed to run IPMItool Command. Error : {e}")

    def power_on(self, nodeid: str):
        """
        Power ON node with nodeid

        Args:
            nodeid (str): Node ID from cluster nodes.
        """
        pass
