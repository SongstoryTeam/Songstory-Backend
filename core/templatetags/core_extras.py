from django import template
from django.utils.http import urlencode

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


@register.simple_tag(takes_context=True)
def query_url(context, *, anchor: str = "", reset: str = "page", **changes) -> str:
    request = context["request"]
    params = request.GET.copy()
    for key in filter(None, reset.split(",")):
        params.pop(key, None)
    for key, value in changes.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    query = urlencode(params, doseq=True)
    suffix = f"#{anchor}" if anchor else ""
    return f"{request.path}?{query}{suffix}" if query else f"{request.path}{suffix}"
