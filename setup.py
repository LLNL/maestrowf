from maestrowf import __version__
from setuptools import setup, find_packages

setup(name='maestrowf',
      description='A tool and library for specifying and conducting general '
      'workflows.',
      version=__version__,
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
        "enum34 ; python_version<'3.4'"
        ],
      extras_require={},
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        ],
      )
