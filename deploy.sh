#!/bin/sh

echo "PyPi Deployment..."
echo "Building distribution"
python -m build
echo "Pushing new version to PyPi"
twine upload dist/* -u $PYPI_USERNAME -p $PYPI_PASSWORD
