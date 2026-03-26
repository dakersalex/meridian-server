#!/usr/bin/env python3
"""
Patches meridian.html to route all Anthropic API calls through the Flask proxy
at /api/claude instead of calling api.anthropic.com directly.

Run from ~/meridian-server/:
    python3 patch_api_proxy.py
"""

from pathlib import Path

HTML_PATH = Path(__file__).parent / "meridian.html"

def patch():
    content = HTML_PATH.read_text(encoding='utf-8')

    original = content

    # Replace all direct Anthropic API calls with the Flask proxy
    content = content.replace(
        "fetch('https://api.anthropic.com/v1/messages',",
        "fetch(SERVER+'/api/claude',"
    )

    # Also handle any with double quotes
    content = content.replace(
        'fetch("https://api.anthropic.com/v1/messages",',
        'fetch(SERVER+"/api/claude",'
    )

    count = original.count("api.anthropic.com")
    if content == original:
        print("❌  No Anthropic API calls found to patch.")
        print("   Check meridian.html manually for fetch calls to api.anthropic.com")
        return False

    HTML_PATH.write_text(content, encoding='utf-8')
    print(f"✅  meridian.html patched — {count} Anthropic API call(s) now routed through Flask proxy.")
    return True

if __name__ == "__main__":
    patch()
