"""
ARCUS — CORS origin tests

The custom domain was missing from the allow-list, so every API call from
arcus-insights.com was blocked by the browser even when the backend was
healthy. These tests pin the origins the app is actually served from.
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest

from backend.main import ALLOWED_ORIGINS, ALLOWED_ORIGIN_REGEX


@pytest.mark.parametrize("origin", [
    "https://arcus-insights.com",       # custom domain
    "https://www.arcus-insights.com",
    "https://shreyas1504.github.io",    # GitHub Pages
    "http://localhost:8080",            # vite dev server
])
def test_served_origins_are_allowed(origin):
    assert origin in ALLOWED_ORIGINS


def test_origins_carry_no_trailing_slash():
    # A trailing slash silently never matches the browser's Origin header.
    assert not [o for o in ALLOWED_ORIGINS if o.endswith("/")]


def test_vercel_previews_match_the_regex():
    pattern = re.compile(ALLOWED_ORIGIN_REGEX)
    assert pattern.fullmatch("https://arcus-git-main-shreyas.vercel.app")


def test_regex_does_not_match_a_lookalike_domain():
    pattern = re.compile(ALLOWED_ORIGIN_REGEX)
    assert not pattern.fullmatch("https://vercel.app.evil.com")
