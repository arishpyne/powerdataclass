#!/usr/bin/env bash
set -ex
echo -e "\e[32mBuilding PyPI package...\e[0m"
python setup.py sdist bdist_wheel
echo -e "\e[32mUploading PyPI package...\e[0m"
twine upload -u $PYPI_LOGIN -p ${PYPI_PASSWORD} ./dist/*