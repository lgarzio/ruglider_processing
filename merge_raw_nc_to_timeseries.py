#!/usr/bin/env python

"""
Author: lgarzio on 5/14/2025
Last modified: lgarzio on 9/19/2025
Convert raw DBD/EBD or SBD/TBD netCDF files from
Slocum gliders to merged timeseries netCDF files using pyglider.
"""

import os
import argparse
import sys
import glob
import yaml
import xarray as xr
import numpy as np
import pyglider.slocum as slocum
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
    
    if isinstance(deployments_root, str):

        #for deployment in args.deployments:
        for deployment in [deployments]:

            # find the deployment binary data filepath
            binarydir, rawncdir, outdir, deployment_location = cf.find_glider_deployment_datapath(logging_base, deployment, deployments_root, mode)

            if not os.path.isdir(rawncdir):
                logging_base.error(f'{deployment} raw NetCDF file data directory not found')
                continue
            
            if not os.path.isdir(outdir):
                logging_base.error(f'{deployment} output file data directory not found')
                continue

            if not os.path.isdir(os.path.join(deployment_location, 'proc-logs')):
                logging_base.error(f'{deployment} deployment proc-logs directory not found')
                continue

            logfilename = logfile_deploymentname(deployment, mode, 'proc_merge_nc_to_timeseries')
            logFile = os.path.join(deployment_location, 'proc-logs', logfilename)
            logging = setup_logger('logging', loglevel, logFile)

            # Set the deployment configuration path
            deployment_config_root = os.path.join(deployment_location, 'config', 'proc')
            if not os.path.isdir(deployment_config_root):
                logging.warning(f'Invalid deployment config root: {deployment_config_root}')

            # Find metadata file
            deploymentyaml = os.path.join(deployment_config_root, 'deployment.yml')
            if os.path.isfile(deploymentyaml):
                with open(deploymentyaml, 'r') as file:
                    try:
                        deployment_meta = yaml.safe_load(file)  # Parse the YAML file
                    except yaml.YAMLError as e:
                        logging.error(f"Error reading YAML file {deploymentyaml}: {e}")
                        continue
            else:
                logging.error(f"deployment.yaml file not found: {deploymentyaml}")
                continue
            
            if mode == 'rt':
                scisuffix = 'tbd'
                glidersuffix = 'sbd'
                profile_filter_time = 30
            elif mode == 'delayed':
                scisuffix = 'ebd'
                glidersuffix = 'dbd'
                profile_filter_time = 30
            else:
                logging.warning(f'Invalid mode provided: {mode}')
                status = 1
                continue
            
            logging.info(f'Processing: {deployment} {mode}')
            
            # make timeseries netcdf file from each debd.nc/stdb.nc pair
            logging.info(f'merging *.{scisuffix}.nc and *.{glidersuffix}.nc netcdf files into timeseries netcdf files')
            logging.info(f'Individual *.{scisuffix}.nc and *.{glidersuffix}.nc filepath: {rawncdir}')
            logging.info(f'Timeseries output filepath: {outdir}')
            
            files = glob.glob(os.path.join(rawncdir, '*.nc'))
            segment_list = []
            for file in files:
                segment = os.path.basename(file).split('.')[0]
                if segment not in segment_list:
                    segment_list.append(segment)
            
            # log the number of .nc files to be merged
            scicount = len([f for f in os.listdir(rawncdir) if f.endswith(f'.{scisuffix}.nc')])
            flightcount = len([f for f in os.listdir(rawncdir) if f.endswith(f'.{glidersuffix}.nc')])
            logging.info(f'Found {scicount} *.{scisuffix}.nc (science) and {flightcount} *.{glidersuffix}.nc (flight) files to merge')

            for seg in sorted(segment_list):
                print(seg)
                ds, savefile = slocum.raw_segment_to_timeseries(rawncdir, outdir, deploymentyaml, logging, profile_filt_time=profile_filter_time,
                                                           profile_min_time=60, segment=seg)
                
                if ds is not None:
                    # add platform metadata variable
                    da = xr.DataArray(np.array(np.nan), name='platform', attrs=deployment_meta['platform'])
                    ds['platform'] = da
                    
                    # add instrument metadata variables
                    for ncvar_name, attributes in deployment_meta.get('instruments', {}).items():
                        da = xr.DataArray(np.array(np.nan), name=ncvar_name, attrs=attributes)
                        ds[ncvar_name] = da
                    
                    # TODO add encoding
                    
                    outname = os.path.join(outdir, savefile)
                    logging.info(f'Writing {outname}')
                    ds.to_netcdf(
                        outname, 'w', encoding={'time': {'units': 'seconds since 1970-01-01T00:00:00Z'}}
                    )
                    
                    # for testing
                    savefile = savefile.replace('.nc', '.csv')
                    outcsv = os.path.join(outdir, savefile)
                    ds.to_dataframe().to_csv(outcsv)

            # log how many files were successfully merged
            outputcount = len([f for f in os.listdir(outdir) if f.endswith('.nc')])
            logging.info(f'Successfully created {outputcount} merged *.nc files (out of {scicount} *.{scisuffix}.nc files and {flightcount} *.{glidersuffix}.nc files)')
            
        return status


if __name__ == '__main__':
    deploy = 'ru39-20250423T1535'  #  ru44-20250306T0038 ru44-20250325T0438 ru39-20250423T1535
    mode = 'rt'  # delayed rt
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
