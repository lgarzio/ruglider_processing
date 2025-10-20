# ruglider_processing

## Installation

`git clone https://github.com/lgarzio/ruglider_processing.git`

Also clone my forked version of pyglider
`git clone https://github.com/lgarzio/pyglider.git`

Navigate to the cloned repo on your local machine
`cd ruglider_processing`

Create the environment
`conda env create -f environment.yml`

Activate the environment
`conda activate ruglider_processing`

Install the local package in your environment
`pip install .`

Navigate to the forked version of pyglider
`cd pyglider`

Install the forked version of pyglider in the environment in editable mode (if you want to make edits)
`pip install -e .`

### Directory structure in glider deployment directory

```bash
├── config
│   ├── qc
│   └── proc
├── data
│   └── in 
│       └── binary
│           └── debd
│           └── stbd
│       └── rawnc
│           └── debd
│           └── stbd
│   └── out
│       └── delayed
│           └── qc_queue
│       └── rt
│           └── qc_queue
└── proc-logs
```

### Usage

1. The following template [config files](https://github.com/lgarzio/ruglider_processing/tree/master/example_config_files) don't need modification but need to be in ../config/proc/
    
    a. deployment-template.yml

    b. sensor_defs-raw.json
    
    c. sensor_defs-sci_profile.json

2. Generate the following [files](https://github.com/lgarzio/ruglider_processing/tree/master/example_config_files) based on the instruments that are installed on the glider
    
    a. instruments.json (using build_deployment_instrument_configurations.py not included in this package)

    b. sensors.txt

3. Manually modify the [config files](https://github.com/lgarzio/ruglider_processing/tree/master/example_config_files) for the deployment and put them in ../config/proc/
    
    a. deployment-globalattrs.yml
    
    b. platform.yml

4. Once all of the config files are in ../config/proc/, run [generate_deploymentyaml.py](https://github.com/lgarzio/ruglider_processing/blob/master/generate_deploymentyaml.py) to create the deployment.yml file that is used to convert the raw glider data files to merged trajectory NetCDF files.

    `python generate_deploymentyaml.py glider-YYYYmmddTHHMM`

5. Run [convert_binary_to_raw_nc.py](https://github.com/lgarzio/ruglider_processing/blob/master/convert_binary_to_raw_nc.py) to convert realtime (-m rt) sbd/tbd binary files located in ../data/in/binary/stbd/ or delayed (-m delayed) dbd/ebd binary files located in ../data/in/binary/debd/ to raw NetCDF files (../data/in/rawnc/) using [pyglider](https://pyglider.readthedocs.io/en/latest/pyglider/pyglider.html). This will generate a log file in ../proc-logs/.

    `python convert_binary_to_raw_nc.py glider-YYYYmmddTHHMM -m delayed`

6. Run [merge_raw_nc_to_timeseries.py](https://github.com/lgarzio/ruglider_processing/blob/master/merge_raw_nc_to_timeseries.py) to convert the raw dbd/ebd or sbd/tbd NetCDF file pairs to merged timeseries NetCDF files using a modified version of [pyglider](https://pyglider.readthedocs.io/en/latest/pyglider/pyglider.html). This generates one file per glider segment, calculates basic science variables like depth, salinity, density, indexes glider profiles, and will generate a log file in ../proc-logs/.

    `python merge_raw_nc_to_timeseries.py glider-YYYYmmddTHHMM -m delayed`
