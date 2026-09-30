#!/usr/bin/env python

"""
Author: lgarzio on 9/21/2026
Last modified: lgarzio on 9/30/2026
Check realtime merged netCDF file names to determine if there are duplicates.
This can happen when a just a flight file is processed then a science file is transferred later
and the pair is re-processed.  This script will check for duplicate files and remove the older file.
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
            
            if not os.path.isdir(outdir):
                logging_base.error(f'{deployment} output file data directory not found')
                continue

            if not os.path.isdir(os.path.join(deployment_location, 'proc-logs')):
                logging_base.error(f'{deployment} deployment proc-logs directory not found')
                continue

            logfilename = logfile_deploymentname(deployment, mode, 'rt_file_management')
            logFile = os.path.join(deployment_location, 'proc-logs', logfilename)
            logging = setup_logger('logging', loglevel, logFile)
                
            logging.info(f'Checking {deployment} {mode} for duplicate trajectory files in {outdir}')
            
            # Find files that only have the flight suffix
            files = sorted(glob.glob(os.path.join(outdir, '*_sbd.nc')))

            # Figure out if there is a corresponding *_stbd.nc file, meaning the tbd file was
            # transferred from the glider after the sbd file was processed.  If so, delete the older
            # sbd file that doesn't contain the science data. The newer stbd file should contain the science data.
            files_removed = 0
            for f in files:
                stbd_file = f.replace('_sbd.nc', '_stbd.nc')
                if os.path.isfile(stbd_file):
                    # If the corresponding stbd.nc file exists, delete the older sbd.nc file
                    fname = os.path.basename(f)
                    logging.info(f'Deleting {fname} and keeping associated *stbd.nc file')
                    os.remove(f)
                    files_removed += 1

             # log how many files were deleted
            logging.info(f'Deleted {files_removed} *_sbd.nc files')


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
