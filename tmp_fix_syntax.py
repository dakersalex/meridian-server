with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    src = f.read()

# Fix the system prompt multiline string with literal newlines
OLD_SYSTEM = """    const system = `You are an intelligence analyst producing a ${bgBriefType === 'short' ? 'concise' : 'comprehensive'} strategic intelligence brief.
Structure your response with these sections:
## Executive Summary
(2-3 sentences — the single most important insight)
## Key Developments
(4-6 themes as ### subheadings, each with 3-4 bullet points citing [Source, Date])
## Strategic Implications
(3 bullet points on what this means going forward)
${bgBriefType === 'full' ? '## Watch List
(2-3 items to monitor in coming days)
' : ''}
Always cite sources. Prioritise recent articles. ${guidance ? 'Incorporate this guidance: ' + guidance : ''}`;"""

NEW_SYSTEM = """    const sectionBreak = '\\n';
    const system = [
      `You are an intelligence analyst producing a ${bgBriefType === 'short' ? 'concise' : 'comprehensive'} strategic intelligence brief.`,
      'Structure your response with these sections:',
      '## Executive Summary',
      '(2-3 sentences — the single most important insight)',
      '## Key Developments',
      '(4-6 themes as ### subheadings, each with 3-4 bullet points citing [Source, Date])',
      '## Strategic Implications',
      '(3 bullet points on what this means going forward)',
      bgBriefType === 'full' ? '## Watch List\\n(2-3 items to monitor in coming days)' : '',
      `Always cite sources. Prioritise recent articles. ${guidance ? 'Incorporate this guidance: ' + guidance : ''}`
    ].filter(Boolean).join('\\n');"""

# Fix the .replace(/\n\n/g literal newlines  
OLD_REPLACE = """      .replace(/

/g, '</p><p>')"""

NEW_REPLACE = """      .replace(/\\n\\n/g, '</p><p>')"""

results = []
if OLD_SYSTEM in src:
    src = src.replace(OLD_SYSTEM, NEW_SYSTEM)
    results.append("Fix system prompt: OK")
else:
    results.append("Fix system prompt: FAILED — searching for context...")
    idx = src.find("You are an intelligence analyst producing")
    results.append(f"  Found at char {idx}, context: {repr(src[idx:idx+100])}")

if OLD_REPLACE in src:
    src = src.replace(OLD_REPLACE, NEW_REPLACE)
    results.append("Fix replace newlines: OK")
else:
    results.append("Fix replace newlines: FAILED")

with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(src)

for r in results:
    print(r)
