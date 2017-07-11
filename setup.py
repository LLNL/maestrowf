from setuptools import setup, find_packages

setup(name='maestrowf',
      decription='A tool and library for specifying and conducting general '
      'workflows.',
      version='1.0.0',
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
