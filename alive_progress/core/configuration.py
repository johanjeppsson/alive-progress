import os
from collections import namedtuple
from itertools import repeat
from types import FunctionType

from ..animations import bars, spinners
from ..animations.utils import spinner_player
from ..styles.internal import BARS, SPINNERS, THEMES

NO_SPINNER = object()  # now it is possible to disable the spinner and the bar at will.
NO_BAR = object()  # these markers represent the empty config.


def _spinner_input_factory(default):
    return __style_input_factory(SPINNERS, spinners, 'inner_spinner_factory', default)


def _bar_input_factory():
    return __style_input_factory(BARS, bars, 'inner_bar_factory', NO_BAR)


def __style_input_factory(name_lookup, module_lookup, inner_name, default):
    def _input(x):
        return name_lookup(x) or func_lookup(x) or default

    name_lookup = __name_lookup_factory(name_lookup)
    func_lookup = __func_lookup_factory(module_lookup, inner_name)
    return _input


def __name_lookup_factory(name_lookup):
    def _input(x):
        if isinstance(x, str):
            return name_lookup.get(x)

    return _input


def __func_lookup_factory(module_lookup, inner_name):
    def _input(x):
        if isinstance(x, FunctionType):
            func_file, _ = os.path.splitext(module_lookup.__file__)
            if x.__code__.co_name == inner_name \
                    and os.path.splitext(x.__code__.co_filename)[0] == func_file:
                return x

    return _input


def _int_input_factory(lower, upper):
    def _input(x):
        if lower <= int(x) <= upper:
            return int(x)

    return _input


def _bool_input_factory():
    def _input(x):
        return bool(x)

    return _input


def _create_spinner_player(local_config):
    spinner = local_config['spinner']
    if spinner is NO_SPINNER:
        return repeat('')
    return spinner_player(spinner(local_config['spinner_length']))


def _create_bars(local_config):
    bar = local_config['bar']
    if bar is NO_BAR:
        obj = lambda p, end: None
        obj.unknown = obj
        return obj
    return bar(local_config['length'], local_config['unknown'])


CONFIG_VARS = dict(  # the ones the user can configure.
    length=_int_input_factory(3, 300),
    spinner=_spinner_input_factory(NO_SPINNER),  # accept empty.
    spinner_length=_int_input_factory(0, 100),
    bar=_bar_input_factory(),
    unknown=_spinner_input_factory(None),  # do not accept empty.
    force_tty=_bool_input_factory(),
    manual=_bool_input_factory(),
    enrich_print=_bool_input_factory(),
    title_length=_int_input_factory(0, 100),
    show_receipt_text=_bool_input_factory(),
)
ADDITIONAL_VARS = dict(  # dynamically generated ones.
    spinner_player=_create_spinner_player,
    bars=_create_bars,
)

Config = namedtuple('Config', tuple(CONFIG_VARS) + tuple(ADDITIONAL_VARS))


def create_config():
    def reset():
        """Resets global configuration to the default one."""
        set_global(  # this must have all available config vars.
            length=40,
            theme='smooth',  # includes spinner, bar and unknown.
            force_tty=False,
            manual=False,
            enrich_print=True,
            title_length=0,
            spinner_length=0,
            show_receipt_text=False,
        )

    def set_global(theme=None, **options):
        """Update the global configuration, to be used in subsequent alive bars.

        See Also:
            alive_progress#alive_bar(**options)

        """
        global_config.update(_parse(theme, options))

    def create_context(theme=None, **options):
        """Create an immutable copy of the current configuration, with optional customization."""
        local_config = {**global_config, **_parse(theme, options)}
        # noinspection PyArgumentList
        return Config(**{k: local_config[k] for k in CONFIG_VARS},
                      **{k: v(local_config) for k, v in ADDITIONAL_VARS.items()})

    def _parse(theme, options):
        """Validate and convert some configuration options."""

        def validator(key, value):
            try:
                result = CONFIG_VARS[key](value)
                if result is None:
                    raise ValueError
                return result
            except KeyError:
                raise ValueError(f'invalid config name: {key}')
            except Exception:
                raise ValueError(f'invalid config value: {key}={value!r}')

        if theme:
            if theme not in THEMES:
                raise ValueError(f'invalid theme name={theme}')
            swap = options
            options = dict(THEMES[theme])
            options.update(swap)
        return {k: validator(k, v) for k, v in options.items()}

    global_config = {}
    reset()

    create_context.set_global, create_context.reset = set_global, reset
    return create_context


config_handler = create_config()
