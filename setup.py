from os import path
from maestrowf import __version__
from setuptools import setup, find_packages

setup(name='maestrowf',
      description='A tool and library for specifying and conducting general '
      'workflows.',
      version='1.1.4',
      author='Francesco Di Natale',
      author_email='dinatale3@llnl.gov',
      url='https://github.com/llnl/maestrowf',
      license='MIT License',
      packages=find_packages(),
      entry_points={
        'console_scripts': [
                'maestro = maestrowf.maestro:main',
                'conductor = maestrowf.conductor:main',
        ]
      },
      install_requires=[
        'PyYAML>=4.2b1',
        'six',
        "filelock",
        "tabulate",
        ],
      extras_require={
        ":python_version<'3.4'": ['enum34'],
      },
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Operating System :: Unix',
        'Operating System :: MacOS :: MacOS X',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering',
        'Topic :: System :: Distributed Computing',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    package_data={
        'maestrowf': [
            'maestrowf/specification/schemas/yamlspecification.json'
        ],
    },
    include_package_data=True,
)
