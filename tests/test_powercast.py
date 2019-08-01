import dataclasses
import math
import typing
from typing import OrderedDict

import pytest

from powerdataclass import powercast


def _test_powercast(value, expected_type, expected_value):
    powercasted_value = powercast(value, expected_type)
    assert type(powercasted_value) == expected_type
    assert powercasted_value == expected_value


def _test_powercast_subscriptable_sequence(
        value, powercast_type, expected_return_type, expected_item_type, expected_value):
    powercasted_value = powercast(value, powercast_type)
    assert type(powercasted_value) == expected_return_type
    for i in powercasted_value:
        assert type(i) == expected_item_type
    assert powercasted_value == expected_value


def _test_powercast_subscriptable_mapping(
        value, powercast_type, expected_return_type, expected_key_type, expected_value_type, expected_value):
    powercasted_value = powercast(value, powercast_type)
    assert type(powercasted_value) == expected_return_type
    for k, v in powercasted_value.items():
        assert type(k) == expected_key_type
        assert type(v) == expected_value_type
    assert powercasted_value == expected_value


@pytest.mark.parametrize('value, expected_type, expected_value', (
        ('1', int, 1),
        (1.1, int, 1),
        (1, str, '1'),
        (1.1, str, '1.1'),
        ([], bool, False),
        (1, bool, True),
        (1, float, 1.0),
        ('1.22', float, 1.22),
))
def test_powercast_casts_to_primitive_types(value, expected_type, expected_value):
    _test_powercast(value, expected_type, expected_value)


@pytest.mark.parametrize('value, expected_type, expected_value', (
        ('1234', list, ['1', '2', '3', '4']),
        ('1234', tuple, ('1', '2', '3', '4')),
        ('1234', set, {'1', '2', '3', '4'}),
        ('1234', frozenset, frozenset(('1', '2', '3', '4'))),
        (OrderedDict([('1', '2')]), dict, {'1': '2'})
))
def test_powercast_casts_to_primitive_collection_types(value, expected_type, expected_value):
    _test_powercast(value, expected_type, expected_value)


@pytest.mark.parametrize('value, powercast_type, expected_return_type, expected_item_type, expected_value', (
        ('1234', typing.List[int], list, int, [1, 2, 3, 4]),
        ('1234', typing.Tuple[int], tuple, int, (1, 2, 3, 4)),
        ('1234', typing.Set[int], set, int, {1, 2, 3, 4}),
        ('1234', typing.FrozenSet[int], frozenset, int, frozenset((1, 2, 3, 4))),
))
def test_powercast_casts_to_subscriptable_collection_sequence_types(
        value, powercast_type, expected_return_type, expected_item_type, expected_value):
    _test_powercast_subscriptable_sequence(
        value, powercast_type, expected_return_type, expected_item_type, expected_value)


@pytest.mark.parametrize(
    'value, powercast_type, expected_return_type, expected_key_type, expected_value_type, expected_value', (
            (OrderedDict([('1', '0.2')]), typing.Dict[int, float], dict, int, float, {1: 0.2}),
    ))
def test_powercast_casts_to_subscriptable_collection_sequence_types(
        value, powercast_type, expected_return_type, expected_key_type, expected_value_type, expected_value):
    _test_powercast_subscriptable_mapping(
        value, powercast_type, expected_return_type, expected_key_type, expected_value_type, expected_value)


def test_powercast_generic_non_subscriptable_types_are_forbidden():
    with pytest.raises(TypeError):
        powercast('1', typing.List)


def test_powercast_casting_a_non_sequence_to_sequence_type_is_forbidden():
    with pytest.raises(ValueError):
        powercast(0.25, typing.List[int])


def test_powercast_casting_a_non_mapping_to_mapping_type_is_forbidden():
    with pytest.raises(ValueError):
        powercast('1', typing.Dict[int, float])


def test_powercast_casting_to_subscripted_sequence_type_with_generic_items_is_forbidden():
    T = typing.TypeVar('T')
    with pytest.raises(TypeError):
        powercast('1', typing.List[T])


def test_powercast_casting_to_subscripted_mapping_type_with_generic_keys_is_forbidden():
    T = typing.TypeVar('T')
    with pytest.raises(TypeError):
        powercast({'1': '2'}, typing.Dict[T, float])


def test_powercast_casting_to_subscripted_mapping_type_with_generic_values_is_forbidden():
    T = typing.TypeVar('T')
    with pytest.raises(TypeError):
        powercast({'1': '2'}, typing.Dict[int, T])


def test_powercast_type_handlers_are_respected_if_passed():
    T = typing.TypeVar('T')

    def handle_int(v):
        return int(v) ** 2

    type_casters = {
        int: handle_int
    }

    v = powercast(['11', 2.22, False], typing.List[int], type_casters)
    assert v == [121, 4, 0]


def test_dataclass_casting():
    @dataclasses.dataclass
    class DC:
        x: int

    v = powercast({'x': 1}, DC)
    assert v == DC(1)


def test_dataclass_casting_from_a_non_mapping_is_forbidden():
    @dataclasses.dataclass
    class DC:
        x: int

    with pytest.raises(ValueError):
        powercast([1], DC)
