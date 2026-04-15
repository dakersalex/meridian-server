import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

# ── Fix 1: Only scrape latest issue, skip if unchanged ────────────────────
old_issue_block = (
    '                # 2. Two most recent issues (discovered dynamically)\n'
    '                issue_urls = self._discover_issues(page)\n'
    '                for issue_url in issue_urls:\n'
    '                    issue_arts = self._scrape_page(page, issue_url, seen, "issue")\n'
    '                    articles.extend(issue_arts)\n'
    '                    log.info("FA: issue %s — %d new" % (issue_url, len(issue_arts)))\n'
)
new_issue_block = (
    '                # 2. Latest issue only — skip if same as last scrape\n'
    '                latest_issue = self._discover_latest_issue(page)\n'
    '                if latest_issue:\n'
    '                    with sqlite3.connect(DB_PATH) as _icx:\n'
    '                        _last_issue = _icx.execute(\n'
    '                            "SELECT value FROM kt_meta WHERE key=\'fa_last_issue_url\'"\n'
    '                        ).fetchone()\n'
    '                    if _last_issue and _last_issue[0] == latest_issue:\n'
    '                        log.info("FA: issue unchanged (%s) — skipping" % latest_issue)\n'
    '                    else:\n'
    '                        issue_arts = self._scrape_page(page, latest_issue, seen, "issue")\n'
    '                        articles.extend(issue_arts)\n'
    '                        log.info("FA: issue %s — %d new" % (latest_issue, len(issue_arts)))\n'
    '                        with sqlite3.connect(DB_PATH) as _icx:\n'
    '                            _icx.execute(\n'
    '                                "INSERT OR REPLACE INTO kt_meta (key, value) VALUES (\'fa_last_issue_url\', ?)"\n'
    '                                , (latest_issue,))\n'
)
assert old_issue_block in content, "Issue block not found"
content = content.replace(old_issue_block, new_issue_block, 1)
print("Fix 1 (single issue, skip if unchanged): applied")

# ── Fix 2: Replace _discover_issues with _discover_latest_issue ───────────
old_discover = (
    '    def _discover_issues(self, page):\n'
    '        """Discover the two most recent issue URLs from the /issues landing page."""\n'
    '        try:\n'
    '            page.goto(self.ISSUES_URL, wait_until="domcontentloaded", timeout=30000)\n'
    '            page.wait_for_timeout(2000)\n'
    '            from bs4 import BeautifulSoup as _BS\n'
    '            soup = _BS(page.content(), "html.parser")\n'
    '            seen_urls = []\n'
    '            for a in soup.select("a[href]"):\n'
    '                href = a.get("href", "")\n'
    '                if "/issues/20" in href and href not in seen_urls:\n'
    '                    seen_urls.append(href)\n'
    '                if len(seen_urls) >= 2:\n'
    '                    break\n'
    '            if seen_urls:\n'
    '                log.info("FA: discovered issues: %s" % seen_urls)\n'
    '                return [self.BASE + u if u.startswith("/") else u for u in seen_urls]\n'
    '        except Exception as e:\n'
    '            log.warning("FA: issue discovery failed: %s" % e)\n'
    '        # Fallback to known recent issues\n'
    '        return [self.BASE + "/issues/2026/105/2", self.BASE + "/issues/2026/105/1"]\n'
)
new_discover = (
    '    def _discover_latest_issue(self, page):\n'
    '        """Discover the single most recent issue URL from the /issues landing page."""\n'
    '        try:\n'
    '            page.goto(self.ISSUES_URL, wait_until="domcontentloaded", timeout=30000)\n'
    '            page.wait_for_timeout(2000)\n'
    '            from bs4 import BeautifulSoup as _BS\n'
    '            soup = _BS(page.content(), "html.parser")\n'
    '            for a in soup.select("a[href]"):\n'
    '                href = a.get("href", "")\n'
    '                if "/issues/20" in href:\n'
    '                    url = self.BASE + href if href.startswith("/") else href\n'
    '                    log.info("FA: latest issue: %s" % url)\n'
    '                    return url\n'
    '        except Exception as e:\n'
    '            log.warning("FA: issue discovery failed: %s" % e)\n'
    '        # Fallback\n'
    '        return self.BASE + "/issues/2026/105/2"\n'
)
assert old_discover in content, "Discover method not found"
content = content.replace(old_discover, new_discover, 1)
print("Fix 2 (_discover_latest_issue): applied")

ast.parse(content)
print("Syntax OK")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
