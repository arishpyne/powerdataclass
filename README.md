# ⚡ Power Dataclass ⚡

[![Build Status](https://api.travis-ci.org/arishpyne/powerdataclass.svg?branch=master)](https://api.travis-ci.org/arishpyne/powerdataclass.svg?branch=master) [![PyPI version](https://badge.fury.io/py/powerdataclass.svg)](https://pypi.python.org/pypi/powerdataclass/)   [![PyPI pyversions](https://img.shields.io/pypi/pyversions/powerdataclass.svg)](https://pypi.python.org/pypi/powerdataclass/)

## Installation

`pip install powerdataclass`

## Usage

Python 3.7 have introduced a spiritual successor of `NamedTuple`: the `dataclass`.
While being nice, the `dataclass` type hinting is only, well, _hinting_.

This library gives you an ability to create dataclasses with field values automatically cast to
the types defined in the `dataclass`'s type hints:

### Typecasting

```python
from powerdataclass import *


class Coordinates(PowerDataclass):
    x: int
    y: int


c1 = Coordinates(1, 2)
c2 = Coordinates('1', '2')
c3 = Coordinates(**{'x': 1.1, 'y': 2.2})

# >>> c1
Coordinates(x=1, y=2)
# >>> c1 == c2 == c3 
True
 ```  

This also works with every generic type that has a Python primitive type as its origin. This applies to subscriptable
types of any level of nestedness as well:

```python
class Vector(PowerDataclass):
    items: List[int]


v1 = Vector(['1', '2', '3'])
v2 = Vector({1.1, 2.2, 3.3})
v3 = Vector(range(1, 4))

# >>> v1
Vector(items=[1, 2, 3])
# >>> v1 == v2 == v3 
True
```

The typecasting also respects other dataclasses (and Power Dataclasses) declared in type hints.
If you pass a mapping or an iterable in place of actual dataclass instance, Power Dataclass will attempt to unpack it to
a corresponding dataclass:

```python
class Vector(PowerDataclass):
    items: List[int]


class Tensor(PowerDataclass):
    vectors: List[Vector]


t1 = Tensor(**{
    'vectors': [
        {'items': [1, 2, 3]},
        {'items': [4, 5, 6]},
        ([7, 8, 9],),
    ]
}
            )

# >>> t1
Tensor(vectors=[Vector(items=[1, 2, 3]), Vector(items=[4, 5, 6]), Vector(items=[7, 8, 9])])
```

If a value type is defined as a dataclass and that dataclass can be instantiated with a sole argument,
it will be cast as well

```python
class TimestampedIntValue(PowerDataclass):
    value: int
    timestamp: int = time.time()


class SensorReadings(PowerDataclass):
    moon_phase_angle: TimestampedIntValue
    mars_surface_temperature: TimestampedIntValue


readings = SensorReadings(122, -70)

# >>> readings
SensorReadings(moon_phase_angle=TimestampedIntValue(value=122, timestamp=1570898094),
               mars_surface_temperature=TimestampedIntValue(value=-70, timestamp=1570898094)
               )
```

### Custom typecasting

You can modify the behaviour of type casting by registering two types of handlers on your fancy PowerDataclass:

* **type handlers**: a unary method marked as a _type handler_ will be applied to any value that has a matching type
  declared in your dataclass typehints.
* **field handlers**: a unary method marked as a _field handler_ will be applied to a value of a specific PDC field.

Those functions must _always_ return a value.

You can do this by marking your methods with special decorators:

```python
class CoolBool(PowerDataclass):
    string_bool: bool
    negated_bool: bool

    @type_handler(bool)
    def handle_bools(self, v):
        if type(v) is str:
            return v.lower() in ['y', 'yes', '1', 'True']
        else:
            return bool(v)

    @field_handler('negated_bool')
    def handle_negated_bools(self, v):
        return not self.handle_bools(v)


# >>> CoolBool('yes', 'no')
CoolBool(string_bool=True, negated_bool=True)
```   

Field handlers take precedence over the type handlers.
Field handlers and type handlers are scoped to a particular Power Dataclass. Inheritance is respected.

### Field Metadata

The behaviour of fields can be modified by providing corresponding flags in a field's `metadata` dictionary,
provided by base Python `dataclasses`.

#### Nullability

Fields are considered non-nullable by default.
This means that if, during instantiation, the value of a field will be equal to `None`, a `ValueError` exception will
occur.
Type casting will be performed on non-null values, except for non-typecast fields (see below)

If a field has a default value, and it is `None`, it will be considered nullable.
Also, if you want to accept `None` but you either don't want to provide defaults at all, provide a non-null default or
provide a default factory, you can mark your field as nullable by either setting the flag or using a pre-made partial:

```python
class Nihilus(PowerDataclass):
    x: int = field(metadata={FieldMeta.NULLABLE: True})
    y: int = None
    z: list = nullable_field(default_factory=list)


# >>> Nihilus()

# ! TypeError: __init__() missing 1 required positional argument: 'x'

# >>> Nihilus(1)
Nihilus(x=1, y=None, z=[])

# >>> Nihilus('1', '1', (1,))
Nihilus(x=1, y=1, z=[1])

# >>> Nihilus('1', None, None)
Nihilus(x=1, y=1, z=None)
```

#### Skipping typecasting (and null checking)

If you want to disable type checking for a specific field you can mark your field as nullable by either setting the
corresponding flag in the fields' `metadata` dictionary or using a pre-made partial:

```python
class Noncasted(PowerDataclass):
    x: int = field(metadata={FieldMeta.SKIP_TYPECASTING: True})
    y: int = noncasted_field()


# >>> Noncasted('1', 2.2)
Noncasted(x='1', y=2.2)
```

#### Dependent and calculated fields

If some of your field processing requires other fields typecast before you can declare this field dependencies by name
by setting the corresponding value in the fields' `metadata`:

```python
class Dependent(PowerDataclass):
    a: int
    b: int = field(metadata={FieldMeta.DEPENDS_ON_FIELDS: ['a']})
    c: int = field(metadata={FieldMeta.DEPENDS_ON_FIELDS: ['d', 'b']})
    d: int = field(metadata={FieldMeta.DEPENDS_ON_FIELDS: ['a']})
```

Fields will be topologically sorted by their dependencies and type casting will be done in this order. For this example,
the order will be:

1) a
2) b
3) d
4) c

