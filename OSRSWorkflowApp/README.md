# OSRSWorkflowApp

Native macOS SwiftUI app for building and running OSRS presets with click and wait actions.

## Open In Xcode

1. Install the full Xcode app.
2. Open `OSRSWorkflowApp/OSRSWorkflowApp.xcodeproj` in Xcode.
3. Select the `OSRSWorkflowApp` scheme.
4. Choose `My Mac`.
5. Press `Run`.

## What Is Included

- preset sidebar
- preset CRUD
- click and wait action editor
- local JSON persistence in Application Support
- run bar with logs
- macOS Accessibility prompt

## Current Scope

This first Swift version includes the editor and a basic automation runner for click and wait steps. The preferred project entrypoint is the Xcode project, not the Swift package, because the app target now includes a real macOS bundle identifier for cleaner indexing and app execution in Xcode.
