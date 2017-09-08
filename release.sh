#!/bin/bash
git commit -am "Released version $1"
git tag -m "Released version $1" $1
git push origin $1

python setup.py sdist bdist_wheel

twine upload dist/*
