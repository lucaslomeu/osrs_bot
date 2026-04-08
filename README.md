# OSRS Clicker

Native macOS preset clicker for OSRS with reusable click and wait workflows.

## Download

Download the latest built app from the repository `Releases` page:

- `OSRSClicker.app.zip`

## Install

1. Download `OSRSClicker.app.zip`
2. Extract the zip
3. Move `OSRSClicker.app` to `Applications` if you want

## First Open

Because the current release is an **unsigned developer build**, macOS may block it the first time.

If that happens:

1. Right-click `OSRSClicker.app`
2. Click `Open`
3. Click `Open` again in the warning dialog

If macOS still blocks the app:

1. Open `System Settings`
2. Go to `Privacy & Security`
3. Scroll down to the security warning
4. Click `Open Anyway`
5. Try opening the app again

## Accessibility Permission

The app needs `Accessibility` permission to control the mouse.

1. Open `System Settings`
2. Go to `Privacy & Security`
3. Open `Accessibility`
4. Enable `OSRS Clicker`

If the app does not appear immediately:

1. Launch the app once
2. Try a calibration or run action
3. Return to `Accessibility` and enable it there

## Quick Start

1. Launch the app
2. Confirm `Owner Contains` matches your game client, usually `RuneLite`
3. Click `Test Window Match`
4. Add `Click` and `Wait` steps
5. Click `Calibrate Click`
6. Move the mouse to the target point and press `F6`
7. Run the preset from the `Runner` tab

## Preset Storage

Presets are stored locally at:

- `~/Library/Application Support/OSRSClicker/presets.json`

## Note

Current GitHub Releases are unsigned developer builds. They are usable, but macOS may require extra confirmation before opening the app.