You can use a combination of field handlers and dependent fields to declare calculated fields:

```python  
class CubeSquarer(PowerDataclass):
    n: int
    n_square: int = field(default=None, metadata={FieldMeta.DEPENDS_ON_FIELDS: ['n']})
    n_cube: int = calculated_field(depends_on=['n'])

    @field_handler('n_square')
    def handle_n_square(self, v):
        return self.n ** 2

    @field_handler('n_cube')
    def handle_n_cube(self, v):
        return self.n ** 3


# >>> CubeSquarer(4)
CubeSquarer(n=4, n_square=16, n_cube=256)
```

It is an error to declare a field as `calculatable` without registering a corresponding `field_handler`

## Modification of Power Dataclass behaviour

You can modify the behaviour of Power Dataclass by editing the `Meta` nested class' attributes.
All Power Dataclasses have a default value for this `Meta` nested class equal
to `powerdataclass.PowerDataclassDefaultMeta`
This `Meta` subclass will emulate the behaviour of class variable inheritance, making every attribute of `Meta` default
to `powerdataclass.PowerDataclassDefaultMeta`

Currently, the following values are now supported:

| Name                            | Default value | Description                                                                                                                                                                |
|---------------------------------|---------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **dataclass_init**              | *True*        | passed to the `dataclasses.dataclass` constructor. [See docs](https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass)                                    |
| **dataclass_repr**              | *True*        | passed to the `dataclasses.dataclass` constructor.                                                                                                                         |
| **dataclass_eq**                | *True*        | passed to the `dataclasses.dataclass` constructor.                                                                                                                         |
| **dataclass_order**             | *False*       | passed to the `dataclasses.dataclass` constructor.                                                                                                                         |
| **dataclass_unsafe_hash**       | *False*       | passed to the `dataclasses.dataclass` constructor.                                                                                                                         |
| **dataclass_frozen**            | *False*       | passed to the `dataclasses.dataclass` constructor.                                                                                                                         |
| **singleton**                   | *False*       | If *True* enables the [Singleton Mode](#singleton-mode).                                                                                                                   |
| **json_encoder**                | *None*        | If set, this class will be used as a `cls` param to `json.dumps` in `PowerDataclass().to_json()` [See docs](https://docs.python.org/3/library/json.html#json.JSONEncoder). |
| **json_decoder**                | *None*        | If set, this class will be used as a `cls` param to `json.loads` in `PowerDataclass.from_json()` [See docs](https://docs.python.org/3/library/json.html#json.JSONDecoder). |
| **as_dict_ignored_when_nested** | *False*       | If set to True, this PDC won't be converted when this PDC is nested and wrapping PDC's `.as_dict()` is called. Can be further ignored if `as_dict(force=True)` was called. |

Example of setting the `Meta` of a `PowerDataclass`:

```python
class PowerDataclassWithNewBehaviour(PowerDataclass):
    class Meta:
        dataclass_frozen = True
        singleton = True
```

## Singleton Mode

If you set the `Meta.singleton` value to `True`, your PowerDataclass will turn into
a [Singleton](https://en.wikipedia.org/wiki/Singleton_pattern).

This means that this PowerDataclass can be instantiated only once, and all further attempts to instantiate this PDC will
return that instance instead:

```python
class PDCSingleton(PowerDataclass):
    a: int

    class Meta:
        singleton = True


singleton1 = PDCSingleton(1)
singleton2 = PDCSingleton(2)

# >>> id(singleton1) == id(singleton2)
True
```

You can test whether a Singleton has been instantiated by calling the class method `.get_instance()` on your Singleton
Mode class.
If there is an instance, it will be returned. Otherwise, `None` will lbe returned.

## Other features

* Automatic recursive conversion to dict with the `.as_dict()` method.
* Automatic recursive conversion to and from JSON strings with the `.as_json()` and `.from_json()`  methods.

### PowerDataclass merging

The `PowerDataclass.merge(other)` allows you to merge two PowerDataclasses, rewriting the fields' values of the first
PDC with the corresponding values of the second PDCs, while retaining the memory address of the first PDC.

```python
class PDC(PowerDataclass):
    x: int
    y: int
    z: int


a = PDC(1, 2, 3)
b = PDC(3, 4, 5)
a.merge(b)
# >>> id(a) != id(b)
True
# >>> a.as_dict() == b.as_dict()
True
```

### PowerDataclass diff

A simple dictionary diff can be calculated between two instances of a same PowerDataclass by using the `.diff()` method

```python
class DiffPDC(PowerDataclass):
    x: int
    y: int
    z: int


a = DiffPDC(1, 2, 3)
b = DiffPDC(3, 4, 5)

# >>> a.diff(b)
{'x': (1, 3), 'y': (2, 4), 'z': (3, 5)}
```

Note that an attempt to compare `PowerDataclass`es of different type will result a `DiffImpossible` exception

### PowerConfig

The `powerdataclass.powerconfig` package contains two pre-made classes suitable for simple configuration management in
your services.
Those classes are: the `PowerConfig` and it's singleton mode subclass, the `GlobalPowerConfig`

Both of those share two extensions over regular `PowerDataclass`:

* A `PowerConfig` can be instantiated from the os environment. `PowerDataclass.Meta.envvar_prefix` will be prepended
  to capitalized names of `PowerConfig`'s fields' names.
   ```python
   class Config(PowerConfig):
       a: int
   
       class Meta:
           envvar_prefix = "CNF"
           
   # >>> Config.from_environ()
   Config(a=5)
   ```

  This class method will read the OS environment variable `CNF_A`. In this example. it ts assumed that this variable is
  present and is equal to `5`.
* there is a predefined `type_handler` for the `bool` type, which casts string values in  `(y, yes, 1, True)` to `True`.

 
---
Made with ⚡ by Arish Pyne (https://github.com/arishpyne/powerdataclass)