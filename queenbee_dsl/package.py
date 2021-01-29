import importlib
import pkgutil
import pathlib
from pkg_resources import get_distribution
from email import message_from_string

from setuptools.command.develop import develop
from setuptools.command.install import install
from typing import Dict, List, Union

from queenbee.plugin.plugin import Plugin, PluginConfig, MetaData
from queenbee.recipe.recipe import Recipe, BakedRecipe, Dependency, DependencyKind
from queenbee.repository.package import PackageVersion
from queenbee.repository.index import RepositoryIndex
from queenbee.config import Config, RepositoryReference

from .function import Function


def _init_repo() -> pathlib.Path:
    """Initiate a local Queenbee repository.

    This function is used by package function to start a local Queenbee repository
    if it doesn't exist. If the repository has already been created it will return
    the path to the repository.
    """

    path = pathlib.Path.home()/'.queenbee'/'queenbee-dsl'
    path.mkdir(exist_ok=True)
    index_file = path/'index.json'
    if index_file.exists():
        return path

    plugins_folder = path/'plugins'
    recipes_folder = path/'recipes'
    plugins_folder.mkdir(exist_ok=True)
    recipes_folder.mkdir(exist_ok=True)
    index = RepositoryIndex.from_folder(path.as_posix())

    index.to_json(index_file.as_posix(), indent=2)
    return path


class PackageQBInstall(install):
    """A class to extend `pip install` run method.

    By adding this class to setup.py this package will be added to queenbee-dsl local
    repository which makes it accessible to other queenbee packages as a dependency.

    See here for an example: https://github.com/pollination/honeybee-radiance-pollination/blob/0b5590f691427f256beb77b37bd43f545106eaf1/setup.py#L3-L14
    """

    def run(self):
        install.run(self)
        # add queenbee package to queenbee-dsl repository
        package_name = self.config_vars['dist_name']
        package(package_name)


class PackageQBDevelop(develop):
    """A class to extend `pip install -e` run method.

    By adding this class to setup.py this package will be added to queenbee-dsl local
    repository which makes it accessible to other queenbee packages as a dependency.

    See here for an example: https://github.com/pollination/honeybee-radiance-pollination/blob/0b5590f691427f256beb77b37bd43f545106eaf1/setup.py#L3-L14
    """

    def run(self):
        develop.run(self)
        package_name = self.config_vars['dist_name']
        package(package_name)


def _get_package_readme(package_name: str) -> str:
    try:
        info = get_distribution(package_name).get_metadata('PKG-INFO')
    except FileNotFoundError:
        info = get_distribution(package_name).get_metadata('METADATA')

    package_data = dict(message_from_string(info))
    lines = package_data.get('Description').split('\n')
    lines = [line[8:] if line[:8] == '        ' else line for line in lines]
    return ''.join(lines)


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
    keywords = package_data.get('Keyword')
    if keywords:
        keywords = [key.strip() for key in keywords.split(',')]
    return keywords


def _get_package_maintainers(package_data: Dict) -> List[Dict]:
    info = []
    maintainer = package_data.get('Maintainer')
    maintainer_email = package_data.get('Maintainer-email')
    author = package_data.get('Author')
    author_email = package_data.get('Author-email')

    if author:
        authors = [m.strip() for m in author.split(',')]
        if author_email:
            emails = [m.strip() for m in author_email.split(',')]
            for name, email in zip(authors, emails):
                info.append({'name': name, 'email': email})
        else:
            for name in authors:
                info.append({'name': name, 'email': None})

    if maintainer:
        maintainers = [m.strip() for m in maintainer.split(',')]
        if maintainer_email:
            emails = [m.strip() for m in maintainer_email.split(',')]
            for name, email in zip(maintainers, emails):
                info.append({'name': name, 'email': email})
        else:
            for name in maintainers:
                info.append({'name': name, 'email': None})
    return info


def _get_package_data(package_name: str) -> Dict:
    try:
        info = get_distribution(package_name).get_metadata('PKG-INFO')
    except FileNotFoundError:
        info = get_distribution(package_name).get_metadata('METADATA')

    package_data = dict(message_from_string(info))

    data = {
        'name': package_data.get('Name'),
        'description': package_data.get('Summary'),
        'home': package_data.get('Home-page'),
        'tag': package_data.get('Version'),
        'keywords': _get_package_keywords(package_data),
        'maintainers': _get_package_maintainers(package_data),
        'license': _get_package_license(package_data)
    }

    return data


def _get_meta_data(module, package_type: str) -> MetaData:
    qb_info = module.__queenbee__
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


def _load_plugin(module) -> Plugin:
    """Load Queenbee plugin from Python package.

    Usually you should not be using this function directly. Use ``load`` function
    instead.

    args:
        module: Python module object for a Queenbee Plugin module.

    returns:
        Plugin - A Queenbee plugin
    """
    qb_info = module.__queenbee__
    package_name = module.__name__
    # get metadata
    config = PluginConfig.parse_obj(qb_info['config'])
    metadata = _get_meta_data(module, 'plugin')

    folder = pathlib.Path(module.__file__).parent

    functions = []
    for (_, name, _) in pkgutil.iter_modules([folder]):
        module = importlib.import_module('.' + name, package_name)
        for attr in dir(module):
            loaded_attr = getattr(module, attr)
            if hasattr(loaded_attr, '__decorator__') and \
                    getattr(loaded_attr, '__decorator__') == 'function':
                if loaded_attr is Function:
                    continue
                functions.append(loaded_attr().queenbee)

    plugin = Plugin(config=config, metadata=metadata, functions=functions)
    return plugin


