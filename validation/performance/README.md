# Performance pass — 6 October 2026

The shipped configuration targets 120 fps while rowing and keeps **native device
pixel density**. No character geometry, rig, materials or water detail was reduced.
The setup/summary background uses 30 fps and hidden pages stop rendering.

## Current headless test

`headless-native.json` records 59 complete one-second buckets from a 60-second
capture window after ten seconds of warm-up. Chromium used the Mac's Apple M1 Max
GPU through ANGLE Metal, with a 914 × 412 CSS viewport at DPR 2.625. The drawing
buffer was 2399 × 1081. This represents phone-sized rendering, not Pixel 8 hardware.

| Measurement | Mean of one-second samples |
| --- | ---: |
| App rendering | 120.00 fps |
| Browser animation callbacks | 120.00 Hz |
| CPU work inside animation tick | 1.14 ms/frame |
| GPU timer | 0.93 ms/frame |
| Draw calls | 368/frame |
| Frame interval p95 | 9.18 ms |

The maximum measured CPU frame was 4.3 ms; maximum frame interval was 9.4 ms.
There were no reported long tasks or JavaScript errors. Wake lock remained held
throughout the sample and released on reset. JSON download, portrait layout and
native-resolution rendering without the diagnostics panel were checked.

`headless-production.json` verifies the production build: 119.92 fps, 1.10 ms
mean CPU work, 0.93 ms mean GPU work, and a 1.9 ms maximum CPU frame.
Screenshots and downloaded report copies sit beside each report. Run the check with:

```sh
# Start the app separately, then:
node scripts/profile-headless.mjs
# Or point to a running production preview:
PROFILE_URL='http://127.0.0.1:5177/rower-fable/?perf=1' \
  PROFILE_LABEL=headless-production node scripts/profile-headless.mjs
```

## Earlier measurements and rejected settings

The initial in-app browser baseline (`baseline.json`) and matched-resolution
batching pass (`batched-dpr2.json`) both rendered at 5120 × 2880. Static batching
reduced average draw calls from 1,019 to 326 and animation-tick CPU work from
3.45 to 1.60 ms. GPU timing varied from 3.51 to 4.27 ms; batching alone did not
improve that metric. Spatial batching renders a few more off-screen triangles
while reducing draw submissions. The triangle count averaged 122,801 vs 124,191.

The in-app browser ran near 30 fps. It was not suitable evidence of the scene's
maximum frame rate; normal headless Chromium subsequently delivered 120 fps.

`optimized-auto.json` and `character-hidden.json` are exploratory measurements
with a reduced drawing buffer. **That resolution policy was rejected and removed.**
The hidden-character pass removed about 45,762 triangles and 20 draws; its GPU
timings were noisy, so it does not establish a reliable isolated GPU cost for June.
The full character is retained.

The synchronous chunk builder produced 21.5–25 ms CPU spikes at 120 m boundaries.
Chunk construction now runs in a worker with transferable buffers and prefetching.
The native headless run measured 1.5–1.6 ms maximum animation-tick work around
those boundaries. Async message work is outside that CPU timer; frame intervals
and the long-task observer also cover scheduling delays.

`headless-native-unlocked.json` is an experimental Chromium run with vsync/frame
rate limiting disabled. It produced abnormal callback pacing (about 104 callbacks
but 52 rendered frames per second); those flags are not used by the app or the
repeatable test. It is not a display-performance measurement.

## Pixel 8 acceptance still required

On the actual Pixel 8, use Chrome over HTTPS with `?perf=1`. Confirm native DPR,
120 Hz browser callbacks and rendering near 120 fps during rowing; compare frame
times early and after 15 minutes. Record brightness, battery use and perceived
heat. The browser cannot provide a reliable phone temperature measurement here.
Keep the screen untouched beyond auto-lock, through rest, then switch away/back
and check that **Screen awake** returns. Save the report if Chrome rejects or
releases the lock. The report includes its actual status and error history.
