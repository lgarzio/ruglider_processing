#!/usr/bin/env python

"""
Author: lgarzio on 9/11/2025
Last modified: lgarzio on 9/19/2025
Generate the deployment.yml file for a glider deployment
Right now, just adds all of the sensors listed in sensors.txt
to the deployment.yml file using sensor information from
sensor_defs-raw.json and sensor_defs-sci_profile.json
"""

import os
import argparse
import sys
import yaml
import json
import ruglider_processing.common as cf
from ruglider_processing.loggers import logfile_basename, setup_logger, logfile_deploymentname


def is_sensor_listed_as_source(sensor, template_data):
    # Check if the sensor is listed as a source in netcdf_variables
    netcdf_variables = template_data.get('netcdf_variables', {})
    for var, attributes in netcdf_variables.items():
        if attributes.get('source') == sensor:
            return True
    return False


#def main(args):
def main(deployments, loglevel, test):
    status = 0

    # loglevel = args.loglevel.upper()
    # test = args.test
    loglevel = loglevel.upper()

    logFile_base = os.path.join(os.path.expanduser('~'), 'glider_proc_log')  # for debugging
    # logFile_base = logfile_basename()
    logging_base = setup_logger('logging_base', loglevel, logFile_base)

    data_home, deployments_root = cf.find_glider_deployments_rootdir(logging_base, test)
    
    if isinstance(deployments_root, str):

        #for deployment in args.deployments:
        for deployment in [deployments]:

            # find the deployment binary data filepath
            deployment_location = cf.find_glider_deployment_location(logging_base, deployment, deployments_root)

            if not os.path.isdir(os.path.join(deployment_location, 'proc-logs')):
                logging_base.error(f'{deployment} deployment proc-logs directory not found')
                continue

            logfilename = logfile_deploymentname(deployment, 'configure', 'deploymentyaml')
            logFile = os.path.join(deployment_location, 'proc-logs', logfilename)
            logging = setup_logger('logging', loglevel, logFile)

            # Set the deployment configuration path
            deployment_config_root = os.path.join(deployment_location, 'config', 'proc')
            if not os.path.isdir(deployment_config_root):
                logging.warning(f'Invalid deployment config root: {deployment_config_root}')

            # Read in the deployment-template.yml file
            templatefile = os.path.join(deployment_config_root, 'deployment-template.yml')
            if os.path.isfile(templatefile):
                with open(templatefile, 'r') as file:
                    try:
                        template_data = yaml.safe_load(file)  # Parse the YAML file
                    except yaml.YAMLError as e:
                        logging.error(f"Error reading YAML file {templatefile}: {e}")
                        continue
            else:
                logging.error(f"Template file not found: {templatefile}")
                continue

            # Read in the deployment specific global attributes from deployment_globalattrs.yml
            # and update the template_data['metadata'] dictionary
            globalattrsfile = os.path.join(deployment_config_root, 'deployment_globalattrs.yml')
            if os.path.isfile(globalattrsfile):
                with open(globalattrsfile, 'r') as file:
                    try:
                        deployment_global_attrs = yaml.safe_load(file)  # Parse the YAML file
                        if 'metadata' in template_data.keys():
                            template_data['metadata'].update(deployment_global_attrs)
                        else:
                            template_data['metadata'] = deployment_global_attrs
                    except yaml.YAMLError as e:
                        logging.error(f"Error reading YAML file {globalattrsfile}: {e}")
                        continue
            else:
                logging.error(f"deployment_globalattrs.yml file not found: {globalattrsfile}")
                continue

            # Read in the platform metadata from platform.yml
            template_data['platform'] = dict()
            platformfile = os.path.join(deployment_config_root, 'platform.yml')
            if os.path.isfile(platformfile):
                with open(platformfile, 'r') as file:
                    try:
                        platform_metadata = yaml.safe_load(file)  # Parse the YAML file
                        if 'platform' in template_data.keys():
                            template_data['platform'].update(platform_metadata['platform'])
                        else:
                            template_data['platform'] = platform_metadata['platform']
                    except yaml.YAMLError as e:
                        logging.error(f"Error reading YAML file {platformfile}: {e}")
                        continue
            else:
                logging.error(f"platform.yml file not found: {platformfile}")
                continue

            # add the platform WMO ID and deployment ID to the global attributes
            template_data['metadata']['wmo_id'] = platform_metadata['platform']['wmo_id']
            template_data['metadata']['wmo_platform_code'] = platform_metadata['platform']['wmo_platform_code']
            template_data['metadata']['deployment'] = deployment

            # find and open instruments.json
            instrumentsfile = os.path.join(deployment_config_root, 'instruments.json')
            if os.path.isfile(instrumentsfile):
                with open(instrumentsfile, 'r') as file:
                    instruments = json.load(file)
            else:
                logging.error(f"instruments.json file not found: {instrumentsfile}")
                continue

            # add all of the instruments from instruments.json to template_data['instruments']
            template_data['instruments'] = dict()
            for instrument in instruments:
                template_data['instruments'][instrument['nc_var_name']] = instrument['attrs']

            # combine both sensor_defs.json files
            sdraw = os.path.join(deployment_config_root, 'sensor_defs-raw.json')
            sdprofile = os.path.join(deployment_config_root, 'sensor_defs-sci_profile.json')
            with open(sdraw, 'r') as file:
                sdraw_data = json.load(file)
            with open(sdprofile, 'r') as file:
                sdprofile_data = json.load(file)
            combined_data = sdraw_data.copy()
            combined_data.update(sdprofile_data)
            
            # find and open sensors.txt
            sensorsfile = os.path.join(deployment_config_root, 'sensors-test.txt')
            if os.path.isfile(sensorsfile):
                with open(sensorsfile, 'r') as file:
                    sensors = file.readlines()  # Read all lines into a list
                    sensors = [sensor.strip() for sensor in sensors]  # Strip whitespace characters like `\n` at the end of each line
            else:
                logging.error(f"sensors.txt file not found: {sensorsfile}")
                continue

            # add all of the variables from sensors.txt to template_data['netcdf_variables']
            for sensor in sensors:
                print(sensor)

                # Check if the sensor is listed as a source in netcdf_variables
                check = is_sensor_listed_as_source(sensor, template_data)
                if check:
                    continue  # it's already in deployment.yml so skip this variable
                else:
                    # find the variable information in sensor_defs and add to the deployment.yml file
                    try:
                        sensor_info = combined_data[sensor]
                        keyname = sensor_info['nc_var_name']
                        template_data['netcdf_variables'][keyname] = {}
                        template_data['netcdf_variables'][keyname]['source'] = sensor
                        for key, value in sensor_info['attrs'].items():
                            if key in ['axis', 'units', 'long_name', 'standard_name', 'valid_min', 'valid_max', 'fill_value']:
                                template_data['netcdf_variables'][keyname][key] = value
                    except KeyError:
                        template_data['netcdf_variables'][sensor] = {}
                        template_data['netcdf_variables'][sensor]['source'] = sensor
                        logging.warning(f'No information found for {sensor} in sensor_defs-raw.json or sensor_defs-sci_profile.json')
            
            # Write the final deployment.yml file
            deploymentyaml = os.path.join(deployment_config_root, 'deployment.yml')
            with open(deploymentyaml, 'w') as outfile:
                try:
                    yaml.dump(template_data, outfile, default_flow_style=False)
                    logging.info(f'Successfully wrote deployment.yml file: {deploymentyaml}')
                except yaml.YAMLError as e:
                    logging.error(f"Error writing YAML file {deploymentyaml}: {e}")
            
        return status


if __name__ == '__main__':
    deploy = 'ru44-20250325T0438'  #  ru44-20250306T0038 ru44-20250325T0438 ru39-20250423T1535
    ll = 'info'
    test = True
    main(deploy, ll, test)
    # arg_parser = argparse.ArgumentParser(description=main.__doc__,
    #                                      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    #
    # arg_parser.add_argument('deployments',
    #                         nargs='+',
    #                         help='Glider deployment name(s) formatted as glider-YYYYmmddTHHMM')
    #
    # arg_parser.add_argument('-l', '--loglevel',
    #                         help='Verbosity level',
    #                         type=str,
    #                         choices=['debug', 'info', 'warning', 'error', 'critical'],
    #                         default='info')
    #
    # arg_parser.add_argument('-test', '--test',
    #                         help='Point to the environment variable key GLIDER_DATA_HOME_TEST for testing.',
    #                         action='store_true')
    #
    # parsed_args = arg_parser.parse_args()
    #
    # sys.exit(main(parsed_args))
