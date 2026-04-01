    w, h = img.size
    TITLE_REGION_END = min(110, h // 4)  # extended: some subtitle lines reach y=83+

    last_dark_y = 0
    for y in range(6, TITLE_REGION_END):
        px = _sample_row(img, y)
        # Use threshold 155 (not 130) to catch medium-grey italic subtitle text
        if sum(1 for p in px if max(p) < 155) >= 2:
            last_dark_y = y

    if last_dark_y == 0:
        return 0  # no title text found

    return last_dark_y + 2
