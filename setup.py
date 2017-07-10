from setuptools import setup, find_packages

setup(name='MaestroWF',
      decription='A tool and library for specifying and conducting general '
      'workflows.',
      version='1.0.0',
      author='Francesco Di Natale',
      author_email='dinatale3@llnl.gov',
      url='https://github.com/llnl/maestrowf',
      packages=find_packages(),
      entry_points={
        'console_scripts': [
            'maestro = maestrowf.launcher:main',
            'conductor = maestrowf.manager:main',
        ]
      },
      install_requires=[
        'PyYAML',
        'six',
        'enum34',
        ],
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        ],
      )
