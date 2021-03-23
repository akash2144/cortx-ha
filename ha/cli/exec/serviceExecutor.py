#!/usr/bin/env python3

# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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

from ha.core.error import HAUnimplemented
from ha.cli.exec.commandExecutor import CommandExecutor

class ServiceStartExecutor(CommandExecutor):

    def validate(self) -> str:
        raise HAUnimplemented("This operation is not implemented.")

    def execute(self) -> str:
        raise HAUnimplemented("This operation is not implemented.")


class ServiceStopExecutor(CommandExecutor):
    def validate(self) -> str:
        raise HAUnimplemented("This operation is not implemented.")

    def execute(self) -> str:
        raise HAUnimplemented("This operation is not implemented.")

class ServiceStatusExecutor(CommandExecutor):

    def validate(self) -> str:
        raise HAUnimplemented("This operation is not implemented.")

    def execute(self) -> str:
        raise HAUnimplemented("This operation is not implemented.")
