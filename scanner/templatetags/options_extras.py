import logging
from django import template

register = template.Library()
logger = logging.getLogger(__name__)


@register.filter(name="lookup")
def lookup(dictionary, key):
    """
    Lookup a key in a dictionary.

    Returns None if dictionary is None or not a dict.
    """
    if dictionary is None:
        return None
    if not isinstance(dictionary, dict):
        logger.warning(f"lookup received non-dict type: {type(dictionary).__name__}")
        return None
    return dictionary.get(key)


@register.filter(name="split")
def split(value, delimiter):
    """Split a string by a delimiter."""
    return value.split(delimiter)


@register.filter
def dict_get(dictionary, key):
    """
    Get value from dictionary by key in template.

    Safely handles non-dict inputs by returning None.

    Usage: {{ my_dict|dict_get:key_var }}

    Args:
        dictionary: Dictionary to look up key in (or any type)
        key: Key to look up

    Returns:
        Value from dictionary, or None if dictionary is invalid or key not found
    """
    if dictionary is None:
        return None

    # Defensive: ensure dictionary is actually a dict
    if not isinstance(dictionary, dict):
        logger.warning(
            f"dict_get received non-dict type: {type(dictionary).__name__}. "
            f"Returning None to prevent AttributeError."
        )
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
