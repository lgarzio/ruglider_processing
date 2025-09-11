#!/usr/bin/env python

import os
import re
import pandas as pd
import pytz
from netCDF4 import num2date
import numpy as np
from dateutil import parser
from netCDF4 import default_fillvals
import xarray as xr


def convert_epoch_ts(data):
    if isinstance(data, xr.core.dataarray.DataArray):
        time = pd.to_datetime(num2date(data.values, data.units, only_use_cftime_datetimes=False))
    elif isinstance(data, pd.core.indexes.base.Index):
        time = pd.to_datetime(num2date(data, 'seconds since 1970-01-01T00:00:00Z', only_use_cftime_datetimes=False))
    elif isinstance(data, pd.core.indexes.datetimes.DatetimeIndex):
        time = pd.to_datetime(num2date(data, 'seconds since 1970-01-01T00:00:00Z', only_use_cftime_datetimes=False))

    return time


def find_glider_deployment_datapath(logger, deployment, deployments_root, mode):
    """
    Find the glider deployment binary data path
    :param logger: logger object
    :param deployment: glider deployment/trajectory name e.g. ru44-20250306T0038
    :param deployments_root: root directory for glider deployments
    :return: data_path, deployment_location
    """
    glider_regex = re.compile(r'^(.*)-(\d{8}T\d{4})')
    match = glider_regex.search(deployment)
    if match:
        try:
            (glider, trajectory) = match.groups()
            try:
                trajectory_dt = parser.parse(trajectory).replace(tzinfo=pytz.UTC)
            except ValueError as e:
                logger.error('Error parsing trajectory date {:s}: {:}'.format(trajectory, e))
                trajectory_dt = None
                data_path = None
                deployment_location = None

            if trajectory_dt:
                trajectory = '{:s}-{:s}'.format(glider, trajectory_dt.strftime('%Y%m%dT%H%M'))
                deployment_name = os.path.join('{:0.0f}'.format(trajectory_dt.year), trajectory)

                # Create fully-qualified path to the deployment location
                deployment_location = os.path.join(deployments_root, deployment_name)
                if mode == 'delayed':
                    modemap = 'debd'
                elif mode == 'rt':
                    modemap = 'stbd'
                else:
                    logger.warning('{:s} invalid mode provided: {:s}'.format(trajectory, mode))
                if os.path.isdir(deployment_location):
                    # Set the deployment binary data path
                    data_path = os.path.join(deployment_location, 'data', 'in', 'binary', modemap)
                    
                    # Set the deployment raw netcdf data path
                    nc_outpath = os.path.join(deployment_location, 'data', 'in', 'rawnc', modemap)

                    # Set the deployment output file directory
                    outdir = os.path.join(deployment_location, 'data', 'out', mode, 'qc_queue')
                    
                    if not os.path.isdir(data_path):
                        logger.warning(f'{trajectory} data directory not found: {data_path}')
                        data_path = None
                        nc_outpath = None
                        deployment_location = None
                        outdir = None
                    if not os.path.isdir(nc_outpath):
                        logger.warning(f'{trajectory} data directory not found: {nc_outpath}')
                        data_path = None
                        nc_outpath = None
                        deployment_location = None
                        outdir = None
                else:
                    logger.warning(f'Deployment location does not exist: {deployment_location}')
                    data_path = None
                    nc_outpath = None
                    deployment_location = None
                    outdir = None

        except ValueError as e:
            logger.error(f'Error parsing invalid deployment name {deployment}: {e}')
            data_path = None
            nc_outpath = None
            deployment_location = None
            outdir = None
    else:
        logger.error(f'Cannot pull glider name from {deployment}')
        data_path = None
        nc_outpath = None
        deployment_location = None
        outdir = None

    return data_path, nc_outpath, outdir, deployment_location


def find_glider_deployments_rootdir(logger, test):
    # Find the glider deployments root directory
    if test:
        envvar = 'GLIDER_DATA_HOME_TEST'
    else:
        envvar = 'GLIDER_DATA_HOME'

    data_home = os.getenv(envvar)

    if not data_home:
        logger.error('{:s} not set'.format(envvar))
        return 1, 1
    elif not os.path.isdir(data_home):
        logger.error('Invalid {:s}: {:s}'.format(envvar, data_home))
        return 1, 1

    deployments_root = os.path.join(data_home, 'deployments')
    if not os.path.isdir(deployments_root):
        logger.warning('Invalid deployments root: {:s}'.format(deployments_root))
        return 1, 1

    return data_home, deployments_root


def return_season(ts):
    if ts.month in [12, 1, 2]:
        season = 'DJF'
    elif ts.month in [3, 4, 5]:
        season = 'MAM'
    elif ts.month in [6, 7, 8]:
        season = 'JJA'
    elif ts.month in [9, 10, 11]:
        season = 'SON'

    return season


def set_encoding(data_array, original_encoding=None):
    """
    Define encoding for a data array, using the original encoding from another variable (if applicable)
    :param data_array: data array to which encoding is added
    :param original_encoding: optional encoding dictionary from the parent variable
    (e.g. use the encoding from "depth" for the new depth_interpolated variable)
    """
    if original_encoding:
        data_array.encoding = original_encoding

    try:
        encoding_dtype = data_array.encoding['dtype']
    except KeyError:
        data_array.encoding['dtype'] = data_array.dtype

    try:
        encoding_fillvalue = data_array.encoding['_FillValue']
    except KeyError:
        # set the fill value using netCDF4.default_fillvals
        data_type = f'{data_array.dtype.kind}{data_array.dtype.itemsize}'
        data_array.encoding['_FillValue'] = default_fillvals[data_type]
