import dataclasses
import json
from enum import Enum
from functools import partial
from typing import Mapping, Iterable, Any, Callable, TypeVar, ByteString

from toposort import toposort_flatten


def _is_iterable_but_not_string_type(value_type):
    return issubclass(value_type, Iterable) and not (issubclass(value_type, ByteString) or issubclass(value_type, str))


def _is_iterable_but_not_string(value):
    return isinstance(value, Iterable) and not (isinstance(value, ByteString) or isinstance(value, str))


def powercast(value: Any, _type: Any, type_casters: Mapping[Any, Callable] = None) -> Any:
    """
    Casts a `value` to a given `_type`. Descends recursively to cast generic subscripted types.
    If target type is a dataclass and value is a mapping, this dataclass will be instantiated by unpacking the mapping.
    :param value: a value to be casted
    :param _type: a type to cast the `value` to. Can be either a primitive type (like `bool` or `list`)
    or a generic subscripted type (like `typing.List[int]`).
    Casting to generic non-subscripted types like `typing.List` is forbidden.
    Casting to generic types, subscripted with TypeVars (like `typing.List[typing.TypeVar('T')`) is forbidden.
    Casting to generic subscripted types, which are not derived from a primitive type (like `typing.Iterable[str]`)
    is forbidden.
    :param type_casters: a mapping of {type: callable). If passed, functions from this mapping will be applied to the
    `value` using `_type` as a key.
    :return: `value` casted to `_type`
    """
    type_casters = type_casters or {}

    value_type = type(value)
    field_type_origin = getattr(_type, '__origin__', None)

    if value_type == _type:
        return value

    if _type in type_casters:
        return type_casters[_type](value)

    if dataclasses.is_dataclass(_type):
        if issubclass(value_type, Mapping):
            return _type(**value)
        elif _is_iterable_but_not_string_type(value_type):
            return _type(*value)
        else:
            try:
                # let's try direct instantiation with one argument
                return _type(value)
            except TypeError:
                raise ValueError(f'The type of this value is defined as'
                                 f' dataclass {_type.__name__}. Instantiation with value as sole argument failed.'
                                 f'To be able to cast the value of '
                                 f'this field to a dataclass instance through args or kwargs unpacking, '
                                 f'it must be an iterable or a mapping respectively, '
                                 f'while it is {value_type.__name__} now')

    if field_type_origin in (list, dict, tuple, set, frozenset):
        if field_type_origin in (list, tuple, set, frozenset):
            item_type = _type.__args__[0]
            if type(item_type) == TypeVar:
                raise TypeError(f'Casting to a TypeVar {_type} is forbidden')
            if not issubclass(value_type, Iterable):
                raise ValueError(f'Cannot cast a non-Iterable value {value} to {field_type_origin}')

            return field_type_origin((powercast(item, item_type, type_casters) for item in value))

        elif field_type_origin is dict:
            key_type = _type.__args__[0]
            value_type = _type.__args__[1]
            if type(key_type) == TypeVar or type(value_type) == TypeVar:
                raise TypeError(f'Casting to a TypeVar {_type} is forbidden')
            if not (issubclass(value_type, Mapping) or hasattr(value, 'items')):
                raise ValueError(f'Cannot cast a non-Mapping value {value} to {field_type_origin}')

            return field_type_origin({
                powercast(key, key_type): powercast(value, value_type, type_casters)
                for key, value in value.items()
            })

    elif field_type_origin:
        raise TypeError(f'Casting to a generic type {_type} is forbidden')
    else:
        # this is not a generic type, cast directly by instantiating
        return _type(value)


# FunkyTools:

def setfuncattr(name: str, value: Any):
    def _inner(method):
        setattr(method, name, value)
        return method

    return _inner


def collapse_classes(klasses, klass_name, klass_type=None):
    klass__dict__, last_klass = {}, None

    for kls in klasses:
        klass__dict__.update(getattr(kls, '__dict__', {}))
        last_klass = kls

    return type(klass_name, (klass_type or last_klass,), klass__dict__)


class PowerDataclassDefaultMeta:
    dataclass_init = True
    dataclass_repr = True
    dataclass_eq = True
    dataclass_order = False
    dataclass_unsafe_hash = False
    dataclass_frozen = False
    singleton = False
    json_encoder = None
    json_decoder = None
    as_dict_ignore_when_nested = False


