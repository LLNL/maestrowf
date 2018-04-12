# Maestro Workflow Conductor Documentation

[maestrowf.rtfd.io](http://maestrowf.readthedocs.io/en/latest/)

This documentation is built with Sphinx for ReadTheDocs.
The contents are automatically generated from the doc strings found in the code.

## Building the Documentation

To build the documentation locally simply use:

``` shell
make html
```

## Updating the Documentation

If the structure of the modules changes, then the documentation will have to be re-generated.
This can be done easily with:

``` shell
sphinx-apidoc -f -M -H 'Maestro Workflow Conductor' -o ./source/ ../../maestrowf
```
