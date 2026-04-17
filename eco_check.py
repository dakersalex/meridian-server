import ast

with open('/Users/alexdakers/meridian-server/meridian.html', 'r') as f:
    content = f.read()

old = (
    "          const keyMap = {'ft':'Financial Times','economist':'The Economist','fa':'Foreign Affairs'};\n"
    "          Object.entries(lr).forEach(([k,v])=>{ if(keyMap[k]) lastRunBySource[keyMap[k]]=new Date(v).getTime(); });\n"
    "        } catch(e) {}\n"
    "        const scrapedSrc = ['Financial Times','The Economist','Foreign Affairs'];\n"
    "        if(scEl) scEl.innerHTML = scrapedSrc.map(s=>{\n"
    "          const d=lastRunBySource[s]?Math.round((Date.now()-lastRunBySource[s])/864e5):99;\n"
    "          return '<div style=\"display:flex;justify-content:space-between;align-items:center;font-size:11px;padding:2.5px 0\">'\n"
    "            +'<span style=\"color:#4a4a4a;font-weight:500\">'+srcShort[s]+'</span>'\n"
    "            +'<span style=\"font-weight:600;color:'+gC(d)+'\">'+gL(d)+'</span></div>';\n"
    "        }).join('');\n"
    "      })();"
)

new = (
    "          const keyMap = {'ft':'Financial Times','economist':'The Economist','fa':'Foreign Affairs'};\n"
    "          Object.entries(lr).forEach(([k,v])=>{ if(keyMap[k]) lastRunBySource[keyMap[k]]=new Date(v).getTime(); });\n"
    "          ecoCdpLive = lr.eco_cdp_live !== false; // undefined = assume OK\n"
    "        } catch(e) {}\n"
    "        const scrapedSrc = ['Financial Times','The Economist','Foreign Affairs'];\n"
    "        if(scEl) scEl.innerHTML = scrapedSrc.map(s=>{\n"
    "          const d=lastRunBySource[s]?Math.round((Date.now()-lastRunBySource[s])/864e5):99;\n"
    "          const cdpWarn = (s==='The Economist' && !ecoCdpLive) ? ' <span title=\"Chrome CDP port 9223 unreachable — Economist scraper will fail\" style=\"color:#c0392b;font-size:10px;cursor:help\">⚠ CDP down</span>' : '';\n"
    "          return '<div style=\"display:flex;justify-content:space-between;align-items:center;font-size:11px;padding:2.5px 0\">'\n"
    "            +'<span style=\"color:#4a4a4a;font-weight:500\">'+srcShort[s]+cdpWarn+'</span>'\n"
    "            +'<span style=\"font-weight:600;color:'+gC(d)+'\">'+gL(d)+'</span></div>';\n"
    "        }).join('');\n"
    "      })();"
)

assert old in content, "Pattern not found"
content = content.replace(old, new, 1)
print("CDP indicator added to LAST SCRAPED")

# Also need to declare ecoCdpLive before the async block
old_decl = "        let lastRunBySource = {};\n"
new_decl = "        let lastRunBySource = {}, ecoCdpLive = true;\n"
assert old_decl in content, "decl not found"
content = content.replace(old_decl, new_decl, 1)
print("ecoCdpLive declared")

count = content.count('<html lang')
assert count == 1
with open('/Users/alexdakers/meridian-server/meridian.html', 'w') as f:
    f.write(content)
print(f"Done. html lang: {count}")
