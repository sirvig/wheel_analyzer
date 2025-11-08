from django import template

register = template.Library()


@register.filter(name="lookup")
def lookup(dictionary, key):
    return dictionary.get(key)


@register.filter(name="split")
def split(value, delimiter):
    """Split a string by a delimiter."""
    return value.split(delimiter)


@register.filter
def dict_get(dictionary, key):
    """
    Get value from dictionary by key in template.

    Usage: {{ my_dict|dict_get:key_var }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.simple_tag
def check_good_options(option_list, intrinsic_value):
    """
    Check if any option in the list has strike <= intrinsic value.

    Args:
        option_list: List of option dictionaries
        intrinsic_value: Decimal intrinsic value or None

    Returns:
        bool: True if at least one option has strike <= IV
    """
    if intrinsic_value is None:
        return False

    for option in option_list:
        if option.get("strike", float("inf")) <= intrinsic_value:
            return True

    return False
