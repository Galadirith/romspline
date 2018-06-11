from setuptools import setup, find_packages

setup(
    name='romspline',
    version='0.0.1',
    url='https://github.com/Galadirith/romspline.git',
    author='Chad Galley',
    author_email='crgalley@tapir.caltech.edu',
    description=(
        'Easy to use Python code for compressing and interpolating 1d data'),
    packages=find_packages(),
    install_requires=[
        'h5py',
        'matplotlib',
        'numpy',
        'scipy'],
    extras_require={
        ':python_version == "2.7"': ['futures']}
)
