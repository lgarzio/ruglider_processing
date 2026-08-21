#!/usr/bin/env python

"""
Author: lgarzio on 5/14/2025
Last modified: lgarzio on 8/21/2026
Convert binary DBD/EBD or SBD/TBD files from 
Slocum gliders to raw netCDF files using pyglider.
"""

import os
import argparse
import sys
import shutil
import pyglider.slocum as slocum
import ruglider_processing.common as cf
from ruglider_processing.loggers import logfile_basename, setup_logger, logfile_deploymentname


def main(args):
# def main(deployments, mode, loglevel, test):
    loglevel = args.loglevel.upper()
    mode = args.mode
    test = args.test
    loglevel = loglevel.upper()

    # logFile_base = os.path.join(os.path.expanduser('~'), 'glider_proc_log')  # for debugging
    logFile_base = logfile_basename()
    logging_base = setup_logger('logging_base', loglevel, logFile_base)

    data_home, deployments_root = cf.find_glider_deployments_rootdir(logging_base, test)

    # Find the cache file directory
    cacdir = os.path.join(data_home, 'cac')
    if not os.path.isdir(cacdir):
        logging_base.error(f'cache file directory not found: {cacdir}')
    
    if isinstance(deployments_root, str):

        for deployment in args.deployments:
        # for deployment in [deployments]:

            # find the deployment data filepaths
            rawncdir, __, deployment_location = cf.find_glider_deployment_datapath(logging_base, deployment, deployments_root, mode)

            binarydir = os.path.join(deployment_location, 'data', 'in', 'binary', 'queue')
            outdir = os.path.join(deployment_location, 'data', 'in', 'rawnc', 'queue')

            if not os.path.isdir(binarydir):
                logging_base.error(f'{deployment} binary file data directory not found')
                continue
            
            if not os.path.isdir(rawncdir):
                logging_base.error(f'{deployment} raw NetCDF output file data directory not found')
                continue

            if not os.path.isdir(outdir):
                logging_base.error(f'{deployment} raw NetCDF output file data directory not found')
                continue

            if not os.path.isdir(os.path.join(deployment_location, 'proc-logs')):
                logging_base.error(f'{deployment} deployment proc-logs directory not found')
                continue

            logfilename = logfile_deploymentname(deployment, mode, 'proc_binary_to_rawnc')
            logFile = os.path.join(deployment_location, 'proc-logs', logfilename)
            logging = setup_logger('logging', loglevel, logFile)

            # Set the deployment configuration path
            deployment_config_root = os.path.join(deployment_location, 'config', 'proc')
            if not os.path.isdir(deployment_config_root):
                logging.warning(f'Invalid deployment config root: {deployment_config_root}')

            # Find metadata files
            deploymentyaml = os.path.join(deployment_config_root, 'deployment.yml')
            if not os.path.isfile(deploymentyaml):
                logging.warning(f'Invalid deployment.yaml file: {deploymentyaml}')
            
            # Find sensor list for processing binary files
            sensorlist = os.path.join(deployment_config_root, 'sensors.txt')
            if not os.path.isfile(sensorlist):
                logging.warning(f'Invalid sensors.txt file: {sensorlist}')
            
            if mode == 'rt':
                scisuffix = 'tbd'
                glidersuffix = 'sbd'
            elif mode == 'delayed':
                scisuffix = 'ebd'
                glidersuffix = 'dbd'
            else:
                logging.warning(f'Invalid mode provided: {mode}')
                continue
            
            logging.info(f'Processing: {deployment} {mode}')

            # convert binary *.T/EBD and *.S/DBD into *.t/ebd.nc and *.s/dbd.nc netcdf files.
            logging.info(f'Converting binary *.{scisuffix} and *.{glidersuffix} into *.{scisuffix}.nc and *.{glidersuffix}.nc netcdf files')
            logging.info(f'Binary filepath: {binarydir}')
            logging.info(f'Output filepath: {outdir}')

            # log the number of binary files to be converted
            scicount = len([f for f in os.listdir(binarydir) if f.endswith(f'.{scisuffix}')])
            if scicount == 0:
                scisuffix = scisuffix.upper()
                scicount = len([f for f in os.listdir(binarydir) if f.endswith(f'.{scisuffix}')])
            flightcount = len([f for f in os.listdir(binarydir) if f.endswith(f'.{glidersuffix}')])
            if flightcount == 0:
                glidersuffix = glidersuffix.upper()
                flightcount = len([f for f in os.listdir(binarydir) if f.endswith(f'.{glidersuffix}')])

            slocum.binary_to_rawnc(binarydir, outdir, cacdir, sensorlist, deploymentyaml, incremental=True, scisuffix=scisuffix, glidersuffix=glidersuffix)

            # Files are written to ./data/in/rawnc/queue for the next step in processing
            # Copy those files to rawncdir
            for f in os.listdir(outdir):
                if f.endswith(f'.{scisuffix}.nc') or f.endswith(f'.{glidersuffix}.nc'):
                    shutil.copy(os.path.join(outdir, f), os.path.join(rawncdir, f))

            # log how many files were successfully converted from binary to *.nc
            oscicount = len([f for f in os.listdir(outdir) if f.endswith(f'.{scisuffix}.nc')])
            if oscicount == 0:
                scisuffix = scisuffix.lower()
                oscicount = len([f for f in os.listdir(outdir) if f.endswith(f'.{scisuffix}.nc')])
            oflightcount = len([f for f in os.listdir(outdir) if f.endswith(f'.{glidersuffix}.nc')])
            if oflightcount == 0:
                glidersuffix = glidersuffix.lower()
                oflightcount = len([f for f in os.listdir(outdir) if f.endswith(f'.{glidersuffix}.nc')])
            logging.info(f'Successfully converted {oscicount} of {scicount} science binary files with suffix *.{scisuffix}')
            logging.info(f'Successfully converted {oflightcount} of {flightcount} engineering binary files with suffix *.{glidersuffix}')

            # Check the file names in ./data/in/rawnc/queue
            # If there aren't a pair of files (sbd/tbd or dbd/ebd) check the files in rawncdir 
            # and copy them to ./data/in/rawnc/queue for the next step in processing.
            # This is necessary for the rt data processing because the binary files are processed as 
            # they are received from the glider and there may be a delay in receiving the other file type.
            if mode == 'rt':
                for f in os.listdir(outdir):
                    seg = f.split('.')[0]
                    # look for this segment in rawncdir
                    rawncmatch = [
                        filename for filename in os.listdir(rawncdir)
                        if seg in filename and filename.endswith('.nc')
                    ]
                    queued_files = set(os.listdir(outdir))
                    for rnm in rawncmatch:
                        if rnm not in queued_files:
                            shutil.copy(os.path.join(rawncdir, rnm), os.path.join(outdir, rnm))
                
            # once all binary files have been processed, remove the files from ./data/in/binary/queue
            for f in os.listdir(binarydir):
                if f.endswith(f'.{scisuffix}') or f.endswith(f'.{glidersuffix}'):
                    os.remove(os.path.join(binarydir, f))

            logging.info(f'Finished converting binary files to raw netcdf files')


if __name__ == '__main__':
    # deploy = 'ru39-20250423T1535'  #  ru44-20250306T0038 ru44-20250325T0438 ru39-20250423T1535
    # mode = 'delayed'  # delayed rt
    # ll = 'info'
    # test = True
    # main(deploy, mode, ll, test)
    arg_parser = argparse.ArgumentParser(description=main.__doc__,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    arg_parser.add_argument('deployments',
                            nargs='+',
                            help='Glider deployment name(s) formatted as glider-YYYYmmddTHHMM')
    
    arg_parser.add_argument('-m', '--mode',
                            help='Dataset mode: real-time (rt) or delayed-mode (delayed)',
                            choices=['rt', 'delayed'],
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
