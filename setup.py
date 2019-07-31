from setuptools import setup, find_packages
from VERSION import __VERSION__

package_name = 'powerdataclass'


setup(
    name=package_name,
    version=__VERSION__,
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    url=f'http://pypi.org/simple/{package_name}',
    install_requires=['setuptools',
                      'toposort'
                      ],
    python_requires=">=3.7",
    license='MIT',
    author='Arish Pyne',
    author_email='arishpyne@gmail.com',
    description='Power Dataclass: dataclasses with auto typecasting and other power features',
)