class PowerDataclassBase(type):
    def __new__(mcs, name, bases, spec):
        klass = super().__new__(mcs, name, bases, spec)
        klass_type_handlers = {}
        klass_field_handlers = {}

        for base_klass in klass.__mro__:
            klass_field_handlers.update(getattr(base_klass, '__pdc_field_handlers__', {}))
            klass_type_handlers.update(getattr(base_klass, '__pdc_type_handlers__', {}))

        for method_name, method in spec.items():
            if hasattr(method, '__pdc_field_handler_field__'):
                klass_field_handlers.update({method.__pdc_field_handler_field__: method})
            if hasattr(method, '__pdc_type_handler_type__'):
                klass_type_handlers.update({method.__pdc_type_handler_type__: method})

        klass.Meta = collapse_classes((PowerDataclassDefaultMeta,
                                       *(klass.Meta for klass in (*bases, klass) if hasattr(klass, 'Meta'))),
                                      f'Meta', object)
        klass.__pdc_type_handlers__ = klass_type_handlers
        klass.__pdc_field_handlers__ = klass_field_handlers

        # convert to a dataclass, respecting the `dataclass_` Meta params
        klass = dataclasses.dataclass(klass,
                                      init=klass.Meta.dataclass_init,
                                      repr=klass.Meta.dataclass_repr,
                                      eq=klass.Meta.dataclass_eq,
                                      order=klass.Meta.dataclass_order,
                                      unsafe_hash=klass.Meta.dataclass_unsafe_hash,
                                      frozen=klass.Meta.dataclass_frozen,
                                      )

        for field in dataclasses.fields(klass):
            if field.metadata.get(FieldMeta.DEPENDS_ON_FIELDS, []) and field.name not in klass.__pdc_field_handlers__:
                raise MissingFieldHandler(f'A field handler must be registered on {klass.__name__} for '
                                          f'a field named `{field.name}` because it is declared as calculatable.')

        def __pdc_determine_field_handling_order__(cls):
            fields = dataclasses.fields(cls)

            fields_name_map = {}
            dependent_fields_present = False

            for field in fields:
                if field.metadata.get(FieldMeta.DEPENDS_ON_FIELDS):
                    dependent_fields_present = True
                fields_name_map.update({field.name: field for field in dataclasses.fields(cls)})

            if not dependent_fields_present:
                # bail out of toposort
                return fields

            fields_handling_dependency_graph = {
                field.name: set(field.metadata.get(FieldMeta.DEPENDS_ON_FIELDS, {})) for field in fields
            }

            fields_handling_execution_order = toposort_flatten(fields_handling_dependency_graph)

            return [fields_name_map[field_name] for field_name in fields_handling_execution_order]

        klass.__pdc_field_handling_order__ = __pdc_determine_field_handling_order__(klass)

        if klass.Meta.singleton:
            klass.__singleton_instance__ = None

            def __singleton__new__(cls, *args, **kwargs):
                if cls.__singleton_instance__ is None:
                    cls.__singleton_instance__ = object.__new__(cls)
                return cls.__singleton_instance__

            def get_instance(cls):
                if cls.__singleton_instance__:
                    return cls.__singleton_instance__

            klass.__new__ = staticmethod(__singleton__new__)
            klass.get_instance = classmethod(get_instance)

        return klass


# wrap a PDC's method with this decorator to register it as a field handler.
# field handlers must return a value and will be used to cast values to the type they're registered on.
# field handlers can also be used a tool to calculate values of a field based on the values of other fields.
# See `FieldMeta.DEPENDS_ON_FIELDS` to achieve this behaviour.
field_handler = partial(setfuncattr, '__pdc_field_handler_field__')

# wrap a PDC's method with this decorator to register it as a type handler.
# type handlers must return a value and will be used to cast values to the type they're registered on.
type_handler = partial(setfuncattr, '__pdc_type_handler_type__')


class FieldMeta(Enum):
    """
    Use this in PowerDataclass field's `metadata` to change the behaviour of a field.
    SKIP_TYPECASTING: value must be a `bool`. If True, any typecasting for this field will lbe ignored.
    NULLABLE: value must be a `bool`. If True, PowerDataclass typecasting will not raise errors for fields with
    a defined type and None value.
    DEPENDS_ON_FIELDS: value must be a sequence of field names on which the casting/handling of this field
    depends. Let's say that you have a PDC with two fields: `x` and `y` and you want the value of the field `y` to
    always be equal to the square of `x` value. To achieve this, you can mark field `y` as dependent on `x` and
    then return a value of x ** 2 in `y` field handler.
    Cyclical dependencies are an error.
    """
    SKIP_TYPECASTING = 'skip_typecasting'
    NULLABLE = 'nullable'
    DEPENDS_ON_FIELDS = 'depends_on_fields'


