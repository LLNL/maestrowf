## Setting up your Python Environment

### Installing Maestro Locally

If you plan to use Maestro on a system that you personally manage, it is recommended
that you keep a PATH-accessible copy by using [pipx](https://github.com/pipxproject/pipx).
`pipx` is a management utility for installing Python executables in their own
environments. Install `pipx` following their [install instructions](https://github.com/pipxproject/pipx#install-pipx).

Once `pipx` is installed, simply run:

```bash
pipx install maestrowf
```

Maestro should be accessible on the command line, simple test by running

```
maestro -h
```

### Installing Maestro in Python Virtual Environments

To get started, we recommend using virtual environments. If you do not have the
Python `virtualenv` package installed, take a look at their official [documentation](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/) to get started.

To create a new virtual environment:

    python -m virtualenv maestro_venv
    source maestro_venv/bin/activate
    pip install maestrowf

### Getting Started for Contributors

If you plan to develop on Maestro, install the repository directly using:

    pip install poetry
    poetry install

Once set up, test the environment. The paths should point to a virtual environment folder.

    which python
    which pip
