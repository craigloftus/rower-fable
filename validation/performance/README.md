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

## Earlier separate-body delivery checks

These measurements predate the shared June body. They remain regression history,
not acceptance evidence for the current shared-body exports.

The provisional detailed Ada was tested in the full river scene by substituting
its compressed GLB and matching candidate boat profile in headless Chromium.
`ada-candidate-full-scene.json` records the exact compressed asset hash. At native
DPR 2.625 it averaged 120.00 fps, 1.05 ms CPU and 0.93 ms GPU per frame over 59
complete one-second samples. This is desktop evidence, not a Pixel 8 thermal test,
and must be repeated after the final modelling pass.

`node scripts/compress-character.mjs input.glb output.glb` produces lossless
Meshopt delivery files. It verifies decoded attributes, rig, materials and
animation, plus triangle identity and winding. No quantization, decimation or
animation resampling is performed. That provisional Ada export shrank from 9.97 MB to
3.36 MB; matching native-DPR Three.js captures were pixel-identical. This reduces
download size, not decoded vertex count or GPU memory.

To profile a candidate without changing production assets, use the development
server and provide its GLB and source-specific pose module:

```sh
PROFILE_URL='http://127.0.0.1:5194/rower-fable/?perf=1' \
  PROFILE_CHARACTER=ada PROFILE_LABEL=ada-candidate-full-scene \
  PROFILE_ASSET=validation/characters/delivery/ada.glb \
  PROFILE_POSE_MODULE=/rower-fable/scripts/ada-fit.mjs \
  node scripts/profile-headless.mjs
```

The separate-body Kai also passed the full-scene run at native DPR 2.625 (`kai-final-full-scene.json`):
about 120 fps on the desktop capture, mean CPU 1.07 ms and GPU 0.91 ms,
about 360 draw calls, no browser errors. The delivery hash is
`c3791fa272c5ca7dddebf3f0ab7bb742a9c03d9173dbb3005e39bfcaf19374a4`.
Lossless delivery reduced its 7,738,832-byte source to 2,722,096 bytes;
46,288 character triangles were retained. The installed compressed file passed
all 1,201 native pose checks separately.

The separate-body Sol (`sol-final-full-scene.json`) measured about 120 fps,
mean CPU 1.12 ms and GPU 0.90 ms, with about 361 draw calls, native DPR 2.625,
and no browser errors. The report hashes the actual network response as
`0940c972493f9b01b8a2a8699c3c527b6cb8c77633afab7f5c21f6328ab5696c`.
Its 47,329 triangles are unchanged by compression: 7,803,340 → 3,368,640 bytes.
The installed compressed file passed all 1,201 native pose checks.

## Shared June-body cast — final installed assets

Headless Chromium tested each installed export in the production river scene,
with a 914 × 412 CSS viewport, DPR 2.625 and 2399 × 1081 drawing buffer. Each
run warmed up for 10 seconds and captured 59 complete one-second samples.
The GPU was Apple M1 Max through ANGLE Metal. The `*-shared-body.json` reports
hash the actual model response and match the installed manifest.

| Character | Triangles | Delivery size | Mean fps | Mean CPU | Mean GPU |
| --- | ---: | ---: | ---: | ---: | ---: |
| Kai | 34,758 | 2.37 MB | 120.00 | 1.15 ms | 0.97 ms |
| June | 45,777 | 3.27 MB | 120.00 | 1.18 ms | 1.01 ms |
| Sol | 36,919 | 2.48 MB | 119.69 | 1.15 ms | 0.91 ms |
| Ada | 40,755 | 2.65 MB | 120.00 | 1.25 ms | 0.97 ms |

All four runs had no browser errors, held the wake lock during rowing and
released it on reset. Portrait layout, report download and native resolution
with diagnostics closed also passed. These desktop regression measurements
do not establish sustained Pixel 8 frame rates or thermal behaviour.

The original illustration selector and reload persistence passed for all four
characters. Source builds reproduced all raw exports byte-for-byte from a
staged checkout without reconstruction caches. The final native validators
checked 1,201 poses per character; the source-defined collision scan checked
161 poses per character with zero detected arm/leg or arm/chest intersections.
