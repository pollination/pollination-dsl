from dataclasses import dataclass
from typing import NamedTuple, Dict, List
from collections import namedtuple
import importlib_metadata
import re
import pkg_resources
import warnings
import subprocess
import sys

from queenbee.plugin.plugin import MetaData


def camel_to_snake(name: str) -> str:
    """Change name from CamelCase to snake-case."""
    return name[0].lower() + \
        ''.join(['-' + x.lower() if x.isupper() else x for x in name][1:])


def name_to_pollination(name: str) -> str:
    """Add a pollination- in front of the name."""
    if name.startswith('pollination.'):
        return name.replace('pollination.', 'pollination-')
    elif name.replace('_', '-').startswith('pollination-'):
        return name
    else:
        return f'pollination-{name}'


def import_module(name: str, pull=True):
    """Import a module by name.

    This function only works for pollination namespace packages.
    If the module is not installed and pull is set to True it will try to pull the
    package from PyPI.

    """
    package_name = name_to_pollination(name).replace('-', '_')
    err_msg = \
        f'Failed to import \'{package_name}\' from local installation. ' \
        'Trying to install from PyPI.'

    # for pollination modules split and try again pollination-honeybee-radiance
    # is namedspaced as pollination.honeybee_radiance
    package_name_segments = package_name.split('_')
    _namespace = package_name_segments[0]
    _name = '_'.join(package_name_segments[1:])
    try:
        namespace = __import__(f'{_namespace}.{_name}')
        module = getattr(namespace, _name)
    except ModuleNotFoundError as e:
        if not str(e).endswith(f"'{_namespace}.{_name}'".replace('-', '_')):
            # it is a module import error but not the one that we are trying to import
            raise ModuleNotFoundError(e)

        if pull:
            print(err_msg)
            success = _try_pull_from_pip(package=package_name)
            if success:
                # try again
                return import_module(package_name, pull=False)
        raise ModuleNotFoundError(
            f'Failed to import \'{package_name}\' locally or from PyPI. '
            f'You can try `pip install {package_name}` manually.\nTo ensure '
            f'{package_name} is installed try to run `pip show {package_name}`'
        )

    return module


def _try_pull_from_pip(package):
    try:
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', package]
        )
        return True
    except subprocess.CalledProcessError:
        # it failed to download from PyPI
        # error message will be printed out by pip
        return False


def get_requirement_version(package_name, dependency_name):
    """Get assigned version to a dependency in package requirements."""
    package_name = package_name.replace('pollination.', 'pollination_')
    package_name = name_to_pollination(package_name)
    dependency_name = dependency_name.replace('_', '-')
    requirements = {}
    try:
        req = pkg_resources.get_distribution(package_name).get_metadata('requires.txt')
    except FileNotFoundError:
        # try to get it from meta data
        package_data = importlib_metadata.metadata(package_name)
        req_dists = package_data.get_all('Requires-Dist') or []
        for package in req_dists:
            name, version = package.split(' (')
            version = \
                version.replace('=', '').replace('>', '').replace('<', '') \
                .replace(')', '').strip()
            requirements[name] = version
    else:
        for package in pkg_resources.parse_requirements(req):
            version = \
                str(package.specifier).replace('=', '').replace('>', '').replace('<', '')
            requirements[package.project_name] = version

    assert dependency_name in requirements, \
        f'{dependency_name} is not a requirement for {package_name}.'

    return requirements[dependency_name]


