"""Create a queenbee plugin from a python plugin."""
import pkgutil
import importlib
import pathlib
from queenbee.plugin.plugin import Plugin, PluginConfig, MetaData
from .function import Function


def load(package_name: str) -> Plugin:
    """Load Queenbee plugin from Python package.

    args:
        package_name: Plugin Python package name. The package must be installed
            in the environment that this command being executed.

    returns:
        Plugin - A Queenbeee plugin
    """
    # collect queenbee functions
    module = importlib.import_module(package_name)
    assert hasattr(module, '__queenbee__'), \
        'Failed to find __queenbee__ info in __init__.py'
    qb_info = getattr(module, '__queenbee__')

    # get metadata
    config = PluginConfig.parse_obj(qb_info['config'])
    meta_data = dict(qb_info)
    meta_data.pop('config')
    metadata = MetaData.parse_obj(meta_data)

    folder = pathlib.Path(module.__file__).parent

    functions = []
    for (module_loader, name, ispkg) in pkgutil.iter_modules([folder]):
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


def write_to_folder(package_name: str, target_folder: str, readme: str = None) -> str:
    """Write Queenbee plugin from Python package to a folder.

    args:
        package_name: Plugin Python package name. The package must be installed
            in the environment that this command being executed.
        target_folder: Path to folder to write this plugin.
        readme: Readme contents as a string.

    returns:
        str -- path to plugin folder
    """
    plugin = load(package_name)
    plugin.to_folder(folder_path=target_folder, readme_string=readme)
    return target_folder
