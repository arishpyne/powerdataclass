from setuptools import setup, find_packages

from VERSION import __VERSION__

from os import path

package_name = 'powerdataclass'
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name=package_name,
    version=__VERSION__,
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    url=f'http://pypi.org/simple/{package_name}',
    install_requires=['setuptools',
                      'toposort'
                      ],
    python_requires='>=3.7',
    license='MIT',
    author='Arish Pyne',
    author_email='arishpyne@gmail.com',
    description='Power Dataclass: dataclasses with auto typecasting and other power features',
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Typing :: Typed',
    ]
)
