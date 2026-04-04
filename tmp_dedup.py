
path = '/Users/alexdakers/meridian-server/meridian.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the corruption point — the mangled doctype
corrupt_marker = '</div>TYPE html>'
corrupt_idx = content.find(corrupt_marker)

if corrupt_idx == -1:
    print('Corruption marker not found')
else:
    # Keep everything up to and including </div>\n\n</div>
    # The corrupt marker replaces what should just be </div>
    # So we keep up to corrupt_idx, replace with </div>, discard the rest
    # But we need the legitimate closing tags after the info-strip
    # The structure is: </div>\n\n  </div>\n\n</div>TYPE html>
    # Those three closing divs close: bottom-row, info-strip inner, info-strip outer
    # Find what's before the marker
    before = content[:corrupt_idx]
    
    # Now find the real end of the file — the last </html> before the corruption
    # which is already in `before` since the corruption is what duplicated it
    # Just close it cleanly
    clean_ending = '</div>\n<!-- KEY THEMES VIEW -->'
    
    # The file should end after the info-strip closing div then continue with key-themes
    # Find where the legitimate key-themes section would be after the corruption
    # The second copy starts at the <html lang="en"> after TYPE html>
    second_copy_start = content.find('<html lang="en">', corrupt_idx)
    # Find the last </html> in the file (end of second copy)
    last_html_close = content.rfind('</html>')
    
    # The legitimate content after the info-strip is in the SECOND copy
    # from <!-- KEY THEMES VIEW --> to the end
    kt_in_second = content.find('<!-- KEY THEMES VIEW -->', second_copy_start)
    real_end = content[kt_in_second:last_html_close + 7]
    
    # Reconstruct: first copy up to corruption + proper close of info-strip + rest of page
    fixed = before + '</div>\n' + real_end
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(fixed)
    
    print(f'Fixed: corruption at char {corrupt_idx}')
    print(f'Second copy started at: {second_copy_start}')
    print(f'KEY THEMES in second copy at: {kt_in_second}')
    print(f'Final file length: {len(fixed)}')
