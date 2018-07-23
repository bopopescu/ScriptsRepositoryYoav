#!/usr/bin/python
# -*- coding: utf-8 -*-

from cloudshell.devices.driver_helper import get_logger_with_thread_id, get_api, get_cli
from cloudshell.devices.driver_helper import parse_custom_commands
from cloudshell.devices.standards.networking.configuration_attributes_structure import \
    create_networking_resource_from_context
from cloudshell.networking.cisco.nxos.cli.cisco_nxos_cli_handler import CiscoNXOSCliHandler as CliHandler
from cloudshell.networking.cisco.nxos.runners.cisco_nxos_connectivity_runner import \
    CiscoNXOSConnectivityRunner as ConnectivityRunner
from cloudshell.networking.cisco.nxos.runners.cisco_nxos_configuration_runner import \
    CiscoNXOSConfigurationRunner as ConfigurationRunner
from cloudshell.networking.cisco.nxos.snmp.cisco_nxos_snmp_handler import CiscoNXOSSnmpHandler as SNMPHandler
from cloudshell.networking.cisco.runners.cisco_autoload_runner import \
    CiscoAutoloadRunner as AutoloadRunner
from cloudshell.networking.cisco.nxos.runners.cisco_nxos_firmware_runner import \
    CiscoNXOSFirmwareRunner as FirmwareRunner

from cloudshell.devices.runners.run_command_runner import RunCommandRunner as CommandRunner
from cloudshell.devices.runners.state_runner import StateRunner as StateRunner
from cloudshell.networking.networking_resource_driver_interface import NetworkingResourceDriverInterface
from cloudshell.shell.core.driver_utils import GlobalLock
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
import cloudshell.api.cloudshell_api as csapi


