# haflati-studio

Renders Haflati's Instagram posts (stills, carousels, Reels) for the automated posting system.

- `studio/layouts.py` - the brand formats (statement, problem, chips, bilingual, hero, arch, photo_line, split, framed, reel)
- `studio/build.py` - turns a post spec from the weekly planner into a layout; enforces the approved photo library and headline limits
- `studio/render.py` - renders with headless Chromium (JPG) and ffmpeg (MP4), and fails any post whose text overflows or overlaps
- `assets/` - logo and approved photo library (Pexels, illustrative only); brand fonts are installed from @fontsource at build time
- `.github/workflows/render.yml` - run by Make; publishes files to GitHub Pages and reports back to Make

Run one spec locally: `python -m studio spec.json out`
