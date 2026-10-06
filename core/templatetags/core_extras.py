from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def nav_active(context, *url_names):
    match = getattr(context.get("request"), "resolver_match", None)
    if not match:
        return ""
    current = f"{match.namespace}:{match.url_name}" if match.namespace else match.url_name
    return "active" if current in url_names else ""


PLURAL_FORMS_COUNT = 3
FEW_ENDINGS = (2, 3, 4)
EXCLUDED_TEENS = range(11, 15)


@register.filter
def uk_plural(number, forms: str) -> str:
    one, few, many = forms.split(",")[:PLURAL_FORMS_COUNT]
    count = abs(int(number))
    if count % 100 in EXCLUDED_TEENS:
        return many
    if count % 10 == 1:
        return one
    if count % 10 in FEW_ENDINGS:
        return few
    return many