def _load_recipe(module, baked: bool = False) -> Union[BakedRecipe, Recipe]:
    # load entry-point DAG
    """Load Queenbee plugin from Python package.

    Usually you should not be using this function directly. Use ``load`` function
    instead.

    args:
        module: Python module object for a Queenbee Recipe.

    returns:
        Recipe - A Queenbee recipe. It will be a baked recipe if baked is set to True.
    """
    qb_info = module.__queenbee__
    package_name = module.__name__

    main_dag = qb_info.get('entry_point', None)()
    assert main_dag, f'{package_name} __queenbee__ info is missing the enetry_point key.'

    # get metadata
    metadata = dict(qb_info)
    metadata = _get_meta_data(module, 'recipe')

    _dependencies = main_dag._dependencies
    # create a queenbee Recipe object

    # load dags
    qb_dag = main_dag.queenbee
    qb_dag.name = 'main'
    dags = [qb_dag] + [dag.queenbee for dag in _dependencies['dag']]

    # add dependencies
    repo = _init_repo()
    plugins = [
        Dependency(
            kind=DependencyKind.plugin, name=plugin['name'], tag=plugin['tag'],
            source=repo.as_uri()
        ) for plugin in _dependencies['plugin']
    ]
    recipes = [
        Dependency(
            kind=DependencyKind.recipe, name=recipe['name'], tag=recipe['tag'],
            source=repo.as_uri()
        ) for recipe in _dependencies['recipe']
    ]

    recipe = Recipe(metadata=metadata, dependencies=plugins + recipes, flow=dags)

    if baked:
        rf = RepositoryReference(name='queenbee-dsl', path='file:///' + repo.as_posix())
        config = Config(repositories=[rf])
        recipe = BakedRecipe.from_recipe(recipe=recipe, config=config)

    return recipe


def load(package_name: str, baked: bool = False) -> Union[Plugin, BakedRecipe, Recipe]:
    """Load Queenbee Plugin or Recipe from Python package.

        package_name: Python package name (e.g. honeybee-radiance-pollination)
        baked: A boolean value to indicate wether to return a Recipe or a BakedRecipe.
    """
    package_name = package_name.replace('-', '_')
    try:
        module = importlib.import_module(package_name)
    except ModuleNotFoundError:
        raise ValueError(
            f'No module named \'{package_name}\'. Did you forget to install the module?'
            '\nYou can use `pip install` command to install the package from a local '
            'repository or from PyPI.'
        )
    assert hasattr(module, '__queenbee__'), \
        'Failed to find __queenbee__ info in __init__.py'
    qb_info = getattr(module, '__queenbee__')
    if 'config' in qb_info:
        # it's a plugin
        return _load_plugin(module)
    else:
        # it's a recipe
        return _load_recipe(module, baked)


def package(package_name: str, readme: str = None) -> None:
    """Package a plugin or a recipe and add it to Queenbee local repository.

        Args:
            package_name: Python package name (e.g. honeybee-radiance-pollination)
            readme: Readme contents as a string.
    """
    # init a Queenbee package
    repository_path = _init_repo()
    index_path = repository_path/'index.json'
    qb_obj = load(package_name, baked=False)

    if isinstance(qb_obj, Recipe):
        qb_type = 'recipe'
    elif isinstance(qb_obj, Plugin):
        qb_type = 'plugin'
    else:
        raise TypeError('Input package must be a Queenbee Plugin or a Queenbee Recipe.')

    # add to queenbee-dsl repository
    try:
        plugin_version, file_object = PackageVersion.package_resource(
            qb_obj, readme=_get_package_readme(package_name)
        )
    except Exception as error:
        raise ValueError(f'Failed to package {package_name} {qb_type}\n {error}')

    file_path = repository_path/f'{qb_type}s'/plugin_version.url
    file_object.seek(0)
    file_path.write_bytes(file_object.read())

    # re-index the repository
    repo_index = RepositoryIndex.from_folder(repository_path)
    repo_index.to_json(index_path.as_posix(), indent=2)


def translate(
        package_name: str,
        target_folder: str,
        baked: bool = False,
        readme: str = None
        ) -> str:
    """Translate Python package to a Queenbee plugin or recipe.

    BakedRecipes are written to a single file.

    args:
        package_name: Python package name. The package must be installed
            in the environment that this command being executed.
        target_folder: Path to folder to write this plugin.
        baked: A boolean to write the Recipes as BackedRecipes. It will be ignored for
            plugins.
        readme: Readme contents as a string.

    returns:
        str -- path to the generated folder or file.
    """
    qb_object = load(package_name, baked=baked)
    if baked and isinstance(qb_object, BakedRecipe):
        recipe_file = pathlib.Path(target_folder, package_name + '.yaml')
        recipe_file.write_text(qb_object.yaml())
        return recipe_file.as_posix()
    else:
        qb_object.to_folder(
            folder_path=target_folder,
            readme_string=_get_package_readme(package_name)
        )
        return target_folder
