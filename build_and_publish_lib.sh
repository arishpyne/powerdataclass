#!/usr/bin/env bash
echo -e "\e[32mBuilding PyPI package...\e[0m"
python setup.py sdist bdist_wheel
echo -e "\e[32mUploading PyPI package...\e[0m"
twine upload ./dist/*
#twine upload -u ${TWINE_USERNAME} -p ${TWINE_PASSWORD} -r ${TWINE_REPOSITORY} ./dist/*