## What's New in v2.4.9

### Bug Fixes

1. **Linux AppImage build fixed** — `build_linux.py` had three bugs preventing a working release build: `appimagetool` was invoked by bare filename (resolved via `$PATH` instead of the working directory, always failing with `FileNotFoundError`), the generated `.desktop` file's `Version` key held the app version instead of the required desktop-entry-spec version, and the referenced icon file was never actually written. The Linux build is now re-enabled in the tag-triggered release workflow, so `v*` tags produce both Windows and Linux release artifacts.
