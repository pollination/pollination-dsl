# queenbee-python-dsl
A Python Domain Specific Language (DSL) to create Queenbee Plugins and Recipes as Python
objects.

![image](https://user-images.githubusercontent.com/2915573/103444096-5a7b3880-4c33-11eb-98a3-09df1ab6c76e.png)

# API docs
[Queenbee-DSL API docs](https://pollination.github.io/queenbee-python-dsl/docs/queenbee_dsl.html#subpackages)

# Installation
1. Clone this repository.
2. Change directory to root folder of the repository.
3. `pip install .`

# Quick Start

If you are interested to start writing your own plugins and recipe see the
[introduction post](https://github.com/pollination/queenbee-python-dsl/wiki/Introduction).

## Function

```python
from dataclasses import dataclass
from queenbee_dsl.function import Function, command, Inputs, Outputs


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

The Queenbee class is accessible from `queenbee` property.
Try `print(CreateOctreeWithSky().queenbee.yaml())` and you should see the full Queenbee
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
another.

## Plugin

To create a Queenbee plugin use the functions to create a standard Python module. The only
change is that you need to provide the information for Queenbee plugin in the `__init__.py`
file as dictionary assigned to `__queenbee__` variable.

In the near future we might be able to use Python package's information to collect most
of these information.

Follow the standard way to install a Python package. Once the package is installed you
can use `queenbee-dsl` to load the package or write it to a folder.

```python
from queenbee_dsl.package import load, write

# name of the queenbee package
python_package = 'pollination_honeybee_radiance'

# load this package as Queenbee Plugin
plugin = load(python_package)

# or write the package as a Queenbee plugin to a folder directly
write(python_package, './pollination-honeybee-radiance')

```

See [`pollination-honeybee-radiance` plugin](https://github.com/pollination/pollination-honeybee-radiance) for a full project example.

## Recipe

`Recipe` is a collection of `DAG`s. Each `DAG` is a collection of interrelated `task`s.
You can use queenbee-dsl to create complex recipes with minimum code by reusing the `functions`
as templates for each task.

Packaging a plugin is exactly the same as packaging a plugin.

```python
from queenbee_dsl.package import load, write

# name of the queenbee package
python_package = 'daylight-factor'

# load this package as Queenbee Recipe
recipe = load(python_package, baked=True)

# or write the package as a Queenbee plugin to a folder directly
write(python_package, './daylight-factor')

```

See [`daylight factor` recipe](https://github.com/pollination/ladybug-tools-recipes/tree/master/recipes/daylight-factor) for a full project example.
