"""Raise the bar in getThemeArticles: require 2+ keyword hits across title+summary."""
from pathlib import Path

p = Path('/Users/alexdakers/meridian-server/meridian.html')
src = p.read_text()

OLD = """  const matchedArticles = articles.filter(a => {
    const title   = (a.title   || '').toLowerCase();
    const summary = (a.summary || '').toLowerCase();
    const tags    = (a.tags    || []).map(t => t.toLowerCase()).join(' ');
    const topic   = (a.topic   || '').toLowerCase();

    // Primary: keyword must appear as a whole word in title or summary
    const inContent = kwRegs.some(r => r.test(title) || r.test(summary));
    if (inContent) return true;

    // Fallback: whole-word match in tags or topic (but not the loose substring check)
    return kwRegs.some(r => r.test(tags) || r.test(topic));
  });"""

NEW = """  const matchedArticles = articles.filter(a => {
    const title   = (a.title   || '').toLowerCase();
    const summary = (a.summary || '').toLowerCase();
    const tags    = (a.tags    || []).map(t => t.toLowerCase()).join(' ');
    const topic   = (a.topic   || '').toLowerCase();

    // Count whole-word keyword hits across title + summary (primary signal)
    const contentHits = kwRegs.filter(r => r.test(title) || r.test(summary)).length;

    // Require 2+ hits in content — eliminates articles that only incidentally
    // mention a single broad keyword like 'military' or 'geopolitics'
    if (contentHits >= 2) return true;

    // Single content hit + corroborating tag/topic match also qualifies
    // (catches well-tagged articles where the summary is brief)
    if (contentHits === 1) {
      return kwRegs.some(r => r.test(tags) || r.test(topic));
    }

    return false;
  });"""

assert OLD in src, "OLD not found"
src = src.replace(OLD, NEW, 1)
p.write_text(src)
print("Patched OK")
