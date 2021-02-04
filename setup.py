import setuptools

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

with open('README.md') as fh:
    long_description = fh.read()

setuptools.setup(
    name="pollination-dsl",
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    author="Pollination",
    author_email="info@pollination.cloud",
    description="A Python DSL to create Pollination recipes and plugins.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pollination/pollination-dsl",
    packages=setuptools.find_packages(exclude=["tests/*", "docs/*"]),
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={"console_scripts": ["pollination = pollination_dsl.cli:main"]},
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Operating System :: OS Independent"
    ],
)
