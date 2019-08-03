from powerdataclass.powerconfig import PowerConfig, ignore_environ_field


def test_powerconfig_reads_from_env(monkeypatch):
    monkeypatch.setenv('POWERCONFIG_A', '1')

    class PC(PowerConfig):
        a: int

    pc = PC.from_environ()

    assert pc.a == 1


def test_powerconfig_skips_reading_from_env_for_marked_fields(monkeypatch):
    monkeypatch.setenv('POWERCONFIG_A', '1')
    monkeypatch.setenv('POWERCONFIG_B', '2')

    class PC(PowerConfig):
        a: int
        b: int = ignore_environ_field(default=3)

    pc = PC.from_environ()

    assert pc.a == 1
    assert pc.b == 3
