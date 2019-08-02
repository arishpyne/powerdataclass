import typing
from json import JSONEncoder, JSONDecoder
from unittest import mock

import pytest

from powerdataclass import PowerDataclass, field_handler, type_handler, noncasted_field, \
    nullable_field, field, FieldMeta, calculated_field, MissingFieldHandler


def test_pdc_calls_powercast_for_types_not_handled_by_handlers():
    class PDC(PowerDataclass):
        x: int
        y: str

    with mock.patch('powerdataclass.powercast') as powercast_mock:
        pdc = PDC('1', 2)

        assert powercast_mock.call_args_list == [
            mock.call('1', int, PDC.__pdc_type_handlers__),
            mock.call(2, str, PDC.__pdc_type_handlers__)
        ]


def test_pdc_calls_type_handlers_for_registered_types():
    int_handler_mock = mock.MagicMock()
    str_handler_mock = mock.MagicMock()

    class PDC(PowerDataclass):
        x: int
        y: str

        @type_handler(int)
        def int_handler(self, v):
            return int_handler_mock(self, v)

        @type_handler(str)
        def str_handler(self, v):
            return str_handler_mock(self, v)

    with mock.patch('powerdataclass.powercast', return_value=None) as powercast_mock:
        pdc = PDC('1', 2)

        assert powercast_mock.call_args_list == []
        assert int_handler_mock.call_args_list == [mock.call(pdc, '1')]
        assert str_handler_mock.call_args_list == [mock.call(pdc, 2)]


def test_pdc_type_handlers_are_applied_for_nested_values_as_well():
    class PDC(PowerDataclass):
        x: int
        y: typing.List[int]

        @type_handler(int)
        def int_handler(self, v):
            return int(v) ** 2

    pdc = PDC('2', ['3', '4', '5'])
    assert pdc.x == 4
    assert pdc.y == [9, 16, 25]


def test_pdc_calls_field_handlers_for_registered_fields():
    field_x_handler_mock = mock.MagicMock()
    field_y_handler_mock = mock.MagicMock()

    class PDC(PowerDataclass):
        x: int
        y: str

        @field_handler('x')
        def field_x_handler(self, v):
            return field_x_handler_mock(self, v)

        @field_handler('y')
        def field_y_handler(self, v):
            return field_y_handler_mock(self, v)

    with mock.patch('powerdataclass.powercast', return_value=None) as powercast_mock:
        pdc = PDC('1', 2)

        assert powercast_mock.call_args_list == []
        assert field_x_handler_mock.call_args_list == [mock.call(pdc, '1')]
        assert field_y_handler_mock.call_args_list == [mock.call(pdc, 2)]


def test_pdc_field_handlers_take_precedence_over_type_handlers():
    field_x_handler_mock = mock.MagicMock()
    field_y_handler_mock = mock.MagicMock()

    int_handler_mock = mock.MagicMock()
    str_handler_mock = mock.MagicMock()

    class PDC(PowerDataclass):
        x: int
        y: str

        @field_handler('x')
        def field_x_handler(self, v):
            return field_x_handler_mock(self, v)

        @field_handler('y')
        def field_y_handler(self, v):
            return field_y_handler_mock(self, v)

        @type_handler(int)
        def int_handler(self, v):
            return int_handler_mock(self, v)

        @type_handler(str)
        def str_handler(self, v):
            return str_handler_mock(self, v)

    with mock.patch('powerdataclass.powercast', return_value=None) as powercast_mock:
        pdc = PDC('1', 2)

        assert powercast_mock.call_args_list == []
        assert field_x_handler_mock.call_args_list == [mock.call(pdc, '1')]
        assert field_y_handler_mock.call_args_list == [mock.call(pdc, 2)]
        assert int_handler_mock.call_args_list == []
        assert str_handler_mock.call_args_list == []


def test_pdc_field_casting_completely_ignored_for_marked_fields():
    field_x_handler_mock = mock.MagicMock()
    field_y_handler_mock = mock.MagicMock()

    int_handler_mock = mock.MagicMock()
    str_handler_mock = mock.MagicMock()

    class PDC(PowerDataclass):
        x: int = noncasted_field()
        y: str = noncasted_field()

        @field_handler('x')
        def field_x_handler(self, v):
            return field_x_handler_mock(self, v)

        @field_handler('y')
        def field_y_handler(self, v):
            return field_y_handler_mock(self, v)

        @type_handler(int)
        def int_handler(self, v):
            return int_handler_mock(self, v)

        @type_handler(str)
        def str_handler(self, v):
            return str_handler_mock(self, v)

    with mock.patch('powerdataclass.powercast', return_value=None) as powercast_mock:
        assert powercast_mock.call_args_list == []
        assert field_x_handler_mock.call_args_list == []
        assert field_y_handler_mock.call_args_list == []
        assert int_handler_mock.call_args_list == []
        assert str_handler_mock.call_args_list == []


def test_pdc_nullable_fields():
    class PDC(PowerDataclass):
        x: int = nullable_field()

    PDC(None)


