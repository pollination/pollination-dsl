import importlib
import pkgutil
import pathlib
import warnings
from typing import Union

from queenbee.plugin.plugin import Plugin, PluginConfig
from queenbee.recipe.recipe import Recipe, BakedRecipe, Dependency, DependencyKind
from queenbee.repository.package import PackageVersion
from queenbee.repository.index import RepositoryIndex
from queenbee.config import Config, RepositoryReference

from .function import Function
from .common import import_module, _get_meta_data, _get_package_readme, \
    get_requirement_version, name_to_pollination


def _init_repo() -> pathlib.Path:
    """Initiate a local Queenbee repository.

    This function is used by package function to start a local Queenbee repository
    if it doesn't exist. If the repository has already been created it will return
    the path to the repository.
    """
    HOME = pathlib.Path.home().as_posix()
    path = pathlib.Path(HOME, '.queenbee', 'pollination-dsl')
    path.mkdir(parents=True, exist_ok=True)

    index_file = path/'index.json'

    plugins_folder = path/'plugins'
    recipes_folder = path/'recipes'
    plugins_folder.mkdir(exist_ok=True)
    recipes_folder.mkdir(exist_ok=True)

    if not index_file.exists():
        index = RepositoryIndex.from_folder(path.as_posix())
        index.to_json(index_file.as_posix(), indent=2)

    return path


def _load_plugin(module) -> Plugin:
    """Load Queenbee plugin from Python package.

    Usually you should not be using this function directly. Use ``load`` function
    instead.

    args:
        module: Python module object for a Queenbee Plugin module.

    returns:
        Plugin - A Queenbee plugin
    """
    qb_info = module.__pollination__
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


def package_recipe_dependencies(recipe: Recipe) -> None:
    """Try to load/package recipe dependencies from local registry.

    If the dependency is not available in local registry then it will try to package
    it from a local python installation. If that also fails it will try to pull it
    down using pip install.
    """
    print(f'packaging dependencies for {recipe.metadata.name}:{recipe.metadata.tag}')
    for dep in recipe.dependencies:
        package(dep.name)


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
    qb_info = module.__pollination__
    package_name = module.__name__

    main_dag_entry = qb_info.get('entry_point', None)
    assert main_dag_entry, \
        f'{package_name} __pollination__ info is missing the enetry_point key.'

    main_dag = main_dag_entry()

    # get metadata
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
        package_recipe_dependencies(recipe)
        rf = RepositoryReference(
            name='pollination-dsl', path='file:///' + repo.as_posix()
        )
        config = Config(repositories=[rf])
        recipe = BakedRecipe.from_recipe(recipe=recipe, config=config)

    return recipe


def load(package_name: str, baked: bool = False) -> Union[Plugin, BakedRecipe, Recipe]:
    """Load Queenbee Plugin or Recipe from Python package.

        package_name: Python package name (e.g. honeybee-radiance-pollination)
        baked: A boolean value to indicate wether to return a Recipe or a BakedRecipe.
    """
    module = import_module(package_name)

    assert hasattr(module, '__pollination__'), \
        'Failed to find __pollination__ info in __init__.py'
    qb_info = getattr(module, '__pollination__')
    if 'config' in qb_info:
        print(f'loading plugin: {package_name}')
        # it's a plugin
        package = _load_plugin(module)
    elif 'entry_point' in qb_info:
        print(f'loading recipe: {package_name}')
        # it's a recipe
        package = _load_recipe(module, baked)
        # try to update recipe tag based on requirements
        for dep in package.dependencies:
            name = name_to_pollination(dep.name)
            try:
                tag = get_requirement_version(package_name, name)
            except AssertionError:
                warnings.warn(
                    f'{package_name} has dependencies on {name} but it is not set as '
                    'one of the package dependencies in setup.py. Will use the version '
                    f'of the currently installed version: {name}:{dep.tag}'
                )
            else:
                dep.tag = tag
    else:
        raise ValueError(
            f'Error loading {package_name}. Package must be a DSL plugin or a DSL '
            f'recipe.'
        )
    return package


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
        package_recipe_dependencies(qb_obj)
    elif isinstance(qb_obj, Plugin):
        qb_type = 'plugin'
    else:
        raise TypeError('Input package must be a Queenbee Plugin or a Queenbee Recipe.')

    # add to pollination-dsl repository
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
