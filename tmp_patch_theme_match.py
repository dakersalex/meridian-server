"""
Patch getThemeArticles() in meridian.html to use tighter keyword matching:
- Word-boundary regex matching (prevents 'war' matching 'softwar[e]')
- Require match in title OR summary (actual content), not just tags/topic
- Tags/topic still used but with word-boundary check
"""
from pathlib import Path

p = Path('/Users/alexdakers/meridian-server/meridian.html')
src = p.read_text()

OLD = '''function getThemeArticles(idx) {
  if (!ktThemes || idx === null) return [];
  const kws = (ktThemes[idx].keywords || []).map(k => k.toLowerCase());

  const matchedArticles = articles.filter(a => {
    const tags = (a.tags || []).map(t => t.toLowerCase());
    const topic = (a.topic || '').toLowerCase();
    const title = (a.title || '').toLowerCase();
    return kws.some(k =>
      tags.some(t => t.includes(k) || k.includes(t)) ||
      topic.includes(k) ||
      title.includes(k)
    );
  });'''

NEW = '''function getThemeArticles(idx) {
  if (!ktThemes || idx === null) return [];
  const kws = (ktThemes[idx].keywords || []).map(k => k.toLowerCase());

  // Word-boundary regex for each keyword — prevents 'war' matching 'software'
  // Multi-word keywords like 'Middle East' are matched as phrases
  const kwRegs = kws.map(k => new RegExp('\\\\b' + k.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&') + '\\\\b', 'i'));

  const matchedArticles = articles.filter(a => {
    const title   = (a.title   || '').toLowerCase();
    const summary = (a.summary || '').toLowerCase();
    const tags    = (a.tags    || []).map(t => t.toLowerCase()).join(' ');
    const topic   = (a.topic   || '').toLowerCase();

    // Primary: keyword must appear as a whole word in title or summary
    const inContent = kwRegs.some(r => r.test(title) || r.test(summary));
    if (inContent) return true;

    // Fallback: whole-word match in tags or topic (but not the loose substring check)
    return kwRegs.some(r => r.test(tags) || r.test(topic));
  });'''

assert OLD in src, f"OLD not found — check indentation"
src = src.replace(OLD, NEW, 1)
p.write_text(src)
print("Patched getThemeArticles OK")
