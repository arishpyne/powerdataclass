import dataclasses

from powerdataclass import PowerDataclass, field_handler, type_handler


def test_pdc_metaclass_pdc_meta_collapses_pdc_meta():
    @dataclasses.dataclass
    class PDC(PowerDataclass):
        pass

    @dataclasses.dataclass
    class PDC2(PDC):
        class Meta:
            a = 1

    @dataclasses.dataclass
    class PDC3(PDC2):
        class Meta:
            a = 2
            b = 3

    assert getattr(PDC.Meta, 'a', None) is None
    assert getattr(PDC2.Meta, 'b', None) is None
    assert getattr(PDC2.Meta, 'a') == 1
    assert getattr(PDC2.Meta, 'b', None) is None
    assert getattr(PDC3.Meta, 'a') == 2
    assert getattr(PDC3.Meta, 'b') == 3



def test_pdc_metaclass_registers_handlers():
    @dataclasses.dataclass
    class PDC(PowerDataclass):
        @field_handler('field')
        def handle_field(self, v):
            return v

        @type_handler(bool)
        def handle_type(self, v):
            return v

    assert PDC.__pdc_type_handlers__ == {bool: PDC.handle_type}
    assert PDC.__pdc_field_handlers__ == {'field': PDC.handle_field}


def test_pdc_metaclass_registers_handlers_respects_inheritance():
    @dataclasses.dataclass
    class PDC(PowerDataclass):
        @field_handler('field')
        def handle_field(self, v):
            return v

        @type_handler(bool)
        def handle_type(self, v):
            return v

    @dataclasses.dataclass
    class PDC2(PDC):
        @field_handler('field2')
        def handle_field2(self, v):
            return v

        @type_handler(list)
        def handle_type2(self, v):
            return v

    assert PDC2.__pdc_type_handlers__ == {bool: PDC.handle_type, list: PDC2.handle_type2}
    assert PDC2.__pdc_field_handlers__ == {'field': PDC.handle_field, 'field2': PDC2.handle_field2}


def test_pdc_metaclass_registers_handlers_overwrites_parent_handlers_if_matching_type_or_field():
    @dataclasses.dataclass
    class PDC(PowerDataclass):
        @field_handler('field')
        def handle_field(self, v):
            return v

        @type_handler(bool)
        def handle_type(self, v):
            return v

    @dataclasses.dataclass
    class PDC2(PDC):
        @field_handler('field')
        def handle_field(self, v):
            return v

        @type_handler(bool)
        def handle_type(self, v):
            return v

    assert PDC2.__pdc_type_handlers__ == {bool: PDC2.handle_type}
    assert PDC2.__pdc_field_handlers__ == {'field': PDC2.handle_field}


def test_pdc_metaclass_collapses_meta():
    @dataclasses.dataclass
    class PDC(PowerDataclass):
        @field_handler('field')
        def handle_field(self, v):
            return v

        @type_handler(bool)
        def handle_type(self, v):
            return v

    @dataclasses.dataclass
    class PDC2(PDC):
        @field_handler('field')
        def handle_field(self, v):
            return v

        @type_handler(bool)
        def handle_type(self, v):
            return v

    assert PDC2.__pdc_type_handlers__ == {bool: PDC2.handle_type}
    assert PDC2.__pdc_field_handlers__ == {'field': PDC2.handle_field}