# ⚡ Power Dataclass ⚡

### DISCLAIMER
**This library is leveraging the inner mechanics of Python 3.7's `typing` module, and thus only works with Python 3.7**
**You may experience real shock when it breaks. Wear protective gloves.**

## Installation
`pip install powerdataclass`

## Usage
Python 3.7 have introduced a spiritual successor of `NamedTyple`: the `dataclass`.
While being nice, the `dataclass` type hinting is only, well, _hinting_.

This library gives you an ability to create dataclasses with field values automatically casted to 
the types defined in the `dataclass`'s type hints:

    @dataclasses.dataclass
    class Coordinates(powerdataclass.PowerDataclass):
        x: int
        y: int
    
    c1 = Coordinates(1,2)
    c2 = Coordinates('1', '2')
    c3 = Coordinates(**{'x': 1.1, 'y': 2.2})
    
    
    >>> c1
    Coordinates(x=1, y=2)
    >>> c1 == c2 == c3 
    True
    
   
This also works with every generic type that has a Python primitive type as it's origin. This applies to subscriptable types of any level of nestedness as well:
   
    @dataclasses.dataclass
    class Vector(powerdataclass.PowerDataclass):
        items: List[int]
    
    v1 = Vector(['1', '2', '3'])
    v2 = Vector({1.1, 2.2, 3.3})
    v3 = Vector(range(1, 4))
    
    >>> v1
    Vector(items=[1, 2, 3])
    >>> v1 == v2 == v3 
    True


The typecasting also respects other dataclasses (and Power Dataclasses) declared in type hints.
If you pass a mapping in place of actual dataclass instance, Power Dataclass will attempt to unpack it to a corresponding dataclass:

    @dataclasses.dataclass
    class Vector(powerdataclass.PowerDataclass):
        items: List[int]
       
    @dataclasses.dataclass
    class Tensor(powerdataclass.PowerDataclass):
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

You can modify the behaviour of type casting by registering two types of handlers on your fancy PowerDataclass:
* **type handlers**: an unary method marked as a _type handler_ will be applied to any value that has a matching type declared in your dataclass typehints.
* **field handlers**: an unary method marked as a _field handler_ will be applied to a value of a specific PDC field.

Those functions must _always_ return a value.

You can do this by marking your methods with special decorators:

    @dataclasses.dataclass
    class CoolBool(powerdataclass.PowerDataclass):
        string_bool: bool
        negated_bool: bool
    
        @powerdataclass.register_pdc_type_handler(bool)
        def handle_bools(self, v):
            if type(v) is str:
                return v.lower() in ['y', 'yes', '1', 'True']
            else:
                return bool(v)
                
        @powerdataclass.register_pdc_field_handler('negated_bool')
        def handle_xored_bools(self, v):
            return not self.handle_bools(v)

    >>> CoolBool('yes', 'no')
    CoolBool(string_bool=True, negated_bool=True)
    
Field handlers take precedence over the type handlers.
Field handlers and type handlers are scoped to a particular Power Dataclass. Inheritance is respected.

If you want to accept `None` as a valid value but also want non-null values to be typecasted you can mark your field as nullable by either setting the corresponding flag in the fields's `metadata` dictionary or using a premade partial:

    @dataclasses.dataclass
    class Nihilus(powerdataclass.PowerDataclass):
        x: int = dataclasses.field(metadata={powerdataclass.FieldMeta.NULLABLE: True})
        y: int = powerdataclass.nullable_field()
    
    >>> Nihilus(None, None)
    Nihilus(x=None, y=None) 
    >>> Nihilus('1', None)
    Nihilus(x=1, y=None)

If you want to disable type checking for a specific field you can mark your field as nullable by either setting the corresponding flag in the fields's `metadata` dictionary or using a premade partial:

    @dataclasses.dataclass
    class Noncasted(powerdataclass.PowerDataclass):
        x: int = field(metadata={powerdataclass.FieldMeta.SKIP_TYPECASTING: True})
        y: int = powerdataclass.noncasted_field()
        
    >>> Noncasted('1', 2.2)
    Noncasted(x='1', y=2.2)
    
If some of your field processing requires other fields typecasted before you can declare this field dependencies by name by setting the corresponding value in the fields's `metadata`:

    @dataclasses.dataclass
    class Dependent(powerdataclass.PowerDataclass):
        a: int
        b: int = field(metadata={powerdataclass.FieldMeta.DEPENDS_ON_FIELDS: ['a']})
        c: int = field(metadata={powerdataclass.FieldMeta.DEPENDS_ON_FIELDS: ['d', 'b']})
        d: int = field(metadata={powerdataclass.FieldMeta.DEPENDS_ON_FIELDS: ['a']})
        
Fields will be topologically sorted by their dependencies and type casting will be done in this order. For this example, the order will be:
1) a
2) b
3) d
4) c

## Other features
Power Dataclasses support automatic recursive conversion to dict with the `.as_dict()` method.
Power Dataclasses support automatic recursive conversion to and from JSON strings with the `.as_json()` and `.from_json()`  methods.



---
Made with ⚡ by Arish Pyne