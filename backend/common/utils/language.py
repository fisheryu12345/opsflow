# -*- coding: utf-8 -*-
"""Shared language-detection utility.

Used by views and serializers to determine the request language.
Returns 'en' or 'zh' — suitable for both i18n message selection and
serializer field switching (name vs name_en).
"""


def get_request_lang(request) -> str:
    """Extract language preference from a DRF request.

    Checks query param `lang` first, then `X-Lang` header.
    Returns 'en' if the value starts with 'en', otherwise 'zh'.

    Usage:
        lang = get_request_lang(request)
        label = name_en if lang == 'en' else name
    """
    if not request:
        return 'zh'
    val = (
        request.query_params.get('lang', '')
        or request.META.get('HTTP_X_LANG', '')
    )
    if isinstance(val, str) and val.startswith('en'):
        return 'en'
    return 'zh'
