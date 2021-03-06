import json
import time
from multiprocessing import get_logger
from cloudshell.core.logger import qs_logger
from azure.mgmt.network import NetworkManagementClient
from cloudshell.api.cloudshell_api import CloudShellAPISession, InputNameValue
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.shell.core.driver_context import InitCommandContext, ResourceCommandContext, AutoLoadResource, \
    AutoLoadAttribute, AutoLoadDetails, CancellationContext
# from data_model import *  # run 'shellfoundry generate' to generate data model classes
from msrestazure.azure_active_directory import ServicePrincipalCredentials
from retrying_qslogger.retrying_qslogger import retry
import cloudshell_cli_handler
import qs_cs_config_parser as parse_config

COREVSRXFILENAME = 'linux_server'


class CentosDriver (ResourceDriverInterface):

    def __init__(self):
        """
        ctor must be without arguments, it is created with reflection at run time
        """
        pass

    def initialize(self, context):
        """
        Initialize the driver session, this function is called everytime a new instance of the driver is created
        This is a good place to load and cache the driver configuration, initiate sessions etc.
        :param InitCommandContext context: the context the command runs on
        """
        pass

    def cleanup(self):
        """
        Destroy the driver session, this function is called everytime a driver instance is destroyed
        This is a good place to close any open sessions, finish writing to log files
        """
        pass

    # <editor-fold desc="Discovery">

    def get_inventory(self, context):
        """
        Discovers the resource structure and attributes.
        :param AutoLoadCommandContext context: the context the command runs on
        :return Attribute and sub-resource information for the Shell resource you can return an AutoLoadDetails object
        :rtype: AutoLoadDetails
        """
        # See below some example code demonstrating how to return the resource structure and attributes
        # run 'shellfoundry generate' in order to create classes that represent your data model
        '''
        resource = Centos.create_from_context(context)
        resource.vendor = 'Vendor'
        resource.model = 'Model'
        return resource.create_autoload_details()
        '''
        return AutoLoadDetails([], [])

    # </editor-fold>

    # <editor-fold desc="Orchestration Save and Restore Standard">
    def orchestration_save(self, context, cancellation_context, mode, custom_params):
        """
        Saves the Shell state and returns a description of the saved artifacts and information
        This command is intended for API use only by sandbox orchestration scripts to implement
        a save and restore workflow
        :param ResourceCommandContext context: the context object containing resource and reservation info
        :param CancellationContext cancellation_context: Object to signal a request for cancellation. Must be enabled in drivermetadata.xml as well
        :param str mode: Snapshot save mode, can be one of two values 'shallow' (default) or 'deep'
        :param str custom_params: Set of custom parameters for the save operation
        :return: SavedResults serialized as JSON
        :rtype: OrchestrationSaveResult
        """

        # See below an example implementation, here we use jsonpickle for serialization,
        # to use this sample, you'll need to add jsonpickle to your requirements.txt file
        # The JSON schema is defined at:
        # https://github.com/QualiSystems/sandbox_orchestration_standard/blob/master/save%20%26%20restore/saved_artifact_info.schema.json
        # You can find more information and examples examples in the spec document at
        # https://github.com/QualiSystems/sandbox_orchestration_standard/blob/master/save%20%26%20restore/save%20%26%20restore%20standard.md
        '''
        # By convention, all dates should be UTC
        created_date = datetime.datetime.utcnow()

        # This can be any unique identifier which can later be used to retrieve the artifact
        # such as filepath etc.

        # By convention, all dates should be UTC
        created_date = datetime.datetime.utcnow()

        # This can be any unique identifier which can later be used to retrieve the artifact
        # such as filepath etc.
        identifier = created_date.strftime('%y_%m_%d %H_%M_%S_%f')

        orchestration_saved_artifact = OrchestrationSavedArtifact('REPLACE_WITH_ARTIFACT_TYPE', identifier)

        saved_artifacts_info = OrchestrationSavedArtifactInfo(
            resource_name="some_resource",
            created_date=created_date,
            restore_rules=OrchestrationRestoreRules(requires_same_resource=True),
            saved_artifact=orchestration_saved_artifact)

        return OrchestrationSaveResult(saved_artifacts_info)
        '''
        pass

    def orchestration_restore(self, context, cancellation_context, saved_artifact_info, custom_params):
        """
        Restores a saved artifact previously saved by this Shell driver using the orchestration_save function
        :param ResourceCommandContext context: The context object for the command with resource and reservation info
        :param CancellationContext cancellation_context: Object to signal a request for cancellation. Must be enabled in drivermetadata.xml as well
        :param str saved_artifact_info: A JSON string representing the state to restore including saved artifacts and info
        :param str custom_params: Set of custom parameters for the restore operation
        :return: None
        """
        '''
        # The saved_details JSON will be defined according to the JSON Schema and is the same object returned via the
        # orchestration save function.
        # Example input:
        # {
        #     "saved_artifact": {
        #      "artifact_type": "REPLACE_WITH_ARTIFACT_TYPE",
        #      "identifier": "16_08_09 11_21_35_657000"
        #     },
        #     "resource_name": "some_resource",
        #     "restore_rules": {
        #      "requires_same_resource": true
        #     },
        #     "created_date": "2016-08-09T11:21:35.657000"
        #    }

        # The example code below just parses and prints the saved artifact identifier
        saved_details_object = json.loads(saved_details)
        return saved_details_object[u'saved_artifact'][u'identifier']
        '''
        pass

    def _get_logger_with_reservation_id(self, context):
        self.logger = qs_logger._create_logger(
            log_group=context.reservation.reservation_id,
            log_category='centos_server',
            log_file_prefix='centos'
        )

    @retry(stop_max_attempt_number=1)
    def _get_network_client(self, client_id, client_secret, tenant, subscription):
        credentials = ServicePrincipalCredentials(client_id=client_id,
                                                  secret=client_secret,
                                                  tenant=tenant)
        return NetworkManagementClient(credentials, subscription)

    def send_command(self, context, command):
        self._get_logger_with_reservation_id(context)
        outp = self._send_command(context, command)
        return outp

    @retry(stop_max_attempt_number=1)
    def _send_command(self, context, command):
        """
        :param ResourceCommandContext context:
        :return:
        """
        session = CloudShellAPISession(host=context.connectivity.server_address,
                                       token_id=context.connectivity.admin_auth_token,
                                       domain=context.reservation.domain)
        username = context.resource.attributes.get('{Model}.User'.format(Model=context.resource.model))
        password_enc = context.resource.attributes.get('{Model}.Password'.format(Model=context.resource.model))
        password = session.DecryptPassword(password_enc).Value
        my_session = cloudshell_cli_handler.CreateSession(
            host=context.resource.address,
            username=username,
            password=password,
            logger=self.logger
        )
        if not isinstance(command, list):
            commands = [command]
        else:
            commands = command
        outp = my_session.send_terminal_command(commands, password=password)
        self.logger.info(outp)
        return outp

    def run_parsed_config(self, context):
        self._get_logger_with_reservation_id(context)
        session = CloudShellAPISession(host=context.connectivity.server_address,
                                       token_id=context.connectivity.admin_auth_token,
                                       domain=context.reservation.domain)
        Reservation_Description = session.GetReservationDetails(context.reservation.reservation_id).ReservationDescription
        parser = parse_config.parse_commands(session, res_id=context.reservation.reservation_id, logger=self.logger)
        parsed_commands = parser.replace_placeholders(file_name=COREVSRXFILENAME,
                                                      file_type='txt',
                                                      reservation_description=Reservation_Description)
        # for command in parsed_commands:
        #     self._send_command(context, command=command)
        result = []
        try:
            temp_result = self._send_command(context=context, command=parsed_commands)
        except Exception as e:
            self.logger.error(e)
            temp_result = e
        result.append(temp_result)

        return result
        #
        # self._send_command(context, parsed_commands)

    # </editor-fold>
