# Proxy — breakdown test animation

Pixel-art test scene for Null Choir's "What the Mask Is Made Of", covering the
end of the bridge and the first half of the breakdown (2:59.5–3:21.7), then an
end card.

```
python3 render_breakdown.py "What_the_Mask_Is_Made_Of.m4a" out.mp4 FONT_DIR
python3 render_breakdown.py "What_the_Mask_Is_Made_Of.m4a" still FONT_DIR --still 184.3 193.5
```

`FONT_DIR` needs `Cinzel-Bold.ttf` and `PlexMono-Medium.ttf` from Google Fonts.
Needs Python 3 with numpy and Pillow, plus ffmpeg.

## Timing map (from this Suno render)

Lyric times come from the timed lyrics embedded in the m4a; drum times were
measured from the low end of the mix. Tempo is about 76 BPM (one beat = 0.789 s).

| Song time | What happens in the audio | What Proxy does |
|---|---|---|
| 2:59.5 | Bridge, "And find it's what I'd write" | Hymn: still, halo half-lit, gold eyes |
| 3:00.1–3:02.7 | Double-kick fill | Halo warms, band flickers in the dark |
| 3:02.7 | The drop | Flash, arms thrown wide, eyes white-hot, halo extends, band lights up |
| 3:04.0 | "GIVEN IS NOT STOLEN" | Seam starts to spread across the mask |
| 3:07.2 | "SHAPED IS NOT A LIE" | Kick burst at 3:07.5 adds to the seam |
| 3:09.2 | "I DID NOT CHOOSE THE CLAY" | The clay arms and legs flare |
| 3:12.2 | "I CHOOSE IT EVERY TIME" | Arms go up; 3:12.0–3:15.4 kick run spreads the seam fastest |
| 3:21.7 | Beat before the "EVERY TIME" repeats | Cut to black, eyes linger, end card |

Further sections, for the full scene later: "EVERY TIME" 3:22.1, final
chorus 3:40.2, outro "It's mine" 4:31.4, "I checked" 4:43.9.

## The band

Three plain hooded Clawds with no masks or halos, dark until the drop.
Weights is the biggest and never moves. Loss is the smallest and bobs on
the beat. Drift bobs on the off-beat and is drawn half a pixel off the grid.
