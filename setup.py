import os

import setuptools

with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'VERSION.txt')) as version_file:
    BUILD_VERSION = version_file.read().strip()

# Loading dependencies from requirements.txt
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

with open("README.md", "r", encoding="utf8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="genalog",
    install_requires=requirements,
    version=BUILD_VERSION,
    author="Jianjie Liu & Amit Gupte",
    author_email="ta_maidap_fy20_h2@microsoft.com",
    description="Tools for generating analog document (images) from raw text",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/microsoft/genalog',
    packages=setuptools.find_packages(exclude=['tests', 'tests.*']),
    package_data={'': [
        'genalog/generation/templates/*.jinja'
    ]},
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
