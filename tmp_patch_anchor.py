"""
Update the anchor gate: for title_only articles with no summary,
anchor in title alone is sufficient (no summary to check for 2nd hit).
"""
from pathlib import Path

p = Path('/Users/alexdakers/meridian-server/meridian.html')
src = p.read_text()

OLD = """  // keywords[0] is the anchor term — the most specific, defining keyword.
  // An article must mention it as a whole word in title or summary to qualify.
  const anchorReg = kwRegs[0];

  const matchedArticles = articles.filter(a => {
    const title   = (a.title   || '').toLowerCase();
    const summary = (a.summary || '').toLowerCase();
    const tags    = (a.tags    || []).map(t => t.toLowerCase()).join(' ');
    const topic   = (a.topic   || '').toLowerCase();

    // Hard gate: anchor keyword must appear in title or summary
    if (!anchorReg.test(title) && !anchorReg.test(summary)) return false;

    // Then require 2+ total keyword hits in content (anchor already counts as 1)
    const contentHits = kwRegs.filter(r => r.test(title) || r.test(summary)).length;
    if (contentHits >= 2) return true;

    // Single hit (the anchor) + corroborating tag/topic match qualifies
    // for well-tagged articles with brief summaries
    return kwRegs.some(r => r.test(tags) || r.test(topic));
  });"""

NEW = """  // keywords[0] is the anchor term — the most specific, defining keyword.
  // An article must mention it as a whole word in title or summary to qualify.
  const anchorReg = kwRegs[0];

  const matchedArticles = articles.filter(a => {
    const title   = (a.title   || '').toLowerCase();
    const summary = (a.summary || '').toLowerCase();
    const tags    = (a.tags    || []).map(t => t.toLowerCase()).join(' ');
    const topic   = (a.topic   || '').toLowerCase();

    // Hard gate: anchor keyword must appear in title or summary
    if (!anchorReg.test(title) && !anchorReg.test(summary)) return false;

    // Title-only articles have no summary to provide a 2nd hit — if the anchor
    // appears in the title, that's sufficient (they'll be enriched eventually)
    if (!a.summary) return anchorReg.test(title);

    // For articles with summaries, require 2+ keyword hits in content
    const contentHits = kwRegs.filter(r => r.test(title) || r.test(summary)).length;
    if (contentHits >= 2) return true;

    // Single hit (the anchor) + corroborating tag/topic match qualifies
    // for well-tagged articles with brief summaries
    return kwRegs.some(r => r.test(tags) || r.test(topic));
  });"""

assert OLD in src, "OLD not found"
src = src.replace(OLD, NEW, 1)
p.write_text(src)
print("Patched OK")
