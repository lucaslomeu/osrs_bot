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
