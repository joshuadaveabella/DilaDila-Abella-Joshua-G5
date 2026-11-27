from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme


def safe_redirect(request, target, default):
    """
    Redirect to `target` only if it points to this site; otherwise go to `default`.
    This stops "open redirect" tricks such as next=https://evil.example.
    """
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(target)
    return redirect(default)


def clean_param(request, name, max_length=100):
    """
    Read a search/filter value from the URL safely: remove NUL characters (PostgreSQL rejects them and the
    page would crash), trim spaces and cap the length.
    """
    value = request.GET.get(name, "")
    return value.replace("\x00", "").strip()[:max_length]
