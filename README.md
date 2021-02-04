# pollination-dsl
A Python Domain Specific Language (DSL) to create Pollination Plugins and Recipes.

Pollination uses [Queenbee](https://github.com/pollination/queenbee) as its workflow
language. Pollination-dsl makes it easy to create Queenbee object without the need to
learn Queenbee.

![pollination-dsl](https://user-images.githubusercontent.com/2915573/106669142-36d04880-6579-11eb-9763-a718aec27166.jpg)

# API docs
[Pollination-DSL API docs](https://pollination.github.io/pollination-dsl/docs/pollination_dsl.html#subpackages)

# Requirements
Python >=3.7

# Installation

Using pip:

`pip install pollination-dsl`

For local development:

1. Clone this repository.
2. Change directory to root folder of the repository.
3. `pip install -e .`

# Quick Start

If you are interested to start writing your own plugins and recipe see the
[introduction post](https://github.com/pollination/pollination-dsl/wiki/Introduction).

## Function

```python
from dataclasses import dataclass
from pollination_dsl.function import Function, command, Inputs, Outputs


@dataclass
class CreateOctreeWithSky(Function):
    """Generate an octree from a Radiance folder and sky!"""

    # inputs
    include_aperture = Inputs.str(
        default='include',
        description='A value to indicate if the static aperture should be included in '
        'octree. Valid values are include and exclude. Default is include.',
        spec={'type': 'string', 'enum': ['include', 'exclude']}
    )

    black_out = Inputs.str(
        default='default',
        description='A value to indicate if the black material should be used. Valid '
        'values are default and black. Default value is default.',
        spec={'type': 'string', 'enum': ['black', 'default']}
    )

    model = Inputs.folder(description='Path to Radiance model folder.', path='model')

    sky = Inputs.file(description='Path to sky file.', path='sky.sky')

    @command
    def create_octree(self):
        return 'honeybee-radiance octree from-folder model --output scene.oct ' \
            '--{{self.include_aperture}}-aperture --{{self.black_out}} ' \
            '--add-before sky.sky'

    # outputs
    scene_file = Outputs.file(description='Output octree file.', path='scene.oct')

```

If you want to access the `Queenbee` objects you can use `queenbee` property. For example
try `print(CreateOctreeWithSky().queenbee.yaml())` and you should see the full Queenbee
definition:

```yaml
type: Function
annotations: {}
inputs:
- type: FunctionStringInput
  annotations: {}
  name: black-out
  description: A value to indicate if the black material should be used. Valid values
    are default and black. Default value is default.
  default: default
  alias: []
  required: false
  spec:
    type: string
    enum:
    - black
    - default
- type: FunctionStringInput
  annotations: {}
  name: include-aperture
  description: A value to indicate if the static aperture should be included in octree.
    Valid values are include and exclude. Default is include.
  default: include
  alias: []
  required: false
  spec:
    type: string
    enum:
    - include
    - exclude
- type: FunctionFolderInput
  annotations: {}
  name: model
  description: Path to Radiance model folder.
  default: null
  alias: []
  required: true
  spec: null
  path: model
- type: FunctionFileInput
  annotations: {}
  name: sky
  description: Path to sky file.
  default: null
  alias: []
  required: true
  spec: null
  path: sky.sky
  extensions: null
outputs:
- type: FunctionFileOutput
  annotations: {}
  name: scene-file
  description: Output octree file.
  path: scene.oct
name: create-octree-with-sky
description: Generate an octree from a Radiance folder and sky!
command: honeybee-radiance octree from-folder model --output scene.oct --{{inputs.include-aperture}}-aperture
  --{{inputs.black-out}} --add-before sky.sky
```

Since the functions are standard Python classes you can also subclass them from one
another as long as you use the same name for the `@command` method. Otherwise it will
create an invalid function with two commands.

## Plugin

To create a Pollination plugin use the functions to create a standard Python module.
The only change is that you need to provide the information for Pollination plugin in
the `__init__.py` file as dictionary assigned to `__pollination__` variable.

Follow the standard way to install a Python package. Once the package is installed you
can use `pollination-dsl` to load the package or write it to a folder.

```python
from pollination_dsl.package import load, write

# name of the pollination package
python_package = 'pollination_honeybee_radiance'

# load this package as Pollination Plugin
plugin = load(python_package)

# or write the package as a Pollination plugin to a folder directly
write(python_package, './pollination-honeybee-radiance')

```

See [`pollination-honeybee-radiance` plugin](https://github.com/pollination/pollination-honeybee-radiance) for a full project example.

## Recipe

`Recipe` is a collection of `DAG`s. Each `DAG` is a collection of interrelated `task`s.
You can use pollination-dsl to create complex recipes with minimum code by reusing the
`functions` as templates for each task.

Packaging a plugin is exactly the same as packaging a plugin.

```python
from pollination_dsl.package import load, translate

# name of the pollination package
python_package = 'daylight-factor'

# load this package as Pollination Recipe
recipe = load(python_package, baked=True)

# or translate and write the package as a Pollination plugin to a folder directly
translate(python_package, './daylight-factor')

```

See [`daylight factor` recipe](https://github.com/pollination/ladybug-tools-recipes/tree/master/recipes/daylight-factor) for a full project example.


# How to create a pollination-dsl package

Pollination-dsl uses Python's standard packaging to package pollination plugins and recipes.
It parses most of the data from inputs in `setup.py` file and some Pollination specific
information from `__init__.py` file. Below is an example of how these file should look
like.

By taking advantage of [Python's native namespace packaging](https://packaging.python.org/guides/packaging-namespace-packages/#native-namespace-packages)
we keep all the packages under the `pollination` namespace.

## setup.py

```python

#!/usr/bin/env python
import setuptools

# These two class extends setup.py to install the packages as pollination packages
from pollination_dsl.package import PostInstall, PostDevelop

# Read me will be mapped to readme strings
with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    cmdclass={'develop': PostDevelop, 'install': PostInstall},    # required - include this for pollination packaging
    name='pollination-honeybee-radiance',                                   # required - will be used for package name
    packages=setuptools.find_namespace_packages(include=['pollination.*']), # required - that's how pollination find the package
    author='ladybug-tools',                                                 # required - author must match the owner account name on Pollination
    version='0.1.0',                                                        # required - will be used as package tag. you can also use semantic versioning
    zip_safe=False,                                                         # required - set to False to ensure the packaging will always work
    url='https://github.com/pollination/pollination-honeybee-radiance',     # optional - will be translated to home
    description='Honeybee Radiance plugin for Pollination.',                # optional - will be used as package description
    long_description=long_description,                                      # optional - will be translated to ReadMe content on Pollination
    long_description_content_type="text/markdown",
    maintainer='maintainer_1, maintainer_2',                                # optional - will be translated to maintainers. For multiple maintainers
    maintainer_email='maintainer_1@example.come, maintainer_2@example.com', # use comma inside the string.
    keywords='honeybee, radiance, ladybug-tools, daylight',                 # optional - will be used as keywords
    license='PolyForm Shield License 1.0.0, https://polyformproject.org/wp-content/uploads/2020/06/PolyForm-Shield-1.0.0.txt',  # optional - the license link should be separated by a comma
)

```

## __init__.py

Here is an example `__init__.py` for a plugin.

```python

__pollination__ = {
    'icon': 'https://ladybug.tools/assets/icon.png',  # optional - package icon
    'config': {                   # required for Pollination - docker information for this specific plugin
        'docker': {
            'image': 'ladybugtools/honeybee-radiance:1.28.12',
            'workdir': '/home/ladybugbot/run'
        }
    }
}
```

Here is an example `__init__.py` for a recipe.

```python
from .entry import AnnualDaylightEntryPoint

__pollination__ = {
    'icon': 'https://ladybug.tools/assets/icon.png',  # optional - package icon
    'entry_point': AnnualDaylightEntryPoint,  # required - this will point pollination to the class that should be used to start the run
}

```
