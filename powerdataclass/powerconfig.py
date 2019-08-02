from enum import Enum

from powerdataclass import PowerDataclass, FieldMeta, field, type_handler
from dataclasses import fields
from os import environ

class PowerConfigFieldMeta(Enum):
    IGNORE_ENVIRON = 'IGNORE_ENVIRON'


def ignore_environ_field(*args, **kwargs):
    if 'metadata' in kwargs:
        kwargs['metadata'].update({PowerConfigFieldMeta.IGNORE_ENVIRON: True})
    else:
        kwargs['metadata'] = {PowerConfigFieldMeta.IGNORE_ENVIRON: True}
    return field(*args, **kwargs)


def calculated_field(*args, **kwargs):
    if 'metadata' in kwargs:
        kwargs['metadata'].update({PowerConfigFieldMeta.IGNORE_ENVIRON: True})
    else:
        kwargs['metadata'] = {PowerConfigFieldMeta.IGNORE_ENVIRON: True}
    return ignore_environ_field(*args, **kwargs)


class PowerConfig(PowerDataclass):
    class Meta:
        envvar_prefix = "POWERCONFIG"

    @classmethod
    def from_environ(cls):
        print(cls)
        envdict = {field.name:
                       environ.get(f'{cls.Meta.envvar_prefix.upper()}_{field.name.upper()}')
                   for field in fields(cls) if
                   not field.metadata.get(PowerConfigFieldMeta.IGNORE_ENVIRON, False)}

        return cls(**envdict)

    @type_handler
    def __handle_bools__(self, v):
        if isinstance(v, str):
            return v.lower() in ['y', 'yes', '1', 'True']
        return bool(v)


class GlobalPowerConfig(PowerConfig):
    class Meta:
        singleton = True
