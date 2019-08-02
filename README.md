# ⚡ Power Dataclass ⚡
[![Build Status](https://api.travis-ci.org/arishpyne/powerdataclass.svg?branch=master)](https://api.travis-ci.org/arishpyne/powerdataclass.svg?branch=master) [![PyPI version](https://badge.fury.io/py/powerdataclass.svg)](https://pypi.python.org/pypi/powerdataclass/)   [![PyPI pyversions](https://img.shields.io/pypi/pyversions/powerdataclass.svg)](https://pypi.python.org/pypi/powerdataclass/)


>### DISCLAIMER
**This library is leveraging the inner mechanics of Python 3.7's `typing` module, and thus only works with Python 3.7**
**You may experience real shock when it breaks. Wear protective gloves.**

## Installation
`pip install powerdataclass`

## Usage
Python 3.7 have introduced a spiritual successor of `NamedTuple`: the `dataclass`.
While being nice, the `dataclass` type hinting is only, well, _hinting_.

This library gives you an ability to create dataclasses with field values automatically casted to 
the types defined in the `dataclass`'s type hints:

```python
from powerdataclass import *

class Coordinates(PowerDataclass):
    x: int
    y: int

c1 = Coordinates(1,2)
c2 = Coordinates('1', '2')
c3 = Coordinates(**{'x': 1.1, 'y': 2.2})


>>> c1
Coordinates(x=1, y=2)
>>> c1 == c2 == c3 
True
 ```  
   
This also works with every generic type that has a Python primitive type as it's origin. This applies to subscriptable types of any level of nestedness as well:
 
```python
class Vector(PowerDataclass):
    items: List[int]

v1 = Vector(['1', '2', '3'])
v2 = Vector({1.1, 2.2, 3.3})
v3 = Vector(range(1, 4))

>>> v1
Vector(items=[1, 2, 3])
>>> v1 == v2 == v3 
True
```

The typecasting also respects other dataclasses (and Power Dataclasses) declared in type hints.
If you pass a mapping in place of actual dataclass instance, Power Dataclass will attempt to unpack it to a corresponding dataclass:

```python
class Vector(PowerDataclass):
    items: List[int]
   
class Tensor(PowerDataclass):
    vectors: List[Vector]

t1 = Tensor(**{
    'vectors': [
        {'items': [1, 2, 3]},
        {'items': [4, 5, 6]},
        {'items': [7, 8, 9]},
    ]
})

>>> t1
Tensor(vectors=[Vector(items=[1, 2, 3]), Vector(items=[4, 5, 6]), Vector(items=[7, 8, 9])])
```

You can modify the behaviour of type casting by registering two types of handlers on your fancy PowerDataclass:
* **type handlers**: an unary method marked as a _type handler_ will be applied to any value that has a matching type declared in your dataclass typehints.
* **field handlers**: an unary method marked as a _field handler_ will be applied to a value of a specific PDC field.

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

>>> CoolBool('yes', 'no')
CoolBool(string_bool=True, negated_bool=True)
```   

Field handlers take precedence over the type handlers.
Field handlers and type handlers are scoped to a particular Power Dataclass. Inheritance is respected.

If you want to accept `None` as a valid value but also want non-null values to be typecasted you can mark your field as nullable by either setting the corresponding flag in the fields's `metadata` dictionary or using a premade partial:

```python
class Nihilus(PowerDataclass):
    x: int = field(metadata={FieldMeta.NULLABLE: True})
    y: int = nullable_field()

>>> Nihilus(None, None)
Nihilus(x=None, y=None) 
>>> Nihilus('1', None)
Nihilus(x=1, y=None)
```

If you want to disable type checking for a specific field you can mark your field as nullable by either setting the corresponding flag in the fields's `metadata` dictionary or using a premade partial:

```python
class Noncasted(PowerDataclass):
    x: int = field(metadata={FieldMeta.SKIP_TYPECASTING: True})
    y: int = noncasted_field()
    
>>> Noncasted('1', 2.2)
Noncasted(x='1', y=2.2)
```
    
If some of your field processing requires other fields typecasted before you can declare this field dependencies by name by setting the corresponding value in the fields's `metadata`:

```python
class Dependent(PowerDataclass):
    a: int
    b: int = field(metadata={FieldMeta.DEPENDS_ON_FIELDS: ['a']})
    c: int = field(metadata={FieldMeta.DEPENDS_ON_FIELDS: ['d', 'b']})
    d: int = field(metadata={FieldMeta.DEPENDS_ON_FIELDS: ['a']})
```
       
Fields will be topologically sorted by their dependencies and type casting will be done in this order. For this example, the order will be:
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
 
>>> CubeSquarer(4)
CubeSquarer(n=4, n_square=16, n_cube=256)
```

It is an error to declare a field as `calculatable` without registering a corresponding `field_handler`

## Other features
* Automatic recursive conversion to dict with the `.as_dict()` method.
* Automatic recursive conversion to and from JSON strings with the `.as_json()` and `.from_json()`  methods.


---
Made with ⚡ by Arish Pyne (https://github.com/arishpyne/powerdataclass)