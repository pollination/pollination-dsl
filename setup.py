import setuptools

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

with open('README.md') as fh:
    long_description = fh.read()

setuptools.setup(
    name="queenbee-dsl",
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    author="Pollination",
    author_email="info@ladybug.tools",
    description="A Python DSL for Queenbee workflow language.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pollination/queenbee-python-dsl",
    packages=setuptools.find_packages(exclude=["tests"]),
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points='''
        [queenbee.plugins]
        dsl=queenbee_dsl.cli:dsl
    ''',
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Operating System :: OS Independent"
    ],
)
