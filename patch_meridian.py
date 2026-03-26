#!/usr/bin/env python3
"""
Patches meridian.html to save Foreign Affairs PDF articles to Flask (meridian.db)
instead of only localStorage.

Run from ~/meridian-server/:
    python3 patch_meridian.py
"""

import re
from pathlib import Path

HTML_PATH = Path(__file__).parent / "meridian.html"

OLD_FUNC = """function savePDFArticles(){
  const selected=pdfArticles.filter((_,i)=>document.getElementById('include-'+i)?.checked);
  if(!selected.length){toast('No essays selected');return;}

  setStep('save','active');

  selected.forEach(art=>{
    const article={
      id:'fa_'+Date.now()+'_'+Math.random().toString(36).slice(2,7),
      ts:Date.now(),
      source:'Foreign Affairs',
      url:'',
      title:art.title,
      author:art.author||'',
      summary:art.summary||'',
      fullSummary:art.fullSummary||'',
      keyPoints:art.keyPoints||[],
      tags:art.tags||[],
      topic:'',
      folder:'',
    };
    articles.unshift(article);
    if(art.suggestedFolder&&art.suggestedFolder!=='null'){
      pendingSuggestions[article.id]=art.suggestedFolder;
    }
  });

  setStep('save','done');
  saveAll();
  toast(`Saved ${selected.length} essay${selected.length>1?'s':''} from Foreign Affairs`);
  closeModal();"""

NEW_FUNC = """async function savePDFArticles(){
  const selected=pdfArticles.filter((_,i)=>document.getElementById('include-'+i)?.checked);
  if(!selected.length){toast('No essays selected');return;}

  setStep('save','active');

  let savedCount=0;
  for(const art of selected){
    const article={
      id:'fa_'+Date.now()+'_'+Math.random().toString(36).slice(2,7),
      ts:Date.now(),
      source:'Foreign Affairs',
      url:'',
      title:art.title,
      author:art.author||'',
      summary:art.summary||'',
      fullSummary:art.fullSummary||'',
      keyPoints:art.keyPoints||[],
      tags:art.tags||[],
      topic:art.suggestedFolder&&art.suggestedFolder!=='null'?art.suggestedFolder:'',
      folder:'',
    };

    // Save to Flask backend (meridian.db) if server is online
    if(serverOnline){
      try{
        const resp=await fetch(SERVER+'/api/articles',{
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify(article)
        });
        if(resp.ok){
          savedCount++;
          log('Saved to server: '+article.title);
        } else {
          console.warn('Server save failed for: '+article.title);
          // Fall back to localStorage
          articles.unshift(article);
          if(article.topic){pendingSuggestions[article.id]=article.topic;}
        }
      }catch(err){
        console.warn('Server unreachable, saving locally: '+err);
        articles.unshift(article);
        if(article.topic){pendingSuggestions[article.id]=article.topic;}
      }
    } else {
      // Server offline — save to localStorage only
      articles.unshift(article);
      if(article.topic){pendingSuggestions[article.id]=article.topic;}
    }
  }

  setStep('save','done');
  saveAll();

  // Reload articles from server so the new ones appear immediately
  if(serverOnline){
    try{
      const r=await fetch(SERVER+'/api/articles?limit=500');
      const data=await r.json();
      if(data.articles){articles=data.articles;}
    }catch(e){}
  }

  renderArticles();
  toast(`Saved ${selected.length} essay${selected.length>1?'s':''} from Foreign Affairs`);
  closeModal();"""

def patch():
    content = HTML_PATH.read_text(encoding='utf-8')

    if OLD_FUNC not in content:
        print("❌  Could not find the original savePDFArticles function.")
        print("   The HTML may have already been patched, or the function differs slightly.")
        print("   Check meridian.html manually around line 749.")
        return False

    patched = content.replace(OLD_FUNC, NEW_FUNC, 1)
    HTML_PATH.write_text(patched, encoding='utf-8')
    print(f"✅  meridian.html patched successfully ({HTML_PATH})")
    print("   savePDFArticles now saves to Flask (meridian.db) with localStorage fallback.")
    return True

if __name__ == "__main__":
    patch()
