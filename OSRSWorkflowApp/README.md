# OSRS Clicker

Native macOS SwiftUI app for building and running OSRS click presets with click and wait actions.

## Requirements

- macOS
- Xcode installed
- Accessibility permission enabled when testing automation

## Build And Run In Xcode

1. Install the full Xcode app.
2. Open `OSRSWorkflowApp/OSRSWorkflowApp.xcodeproj` in Xcode.
3. Select the `OSRSWorkflowApp` scheme.
4. Choose `My Mac`.
5. Use `Product > Clean Build Folder` if you changed app structure or Xcode cached an old build.
6. Press `Run`.

## First Launch

1. Open the app.
2. Create or select a preset.
3. Grant Accessibility permission when requested.
4. Set `Owner Contains` to your RuneLite window owner if needed.
5. Use `Test Window Match` to confirm the app can find the game window.
6. Add `Click` and `Wait` steps, calibrate clicks, then run the preset.

## What Is Included

- preset sidebar
- preset CRUD with Builder and Runner tabs
- responsive click and wait action editor
- collapsible action cards
- local JSON persistence in Application Support
- run panel with logs and runtime counter
- import/export for preset backups
- pause/resume controls in the runner
- macOS Accessibility prompt

## Preset Storage

Presets are stored locally in the user's Application Support folder. Rebuilding the app in Xcode does not delete saved presets.

Current storage file:

- `~/Library/Application Support/OSRSWorkflowApp/presets.json`

## Distribution Notes

If you want to distribute this app to other macOS users, the codebase is close to publishable, but you should still do a short release pass first:

- replace the personal bundle identifier with a neutral one
- verify the app name, icon, and signing settings
- test import/export on a clean macOS account
- test Accessibility permission flow outside Xcode
- sign and notarize the app if you want normal end-user installation

## Current Scope

This first Swift version includes the editor and a basic automation runner for click and wait steps. The preferred project entrypoint is the Xcode project, not the Swift package, because the app target now includes a real macOS bundle identifier for cleaner indexing and app execution in Xcode.
