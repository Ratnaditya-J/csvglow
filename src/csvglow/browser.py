"""Open HTML file in the default browser."""

from __future__ import annotations

import pathlib
import webbrowser


def open_in_browser(html_path: str) -> None:
    """Open an HTML file in the user's default browser."""
    url = pathlib.Path(html_path).resolve().as_uri()
    webbrowser.open(url)
