from io import open
from typing import List

from setuptools import setup

import arq_admin


def get_readme() -> str:
    """read the contents of the README file"""
    with open('README.md', encoding='utf-8') as f:
        return f.read()


def get_requirements() -> List[str]:
    """read the contents of the requirements file"""
    with open('requirements.txt', encoding='utf-8') as f:
        return [line.replace('==', '>=') for line in f.readlines()]


setup(
    name='arq-django-admin',
    version=arq_admin.__version__,
    setup_requires=['better-setuptools-git-version'],
    install_requires=get_requirements(),
    tests_require=[],
    packages=['arq_admin'],
    package_data={'arq_admin': ['py.typed']},
    include_package_data=True,
    author='Slava Skvortsov',
    description='An app that provides Django admin for ARQ',
    long_description=get_readme(),
    long_description_content_type='text/markdown',
    url='https://github.com/SlavaSkvortsov/arq-django-admin',
    zip_safe=True,
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Monitoring',
    ],
)