def test_pdc_nullable_fields_raises_on_none_in_regular_fields():
    class PDC(PowerDataclass):
        x: int

    with pytest.raises(ValueError):
        PDC(None)


def test_pdc_dependent_fields_field_handlers_execution_order():
    recorded_handlers_execution_order = []

    def get_test_field_handler(name):
        def test_field_handler(self, v):
            recorded_handlers_execution_order.append(name)
            return v

        return test_field_handler

    class PDC(PowerDataclass):
        a: int = field(metadata={FieldMeta.DEPENDS_ON_FIELDS: ['b', 'd', 'f']})
        b: int = field(metadata={FieldMeta.DEPENDS_ON_FIELDS: ['c']})
        c: int = field(metadata={FieldMeta.DEPENDS_ON_FIELDS: ['d']})
        d: int = field(metadata={FieldMeta.DEPENDS_ON_FIELDS: []})
        e: int = field(metadata={FieldMeta.DEPENDS_ON_FIELDS: ['d']})
        f: int = field(metadata={FieldMeta.DEPENDS_ON_FIELDS: ['b', 'c', 'e']})

        @field_handler('a')
        def field_a_handler(self, v):
            return get_test_field_handler('a')(self, v)

        @field_handler('b')
        def field_b_handler(self, v):
            return get_test_field_handler('b')(self, v)

        @field_handler('c')
        def field_c_handler(self, v):
            return get_test_field_handler('c')(self, v)

        @field_handler('d')
        def field_d_handler(self, v):
            return get_test_field_handler('d')(self, v)

        @field_handler('e')
        def field_e_handler(self, v):
            return get_test_field_handler('e')(self, v)

        @field_handler('f')
        def field_f_handler(self, v):
            return get_test_field_handler('f')(self, v)

    PDC(1, 2, 3, 4, 5, 6)
    assert recorded_handlers_execution_order == ['d', 'c', 'e', 'b', 'f', 'a']


def test_pdc_recreatable_from_dict_form():
    class PDC(PowerDataclass):
        x: int
        y: str

    initial = PDC(1, '2')
    dict_form = initial.as_dict()
    assert dict_form == {
        'x': 1,
        'y': '2'
    }

    recreated = PDC(**dict_form)
    assert initial == recreated


def test_pdc_recreatable_from_json_form():
    class PDC(PowerDataclass):
        x: int
        y: str

    initial = PDC(1, '2')
    json_form = initial.as_json()

    recreated = PDC.from_json(json_form)
    assert initial == recreated


def test_pdc_with_nested_pdcs_recreatable_from_dict_form():
    class PDCNestedNested(PowerDataclass):
        n: str
        t: bool

    class PDCNested(PowerDataclass):
        a: int
        b: str
        nested_nested: typing.List[PDCNestedNested]

    class PDC(PowerDataclass):
        x: int
        y: str
        nested: PDCNested

    initial = PDC(1, '2', PDCNested(3, '4', [PDCNestedNested('y', True), PDCNestedNested('n', False)]))
    dict_form = initial.as_dict()
    assert dict_form == {
        'x': 1,
        'y': '2',
        'nested': {
            'a': 3,
            'b': '4',
            'nested_nested': [
                {'n': 'y', 't': True},
                {'n': 'n', 't': False}
            ]
        },
    }

    recreated = PDC(**dict_form)
    assert initial == recreated


def test_pdc_calculated_field():
    class PDC(PowerDataclass):
        n: int
        n_square: int = field(default=None, metadata={FieldMeta.DEPENDS_ON_FIELDS: ['n']})
        n_cube: int = calculated_field(depends_on_fields=['n'])

        @field_handler('n_square')
        def handle_n_square(self, v):
            return self.n ** 2

        @field_handler('n_cube')
        def handle_n_cube(self, v):
            return self.n ** 3

    pdc = PDC(n=2)
    assert pdc.n == 2
    assert pdc.n_square == 4
    assert pdc.n_cube == 8


def test_pdc_calculated_field_raises_if_no_field_handler_is_registered_on_calculated_field():
    with pytest.raises(MissingFieldHandler):
        class PDC(PowerDataclass):
            n: int
            n_square: int = calculated_field(depends_on_fields=['n'])


def test_pdc_uses_json_decoder_and_encoders_from_meta():
    class CustomJSONEncoder(JSONEncoder):
        pass

    class CustomJSONDecoder(JSONDecoder):
        pass

    class PDC(PowerDataclass):
        n: int

        class Meta:
            json_encoder = CustomJSONEncoder
            json_decoder = CustomJSONDecoder

    with mock.patch('json.dumps', return_value='') as dumps_mock:
        PDC(1).as_json()

    assert dumps_mock.call_args[1]['cls'] == CustomJSONEncoder

    with mock.patch('json.loads', return_value={'n': 1}) as loads_mock:
        PDC.from_json('{"n": 1}')

    assert loads_mock.call_args[1]['cls'] == CustomJSONDecoder
