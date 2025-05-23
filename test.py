#!/usr/bin/env python

"""
Author: lgarzio on 5/14/2025
Last modified: lgarzio on 5/20/2025
Testing pyglider
"""

import os
import argparse
import sys
import glob
import numpy as np
import xarray as xr
import pyglider.ncprocess as ncprocess
import pyglider.slocum as slocum
import pyglider.utils as pgutils
import ruglider_processing.common as cf
from ruglider_processing.loggers import logfile_basename, setup_logger, logfile_deploymentname


#def main(args):
def main(deployments, mode, loglevel, test):
    status = 0

    # loglevel = args.loglevel.upper()
    # mode = args.mode
    # test = args.test
    loglevel = loglevel.upper()

    logFile_base = os.path.join(os.path.expanduser('~'), 'glider_proc_log')  # for debugging
    # logFile_base = logfile_basename()
    logging_base = setup_logger('logging_base', loglevel, logFile_base)

    data_home, deployments_root = cf.find_glider_deployments_rootdir(logging_base, test)

    # Find the cache file directory
    cacdir = os.path.join(data_home, 'cac')
    if not os.path.isdir(cacdir):
        logging_base.error(f'cache file directory not found: {cacdir}')
    
    if isinstance(deployments_root, str):

        #for deployment in args.deployments:
        for deployment in [deployments]:

            # find the deployment binary data filepath
            binarydir, rawncdir, outdir, deployment_location = cf.find_glider_deployment_datapath(logging_base, deployment, deployments_root, mode)

            if not binarydir:
                logging_base.error(f'{deployment} binary file data directory not found')
                continue

            if not os.path.isdir(os.path.join(deployment_location, 'proc-logs')):
                logging_base.error(f'{deployment} deployment proc-logs directory not found')
                continue

            logfilename = logfile_deploymentname(deployment, mode)
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
                status = 1
                continue
            
            logging.info(f'Processing: {deployment}')

            # convert binary *.EBD and *.DBD into *.ebd.nc and *.dbd.nc netcdf files.
            #raw_outdir = os.path.join(outdir, 'raw')
            slocum.binary_to_rawnc(binarydir, rawncdir, cacdir, sensorlist, deploymentyaml, incremental=True, scisuffix=scisuffix, glidersuffix=glidersuffix)

            # this combines all dbds into one file, same with ebds - not sure if I like this part
            # slocum.merge_rawnc(raw_outdir, raw_outdir, deploymentyaml, scisuffix=scisuffix, glidersuffix=glidersuffix)

            # make level-1 timeseries netcdf file from the merged raw files
            # ts_dir = os.path.join(outdir, 'timeseries')
            # outname = slocum.raw_to_timeseries(raw_outdir, ts_dir, deploymentyaml, profile_filt_time=100, profile_min_time=300)
            
            # make level-1 timeseries netcdf file from each debd.nc pair - modified by Lori
            files = glob.glob(os.path.join(rawncdir, '*.nc'))
            trajectory_list = []
            for file in files:
                trajectory = os.path.basename(file).split('.')[0]
                if trajectory not in trajectory_list:
                    trajectory_list.append(trajectory)
            
            for traj in sorted(trajectory_list):
                outname = slocum.raw_trajectory_to_timeseries(rawncdir, outdir, deploymentyaml, profile_filt_time=30, 
                                                            profile_min_time=300, trajectory=traj)

            print('done')
            
        return status


if __name__ == '__main__':
    deploy = 'ru44-20250306T0038'
    mode = 'delayed'
    ll = 'info'
    test = True
    main(deploy, mode, ll, test)
    # arg_parser = argparse.ArgumentParser(description=main.__doc__,
    #                                      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    #
    # arg_parser.add_argument('deployments',
    #                         nargs='+',
    #                         help='Glider deployment name(s) formatted as glider-YYYYmmddTHHMM')
    #
    # arg_parser.add_argument('-m', '--mode',
    #                         help='Deployment dataset status',
    #                         choices=['rt', 'delayed'],
    #                         default='rt')
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
