from django import template

register = template.Library()


@register.filter(name="lookup")
def lookup(dictionary, key):
    return dictionary.get(key)


@register.filter(name="split")
def split(value, delimiter):
    """Split a string by a delimiter."""
    return value.split(delimiter)
