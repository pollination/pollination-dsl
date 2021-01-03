import setuptools

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name="queenbee-dsl",
    author="Pollination",
    author_email="info@ladybug.tools",
    description="A Python DSL for Queenbee workflow language.",
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
