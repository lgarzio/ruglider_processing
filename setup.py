from setuptools import setup, find_packages
from ruglider_processing import __version__

setup(
    name='ruglider_processing',
    version=__version__,
    packages=find_packages(),
    url='https://github.com/lgarzio/ruglider_processing',
    author='Lori Garzio',
    author_email='lgarzio@marine.rutgers.edu',
    description='Python tools to process raw glider data to NetCDF.'
)
