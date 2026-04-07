# OSRS Clicker

Native macOS app built with SwiftUI for creating, calibrating, and running OSRS click presets.

## Project Structure

- `OSRSClicker/OSRSClicker.xcodeproj`: Xcode project
- `OSRSClicker/App`: app entrypoint
- `OSRSClicker/Design`: shared theme values
- `OSRSClicker/Models`: preset and action models
- `OSRSClicker/Services`: automation, persistence, permissions, and window lookup
- `OSRSClicker/ViewModels`: app state orchestration
- `OSRSClicker/Views`: sidebar, builder, and runner UI

## Requirements

- macOS 14 or newer
- Xcode 16 or newer
- Accessibility permission enabled for automation

## Build And Run

1. Open `OSRSClicker/OSRSClicker.xcodeproj` in Xcode.
2. Select the `OSRSClicker` scheme.
3. Choose `My Mac`.
4. Use `Product > Clean Build Folder` after structural changes if Xcode cached an older build.
5. Press `Run`.

## First Launch

1. Create or select a preset.
2. Confirm `Owner Contains` matches your game client owner, usually `RuneLite`.
3. Use `Test Window Match` to verify the app can resolve the target window.
4. Add `Click` and `Wait` steps in the `Builder` tab.
5. Press `Calibrate Click`, move the mouse inside the matched game window, and press `F6`.
6. Use the `Runner` tab to start, pause, resume, or stop the preset.

## Preset Storage

Presets are stored locally in:

- `~/Library/Application Support/OSRSClicker/presets.json`

Rebuilding the app in Xcode does not remove saved presets.

## Distribution Notes

- Bundle identifier: `com.osrsclicker.macapp`
- Test the Accessibility permission flow outside Xcode before release
- Add an app icon and signing configuration before public distribution
- Notarize the app if you want a normal end-user install experience

## Installing An Unsigned Release

The current GitHub Releases publish **unsigned developer builds**.

That means macOS may block the app the first time you try to open it. Users can still install and run it with the steps below.

### 1. Download and extract the app

1. Download `OSRSClicker.app.zip` from the GitHub Release page.
2. Extract the zip.
3. Move `OSRSClicker.app` to `Applications` if you want.

### 2. Open the app for the first time

If macOS blocks the app:

1. Right-click `OSRSClicker.app`
2. Click `Open`
3. Click `Open` again in the warning dialog

If macOS still blocks it:

1. Open `System Settings`
2. Go to `Privacy & Security`
3. Scroll to the security warning near the bottom
4. Click `Open Anyway`
5. Try opening the app again

### 3. Grant Accessibility permission

The app needs `Accessibility` permission to control the mouse.

1. Open `System Settings`
2. Go to `Privacy & Security`
3. Open `Accessibility`
4. Enable `OSRS Clicker`

If the app does not appear immediately:

1. Launch the app once
2. Try a calibration or run action
3. Return to `Accessibility` and enable it there

### 4. First use inside the app

1. Create or select a preset
2. Confirm `Owner Contains` matches your game client, usually `RuneLite`
3. Use `Test Window Match`
4. Add `Click` and `Wait` steps
5. Use `Calibrate Click`
6. Press `F6` to save the click position
7. Run the preset from the `Runner` tab

## CI And Releases

- Pull requests to `main` and pushes to `main` run the CI build in GitHub Actions.
- Release tags must use semver format like `v0.1.0`.
- The tag version must match `MARKETING_VERSION` in `OSRSClicker.xcodeproj`.
- Pushing a valid tag creates a GitHub Release automatically with:
  - `OSRSClicker.app.zip`
  - `OSRSClicker.app.zip.sha256`
- The first release pipeline publishes unsigned developer artifacts. Signing and notarization can be added later without changing the tag flow.

## Release Steps

1. Update `MARKETING_VERSION` in `OSRSClicker/OSRSClicker.xcodeproj`.
2. Merge the release commit into `main`.
3. Create a tag such as `v0.1.0`.
4. Push the tag:
   - `git push origin v0.1.0`
5. Wait for the `Release` workflow to finish and publish the GitHub Release.