def get_docker_image_from_dependency(package, dependency, owner, alias=None):
    """Get a docker image id from package information.

    Arguments:
        package: Name of the package (e.g. pollination-honeybee-radiance)
        dependency: Name of the dependency (e.g. honeybee-radiance)
        owner: The account owner for docker image
        alias: An alias name for the docker image. This input is useful in cases that
            docker image name (e.g. ladybug) is different from the dependency name
            (e.g. ladybug-core).

    Returns:
        str -- docker image id (e.g. ladybugtools/honeybee-radiance:0.5.2)
    """
    image_name = alias if alias else dependency
    try:
        image_version = get_requirement_version(package, dependency)
        image_id = f'{owner}/{image_name}:{image_version}'
    except (FileNotFoundError, AssertionError) as error:
        # this should not happen if the package is installed correctly
        # but Python has so many ways to store requirements based on how the package
        # is built and where! It's better to set it to latest instead of failing.
        warnings.warn(
            f'Failed to pinpoint the version for {dependency} as a dependency for'
            f' {package}. Will set the docker version to latest.\n{error}'
        )
        image_id = f'{owner}/{image_name}:latest'

    return image_id


def _get_package_readme(package_name: str) -> str:
    package_name = name_to_pollination(package_name).replace('-', '_')
    package_data = importlib_metadata.metadata(package_name)
    long_description = package_data.get_payload()
    if not long_description.strip():
        content = package_data.get('Description')
        long_description = []
        for line in content.split('\n'):
            long_description.append(re.sub('^        ', '', line))
        long_description = '\n'.join(long_description)
    return long_description


def _get_package_owner(package_name: str) -> str:
    """Author field is used for package owner."""
    package_name = name_to_pollination(package_name).replace('-', '_')
    package_data = importlib_metadata.metadata(package_name)
    owner = package_data.get('Author')
    assert owner, \
        'You must set the author of the package in setup.py to Pollination account owner'
    # ensure there is only one author
    owner = owner.strip()
    assert len(owner.split(',')) == 1, \
        'A Pollination package can only have one author. Use maintainer field for ' \
        'providing multiple maintainers.'

    return owner


def _get_package_license(package_data: Dict) -> Dict:
    # try to get license
    license_info = package_data.get('License')
    if not license_info:
        license, link = None, None
    elif license_info and ',' in license_info:
        license, link = [info.strip() for info in license_info.split(',')]
    else:
        license, link = license_info.strip(), None

    return {'name': license, 'url': link}


def _get_package_keywords(package_data: Dict) -> List:
    keywords = package_data.get('Keywords')
    if keywords:
        keywords = [key.strip() for key in keywords.split(',')]
    return keywords


def _get_package_sources(package_data: Dict) -> str:
    urls = package_data.get_all('Project-URL')
    sources = []
    for url in urls:
        key, value = url.split(',')
        if key == 'icon':
            continue
        sources.append(value.strip())
    return sources


def _get_package_icon(package_data: Dict) -> str:
    urls = package_data.get_all('Project-URL')
    for url in urls:
        key, value = url.split(',')
        if key == 'icon':
            return value.strip()


def _get_package_maintainers(package_data: Dict) -> List[Dict]:
    package_maintainers = []
    maintainer = package_data.get('Maintainer')
    maintainer_email = package_data.get('Maintainer-email')

    if maintainer:
        maintainers = [m.strip() for m in maintainer.split(',')]
        if maintainer_email:
            emails = [m.strip() for m in maintainer_email.split(',')]
            for name, email in zip(maintainers, emails):
                package_maintainers.append({'name': name, 'email': email})
        else:
            for name in maintainers:
                package_maintainers.append({'name': name, 'email': None})
    return package_maintainers


def _clean_version(version: str) -> str:
    """Clean package version."""
    xyz = [v.strip() for v in version.split('.')]

    if len(xyz) == 2:
        return f'{xyz[0]}.{xyz[1]}.0'

    x, y, z = xyz[:3]

    if z == '0':
        return f'{x}.{y}.{z}'

    # clean up the developer version
    try:
        version = f'{x}.{y}.{int(z)}'
    except ValueError:
        # development version like 0.1.dev1+gf910655.d20210207
        version = f'{x}.{y}.0'

    return version


def _get_package_version(package_data: Dict) -> str:
    """Get package version.

    This function returns the non-development version for a development version.
    It removes the .dev part and return x.y.z-1 version if it is a dev version.
    """
    version = package_data.get('Version')
    return _clean_version(version)