class CiscoNXOSShellDriver(ResourceDriverInterface, NetworkingResourceDriverInterface, GlobalLock):
    SUPPORTED_OS = ["NX[ -]?OS|NXOS"]
    SHELL_NAME = "Cisco NXOS Switch 2G"

    def __init__(self):
        super(CiscoNXOSShellDriver, self).__init__()
        self._cli = None

    def initialize(self, context):
        """Initialize method

        :type context: cloudshell.shell.core.context.driver_context.InitCommandContext
        """

        resource_config = create_networking_resource_from_context(shell_name=self.SHELL_NAME,
                                                                  supported_os=self.SUPPORTED_OS,
                                                                  context=context)

        session_pool_size = int(resource_config.sessions_concurrency_limit)
        self._cli = get_cli(session_pool_size)
        return 'Finished initializing'

    @GlobalLock.lock
    def get_inventory(self, context):
        """Return device structure with all standard attributes

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :return: response
        :rtype: str
        """

        logger = get_logger_with_thread_id(context)
        api = get_api(context)

        resource_config = create_networking_resource_from_context(shell_name=self.SHELL_NAME,
                                                                  supported_os=self.SUPPORTED_OS,
                                                                  context=context)
        cli_handler = CliHandler(self._cli, resource_config, logger, api)
        snmp_handler = SNMPHandler(resource_config, logger, api, cli_handler)

        autoload_operations = AutoloadRunner(logger=logger,
                                             resource_config=resource_config,
                                             snmp_handler=snmp_handler)
        logger.info('Autoload started')
        response = autoload_operations.discover()
        logger.info('Autoload completed')
        return response

    def run_custom_command(self, context, custom_command):
        """Send custom command

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :return: result
        :rtype: str
        """

        logger = get_logger_with_thread_id(context)
        api = get_api(context)

        resource_config = create_networking_resource_from_context(shell_name=self.SHELL_NAME,
                                                                  supported_os=self.SUPPORTED_OS,
                                                                  context=context)

        cli_handler = CliHandler(self._cli, resource_config, logger, api)
        send_command_operations = CommandRunner(logger=logger, cli_handler=cli_handler)

        response = send_command_operations.run_custom_command(custom_command=parse_custom_commands(custom_command))

        return response

    def run_custom_config_command(self, context, custom_command):
        """Send custom command in configuration mode

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :return: result
        :rtype: str
        """

        logger = get_logger_with_thread_id(context)
        api = get_api(context)

        resource_config = create_networking_resource_from_context(shell_name=self.SHELL_NAME,
                                                                  supported_os=self.SUPPORTED_OS,
                                                                  context=context)

        cli_handler = CliHandler(self._cli, resource_config, logger, api)
        send_command_operations = CommandRunner(logger=logger, cli_handler=cli_handler)

        result_str = send_command_operations.run_custom_config_command(
            custom_command=parse_custom_commands(custom_command))

        return result_str

    def ApplyConnectivityChanges(self, context, request):
        """
        Create vlan and add or remove it to/from network interface

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :param str request: request json
        :return:
        """

        logger = get_logger_with_thread_id(context)
        api = get_api(context)

        resource_config = create_networking_resource_from_context(shell_name=self.SHELL_NAME,
                                                                  supported_os=self.SUPPORTED_OS,
                                                                  context=context)

        cli_handler = CliHandler(self._cli, resource_config, logger, api)
        connectivity_operations = ConnectivityRunner(logger=logger, cli_handler=cli_handler)
        logger.info('Start applying connectivity changes, request is: {0}'.format(str(request)))
        result = connectivity_operations.apply_connectivity_changes(request=request)
        logger.info('Finished applying connectivity changes, response is: {0}'.format(str(result)))
        logger.info('Apply Connectivity changes completed')
        return result

    def save_demo(self, context, configuration_type):
        folder_path = context.resource.attributes.get('Cisco NXOS Switch 2G.tftp_server')
        session = csapi.CloudShellAPISession(host=context.connectivity.server_address,
                                             token_id=context.connectivity.admin_auth_token,
                                             domain=context.reservation.domain)
        session.WriteMessageToReservationOutput(
            reservationId=context.reservation.reservation_id,
            message='starting to restore to {}'.format(folder_path)
        )

        vrf_management_name = context.resource.attributes.get('Cisco NXOS Switch 2G.VRF Management Name')
        return self.save(context, configuration_type, folder_path, vrf_management_name)

    def save(self, context, configuration_type, folder_path, vrf_management_name):
        """Save selected file to the provided destination

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :param configuration_type: source file, which will be saved
        :param folder_path: destination path where file will be saved
        :param vrf_management_name: VRF management Name
        :return str saved configuration file name:
        """

        logger = get_logger_with_thread_id(context)
        api = get_api(context)

        resource_config = create_networking_resource_from_context(shell_name=self.SHELL_NAME,
                                                                  supported_os=self.SUPPORTED_OS,
                                                                  context=context)

        if not configuration_type:
            configuration_type = 'running'

        if not vrf_management_name:
            vrf_management_name = resource_config.vrf_management_name

        cli_handler = CliHandler(self._cli, resource_config, logger, api)
        configuration_operations = ConfigurationRunner(cli_handler=cli_handler,
                                                       logger=logger,
                                                       resource_config=resource_config,
                                                       api=api)
        logger.info('Save started')
        response = configuration_operations.save(folder_path=folder_path, configuration_type=configuration_type,
                                                 vrf_management_name=vrf_management_name)
        logger.info('Save completed')
        return response


    def restore_demo(self, context, configuration_type, filename):
        path = r'{0}/{1}'.format(context.resource.attributes.get('Cisco NXOS Switch 2G.tftp_server'), filename)
        session = csapi.CloudShellAPISession(host=context.connectivity.server_address,
                                             token_id=context.connectivity.admin_auth_token,
                                             domain=context.reservation.domain)
        session.WriteMessageToReservationOutput(
            reservationId=context.reservation.reservation_id,
            message='starting to restore from {}'.format(path)
        )
        vrf_management_name = context.resource.attributes.get('Cisco NXOS Switch 2G.VRF Management Name')
        restore_method = 'Append'
        return self.restore(context, path, configuration_type, restore_method, vrf_management_name)

    @GlobalLock.lock
    def restore(self, context, path, configuration_type, restore_method, vrf_management_name):
        """Restore selected file to the provided destination

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :param path: source config file
        :param configuration_type: running or startup configs
        :param restore_method: append or override methods
        :param vrf_management_name: VRF management Name
        """

        logger = get_logger_with_thread_id(context)
        logger.info('Restore process started')
        api = get_api(context)
        session = csapi.CloudShellAPISession(host=context.connectivity.server_address,
                                             token_id=context.connectivity.admin_auth_token,
                                             domain=context.reservation.domain)

        session.WriteMessageToReservationOutput(
            reservationId=context.reservation.reservation_id,
            message="Started Restore"
        )

        resource_config = create_networking_resource_from_context(shell_name=self.SHELL_NAME,
                                                                  supported_os=self.SUPPORTED_OS,
                                                                  context=context)

        if not configuration_type:
            configuration_type = 'running'

        if not restore_method:
            restore_method = 'override'

        if not vrf_management_name:
            vrf_management_name = resource_config.vrf_management_name

        cli_handler = CliHandler(self._cli, resource_config, logger, api)
        configuration_operations = ConfigurationRunner(cli_handler=cli_handler,
                                                       logger=logger,
                                                       resource_config=resource_config,
                                                       api=api)
        logger.info('Restore started')
        configuration_operations.restore(path=path, restore_method=restore_method,
                                         configuration_type=configuration_type,
                                         vrf_management_name=vrf_management_name)
        logger.info('Restore completed')

    def orchestration_save(self, context, mode, custom_params):
        """

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :param mode: mode
        :param custom_params: json with custom save parameters
        :return str response: response json
        """

        if not mode:
            mode = 'shallow'

        logger = get_logger_with_thread_id(context)
        api = get_api(context)

        resource_config = create_networking_resource_from_context(shell_name=self.SHELL_NAME,
                                                                  supported_os=self.SUPPORTED_OS,
                                                                  context=context)

        cli_handler = CliHandler(self._cli, resource_config, logger, api)
        configuration_operations = ConfigurationRunner(cli_handler=cli_handler,
                                                       logger=logger,
                                                       resource_config=resource_config,
                                                       api=api)

        logger.info('Orchestration save started')
        response = configuration_operations.orchestration_save(mode=mode, custom_params=custom_params)
        logger.info('Orchestration save completed')
        return response

    def orchestration_restore(self, context, saved_artifact_info, custom_params):
        """

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :param saved_artifact_info: OrchestrationSavedArtifactInfo json
        :param custom_params: json with custom restore parameters
        """

        logger = get_logger_with_thread_id(context)
        api = get_api(context)

        resource_config = create_networking_resource_from_context(shell_name=self.SHELL_NAME,
                                                                  supported_os=self.SUPPORTED_OS,
                                                                  context=context)

        cli_handler = CliHandler(self._cli, resource_config, logger, api)
        configuration_operations = ConfigurationRunner(cli_handler=cli_handler,
                                                       logger=logger,
                                                       resource_config=resource_config,
                                                       api=api)

        logger.info('Orchestration restore started')
        configuration_operations.orchestration_restore(saved_artifact_info=saved_artifact_info,
                                                       custom_params=custom_params)
        logger.info('Orchestration restore completed')

    @GlobalLock.lock
    def load_firmware(self, context, path, vrf_management_name):
        """Upload and updates firmware on the resource

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :param path: full path to firmware file, i.e. tftp://10.10.10.1/firmware.tar
        :param vrf_management_name: VRF management Name
        """

        logger = get_logger_with_thread_id(context)
        api = get_api(context)

        resource_config = create_networking_resource_from_context(shell_name=self.SHELL_NAME,
                                                                  supported_os=self.SUPPORTED_OS,
                                                                  context=context)

        if not vrf_management_name:
            vrf_management_name = resource_config.vrf_management_name

        cli_handler = CliHandler(self._cli, resource_config, logger, api)

        logger.info('Start Load Firmware')
        firmware_operations = FirmwareRunner(cli_handler=cli_handler, logger=logger)
        response = firmware_operations.load_firmware(path=path, vrf_management_name=vrf_management_name)
        logger.info('Finish Load Firmware: {}'.format(response))

    def health_check(self, context):
        """Performs device health check

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :return: Success or Error message
        :rtype: str
        """

        logger = get_logger_with_thread_id(context)
        api = get_api(context)

        resource_config = create_networking_resource_from_context(shell_name=self.SHELL_NAME,
                                                                  supported_os=self.SUPPORTED_OS,
                                                                  context=context)
        cli_handler = CliHandler(self._cli, resource_config, logger, api)

        state_operations = StateRunner(logger=logger, api=api, resource_config=resource_config, cli_handler=cli_handler)
        return state_operations.health_check()

    def cleanup(self):
        pass

    def shutdown(self, context):
        """ Shutdown device

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :return:
        """

        logger = get_logger_with_thread_id(context)
        api = get_api(context)

        resource_config = create_networking_resource_from_context(shell_name=self.SHELL_NAME,
                                                                  supported_os=self.SUPPORTED_OS,
                                                                  context=context)

        cli_handler = CliHandler(self._cli, resource_config, logger, api)
        state_operations = StateRunner(logger=logger, api=api, resource_config=resource_config, cli_handler=cli_handler)

        return state_operations.shutdown()
