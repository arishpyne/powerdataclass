import dataclasses
import json
from enum import Enum
from functools import partial
from typing import Mapping, Iterable, Any, Callable, TypeVar

from toposort import toposort_flatten


class PowerDataclassBase(type):
    def __new__(mcs, name, bases, spec):
        klass_type_handlers = {}
        klass_field_handlers = {}

        for base_klass in bases:
            klass_field_handlers.update(getattr(base_klass, '__pdc_field_handlers__', {}))
            klass_type_handlers.update(getattr(base_klass, '__pdc_type_handlers__', {}))

        for method_name, method in spec.items():
            if hasattr(method, '__pdc_field_handler_field__'):
                klass_field_handlers.update({method.__pdc_field_handler_field__: method})
            if hasattr(method, '__pdc_type_handler_type__'):
                klass_type_handlers.update({method.__pdc_type_handler_type__: method})

        klass = super().__new__(mcs, name, bases, spec)

        klass.__pdc_type_handlers__ = klass_type_handlers
        klass.__pdc_field_handlers__ = klass_field_handlers

        return klass


def setfuncattr(name: str, value: Any):
    def _inner(method):
        setattr(method, name, value)
        return method

    return _inner


register_pdc_field_handler = partial(setfuncattr, '__pdc_field_handler_field__')
register_pdc_type_handler = partial(setfuncattr, '__pdc_type_handler_type__')


def powercast(value: Any, _type: Any, type_casters: Mapping[Any, Callable] = None) -> Any:
    type_casters = type_casters or {}

    value_type = type(value)
    field_type_origin = getattr(_type, '__origin__', None)

    if value_type == _type:
        return value

    if value_type in type_casters:
        return type_casters[value_type](value)

    if dataclasses.is_dataclass(_type):
        if not issubclass(value_type, Mapping):
            raise TypeError(f'The type of this value is defined as'
                            f' dataclass {_type.__name__}. To be able to cast the value of '
                            f'this field to a dataclass instance, '
                            f'it must be a mapping, while it is {value_type.__name__} now')
        return _type(**value)

    if field_type_origin in (list, dict, tuple, set, frozenset):
        if field_type_origin in (list, tuple, set, frozenset):
            item_type = _type.__args__[0]
            if type(item_type) == TypeVar:
                raise TypeError(f'Casting to a TypeVar {_type} is forbidden')
            if not issubclass(value_type, Iterable):
                raise TypeError(f'Cannot cast a non-Iterable value {value} to {field_type_origin}')

            return field_type_origin((powercast(item, item_type) for item in value))

        elif field_type_origin is dict:
            key_type = _type.__args__[0]
            value_type = _type.__args__[1]
            if type(key_type) == TypeVar or type(value_type) == TypeVar:
                raise TypeError(f'Casting to a TypeVar {_type} is forbidden')
            if not issubclass(value_type, Mapping):
                raise TypeError(f'Cannot cast a non-Mapping value {value} to {field_type_origin}')

            return field_type_origin({
                powercast(key, key_type): powercast(value, value_type)
                for key, value in value.items()
            })

    elif field_type_origin:
        raise TypeError(f'Casting to a generic type {_type} is forbidden')
    else:
        # this is not a generic type, rcast directly by instantiating
        return _type(value)


class FieldMeta(Enum):
    SKIP_TYPECASTING = 'skip_typecasting'
    DEPENDS_ON_FIELDS = 'depends_on_fields'
    NULLABLE = 'nullable'


field = dataclasses.field
nullable_field = partial(dataclasses.field, metadata={FieldMeta.NULLABLE: True})
noncasted_field = partial(dataclasses.field, metadata={FieldMeta.SKIP_TYPECASTING: True})


@dataclasses.dataclass
class PowerDataclass(metaclass=PowerDataclassBase):
    def __post_init__(self):
        self.__pdc_handle_fields__()

    def __pdc_handle_fields__(self):
        for field in self.__pdc_determine_field_handling_order__():
            field_value = getattr(self, field.name)

            if field_value is None:
                if field.metadata.get(FieldMeta.NULLABLE, False):
                    continue
                else:
                    raise ValueError(f'A value for {self.__class__.__name__} field `{field.name}` cannot be None')

            if field.metadata.get(FieldMeta.SKIP_TYPECASTING, False):
                continue

            if type(field_value) == field.type:
                continue

            if field.name in self.__pdc_field_handlers__:
                field_value = self.__pdc_field_handlers__[field.name](self, field_value)
            elif field.type in self.__pdc_type_handlers__:
                field_value = self.__pdc_type_handlers__[field.type](self, field_value)
            else:
                # now let the generic typecasting do its job
                field_value = powercast(field_value, field.type, self.__pdc_type_handlers__)

            setattr(self, field.name, field_value)

    def __pdc_determine_field_handling_order__(self):
        fields = dataclasses.fields(self)

        fields_name_map = {field.name: field for field in dataclasses.fields(self)}

        fields_handling_dependency_graph = {
            field.name: set(field.metadata.get(FieldMeta.DEPENDS_ON_FIELDS, {})) for field in fields
        }

        fields_handling_execution_order = toposort_flatten(fields_handling_dependency_graph)

        return (fields_name_map[field_name] for field_name in fields_handling_execution_order)

    def as_dict(self):
        asdict_dict = dataclasses.asdict(self)
        for k, v in asdict_dict.items():
            if dataclasses.is_dataclass(v):
                if getattr(v, 'as_dict'):
                    asdict_dict[k] = v.asdict()
                else:
                    asdict_dict[k] = dataclasses.asdict(v)

        return asdict_dict

    def as_json(self):
        return json.dumps(self.as_dict())

    @classmethod
    def from_json(cls, json_string: str):
        return cls(**json.loads(json_string))