field = dataclasses.field


def nullable_field(*args, **kwargs):
    if 'metadata' in kwargs:
        kwargs['metadata'].update({FieldMeta.NULLABLE: True})
    else:
        kwargs['metadata'] = {FieldMeta.NULLABLE: True}
    return field(*args, **kwargs)


def noncasted_field(*args, **kwargs):
    if 'metadata' in kwargs:
        kwargs['metadata'].update({FieldMeta.SKIP_TYPECASTING: True})
    else:
        kwargs['metadata'] = {FieldMeta.SKIP_TYPECASTING: True}
    return field(*args, **kwargs)


def calculated_field(depends_on_fields=None, *args, **kwargs):
    depends_on_fields = depends_on_fields or []
    if 'metadata' in kwargs:
        kwargs['metadata'].update({FieldMeta.DEPENDS_ON_FIELDS: depends_on_fields})
    else:
        kwargs['metadata'] = {FieldMeta.DEPENDS_ON_FIELDS: depends_on_fields}
    kwargs['default'] = None

    return field(*args, **kwargs)


class PowerDataclass(metaclass=PowerDataclassBase):
    def __post_init__(self):
        self.__pdc_handle_fields__()

    def __pdc_handle_fields__(self):
        for field in self.__pdc_field_handling_order__:
            field_value = getattr(self, field.name)

            if field.metadata.get(FieldMeta.SKIP_TYPECASTING, False):
                continue

            if field.name in self.__pdc_field_handlers__:
                field_value = self.__pdc_field_handlers__[field.name](self, field_value)
            elif field.type in self.__pdc_type_handlers__:
                field_value = self.__pdc_type_handlers__[field.type](self, field_value)
            else:
                if field_value is None:
                    # Turns out, there _is_ a way to check for a missing default ᕕ( ᐛ )ᕗ
                    field_has_default = (field.default is not dataclasses.MISSING)
                    if field.metadata.get(FieldMeta.NULLABLE, False) or field_has_default:
                        continue
                    else:
                        raise ValueError(f'A value for {self.__class__.__name__} field `{field.name}` cannot be None')

                field_value = powercast(field_value, field.type, self.__bound_pdc_type_handlers__)

            setattr(self, field.name, field_value)

    @property
    def __bound_pdc_type_handlers__(self):
        return {k: partial(v, self) for k, v in self.__pdc_type_handlers__.items()}

    def as_dict(self, force=False):
        asdict_dict = {f.name: getattr(self, f.name) for f in dataclasses.fields(self)}

        def _convert_to_dict(v):
            if dataclasses.is_dataclass(v):
                if isinstance(v, PowerDataclass):
                    if v.Meta.as_dict_ignore_when_nested and not force:
                        return v
                    return v.as_dict(force=force)
                # plain dataclass
                return dataclasses.asdict(v)

            if _is_iterable_but_not_string(v):
                return type(v)((_convert_to_dict(i) for i in v))
            elif isinstance(v, Mapping):
                return type(v)(**{k: _convert_to_dict(vv) for k, vv in v.items()})

            # in other cases, just return the value as-is
            return v

        return {k: _convert_to_dict(v) for k, v in asdict_dict.items()}

    def as_json(self, force=False):
        return json.dumps(self.as_dict(force), cls=self.Meta.json_encoder)

    @classmethod
    def from_json(cls, json_string: str):
        return cls(**json.loads(json_string, cls=cls.Meta.json_decoder))

    def merge(self, other):
        """
        Reads another PowerDataclassInstance, replacing the values of this instance fields
        with the corresponding fields' values of the other instance, while retaining the memory address
        Useful for reloading from disk or database
        """

        for field in dataclasses.fields(other):
            setattr(self, field.name, getattr(other, field.name))

    def diff(self, other):
        """
        Returns a simple diff between two PowerDataclasses, provided that tey belong to a same class
        """
        if type(self) != type(other):
            raise DiffImpossible(
                f"Can't get a diff between an instance of {type(self)} and an instance of f{type(other)}")
        diff_dict = {}
        for field in dataclasses.fields(self):
            self_value = getattr(self, f'{field.name}')
            other_value = getattr(other, f'{field.name}')
            if self_value != other_value:
                diff_dict.update({f'{field.name}': (self_value, other_value)})
        return diff_dict


class PowerDataclassException(Exception):
    pass


class MissingFieldHandler(PowerDataclassException):
    """Raised when no registered field handler for calculated field can be found"""
    pass


class DiffImpossible(PowerDataclassException):
    """Raised when an attempt to get a diff between two PowerDataclasses """