def _get_package_data(package_name: str) -> Dict:
    """Get package data as a dictionary."""
    package_name = name_to_pollination(package_name).replace('-', '_')
    package_data = importlib_metadata.metadata(package_name)

    data = {
        'name': package_data.get('Name').replace('pollination-', ''),
        'description': package_data.get('Summary'),
        'home': package_data.get('Home-page'),
        'tag': _get_package_version(package_data),
        'keywords': _get_package_keywords(package_data),
        'maintainers': _get_package_maintainers(package_data),
        'license': _get_package_license(package_data),
        'icon': _get_package_icon(package_data),
        'sources': _get_package_sources(package_data)
    }

    return data


def _get_meta_data(module, package_type: str) -> MetaData:
    """Get package metadata."""
    qb_info = dict(module.__pollination__)
    package_data = _get_package_data(module.__name__)

    if package_type == 'plugin':
        qb_info.pop('config')
    else:
        # recipe
        qb_info.pop('entry_point')

    for k, v in package_data.items():
        if v is None:
            continue
        if k == 'name' and k in qb_info:
            # only use package name if name is not provided
            continue
        qb_info[k] = v

    metadata = MetaData.parse_obj(qb_info)
    return metadata


@dataclass
class _BaseClass:
    """Base class for Pollination dsl Function and DAG.

    Do not use this class directly.
    """
    _cached_queenbee = None
    _cached_outputs = None
    _cached_package = None
    _cached_inputs = None

    @property
    def queenbee(self):
        raise NotImplementedError

    @property
    def _inputs(self) -> NamedTuple:
        """Return inputs as a simple object with dot notation.

        Use this property to access the inputs when creating a DAG.

        The name starts with a _ not to conflict with a possible member of the class
        with the name inputs.
        """
        if self._cached_inputs:
            return self._cached_inputs
        cls_name = camel_to_snake(self.__class__.__name__)
        mapper = {
            inp.name.replace('-', '_'): {
                'name': inp.name.replace('-', '_'),
                'parent': cls_name,
                'value': inp
            } for inp in self.queenbee.inputs
        }

        inputs = namedtuple('Inputs', list(mapper.keys()))
        self._cached_inputs = inputs(*list(mapper.values()))

        return self._cached_inputs

    @property
    def _outputs(self) -> NamedTuple:
        """Return outputs as a simple object with dot notation.

        Use this property to access the outputs when creating a DAG.

        The name starts with a _ not to conflict with a possible member of the class
        with the name outputs.
        """
        if self._cached_outputs:
            return self._cached_outputs
        cls_name = camel_to_snake(self.__class__.__name__)
        mapper = {
            out.name.replace('-', '_'): {
                'name': out.name.replace('-', '_'),
                'parent': cls_name, 'value': out
            } for out in self.queenbee.outputs
        }
        outputs = namedtuple('Outputs', list(mapper.keys()))
        self._cached_outputs = outputs(*list(mapper.values()))

        return self._cached_outputs

    @property
    def _package(self) -> dict:
        """Queenbee package information.

        This information will only be available if the function is part of a Python
        package.
        """
        if self._cached_package:
            return self._cached_package

        module = import_module(self._python_package, pull=True)
        assert hasattr(module, '__pollination__'), \
            'Failed to find __pollination__ info in __init__.py'
        package_data = _get_package_data(module.__name__)
        pollination_data = getattr(module, '__pollination__')
        for k, v in package_data.items():
            pollination_data[k] = v
        self._cached_package = pollination_data
        return self._cached_package

    @property
    def _python_package(self) -> str:
        """Python package information for this function.

        This information will only be available if the function is part of a Python
        package.
        """
        module = self.__module__
        if module.startswith('pollination'):
            return '.'.join(self.__module__.split('.')[:2])
        else:
            return self.__module__.split('.')[0]
