#!/usr/bin/env python

"""
Author: lgarzio on 9/21/2026
Last modified: lgarzio on 9/21/2026
Check realtime merged netCDF file names to determine if they need to be re-merged
"""

import os
import argparse
import sys
import glob
import shutil
import ruglider_processing.common as cf
from ruglider_processing.loggers import logfile_basename, setup_logger, logfile_deploymentname

    
def main(args):
    loglevel = args.loglevel.upper()
    mode = args.mode
    test = args.test
    loglevel = loglevel.upper()

    logFile_base = logfile_basename()
    logging_base = setup_logger('logging_base', loglevel, logFile_base)

    data_home, deployments_root = cf.find_glider_deployments_rootdir(logging_base, test)
    
    if isinstance(deployments_root, str):

        for deployment in args.deployments:

            # find the deployment binary data filepath
            rawncdir, outdir, deployment_location = cf.find_glider_deployment_datapath(logging_base, deployment, deployments_root, mode)
            outdir = os.path.dirname(outdir)
            raw_queuedir = os.path.join(deployment_location, 'data', 'in', 'rawnc', 'queue')

            if not os.path.isdir(raw_queuedir):
                logging_base.error(f'{deployment} queue directory containing raw NetCDF files not found')
                continue
            
            if not os.path.isdir(outdir):
                logging_base.error(f'{deployment} output file data directory not found')
                continue

            if not os.path.isdir(os.path.join(deployment_location, 'proc-logs')):
                logging_base.error(f'{deployment} deployment proc-logs directory not found')
                continue

            logfilename = logfile_deploymentname(deployment, mode, 'rt_file_management')
            logFile = os.path.join(deployment_location, 'proc-logs', logfilename)
            logging = setup_logger('logging', loglevel, logFile)
                
            logging.info(f'Checking {deployment} {mode} to determine if files need to be re-merged')
            
            # Find files that only have the flight suffix
            files = glob.glob(os.path.join(outdir, '*_sbd.nc'))

            # Figure out of the corresponding science files exist for each flight file
            file_pairs = 0
            for f in files:
                segment = os.path.basename(f).split('_')[0]
                flight_file = f'{segment}.tbd.nc'
                raw_flight_file = os.path.join(rawncdir, flight_file)
                if os.path.isfile(raw_flight_file):
                    # If the corresponding science file exists, copy both files to the queue directory to
                    # be re-merged
                    science_file = f'{segment}.sbd.nc'
                    raw_science_file = os.path.join(rawncdir, science_file)
                    logging.info(f'Copying {flight_file} and {science_file} to queue for re-merging')
                    shutil.copy(raw_flight_file, os.path.join(raw_queuedir, flight_file))
                    shutil.copy(raw_science_file, os.path.join(raw_queuedir, science_file))
                    file_pairs += 1

             # log how many files were successfully merged
            logging.info(f'Copied {file_pairs} file pairs to the {raw_queuedir} for re-merging')


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=main.__doc__,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    arg_parser.add_argument('deployments',
                            nargs='+',
                            help='Glider deployment name(s) formatted as glider-YYYYmmddTHHMM')
    
    arg_parser.add_argument('-m', '--mode',
                            help='Dataset mode: real-time (rt) only',
                            choices=['rt'],
                            default='rt')
    
    arg_parser.add_argument('-l', '--loglevel',
                            help='Verbosity level',
                            type=str,
                            choices=['debug', 'info', 'warning', 'error'],
                            default='info')
    
    arg_parser.add_argument('-test', '--test',
                            help='Point to the environment variable key GLIDER_DATA_HOME_TEST for testing.',
                            action='store_true')
    
    parsed_args = arg_parser.parse_args()
    
    sys.exit(main(parsed_args))
