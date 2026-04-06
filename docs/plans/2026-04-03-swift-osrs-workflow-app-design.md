# Swift OSRS Workflow App Design

## Summary

Build a native macOS app in Swift and SwiftUI that replaces the current Python bot scripts with a preset-driven OSRS workflow tool. The app should focus on building and running repeatable action sequences for RuneLite using a polished interface, reliable macOS permissions handling, and safe runtime controls.

## Product Goals

- run on macOS as a fully native Swift app
- replace script-style commands with a visual preset editor
- support OSRS workflows without hard-coded panels like combat, magic, or fletching
- make mouse click automation the primary first-class workflow
- support save, duplicate, and delete preset management
- keep the system extensible for optional future actions such as key press

## Non-Goals For V1

- image recognition or combat state detection
- scripting branches or conditionals
- per-skill built-in workflow panels
- cloud sync or online accounts
- cross-platform support

## Core Product Model

The app centers on editable presets. A preset represents one runnable OSRS workflow and contains metadata plus an ordered list of steps.

Each preset should include:

- unique identifier
- user-facing name
- optional notes
- target window preferences
- loop mode
- ordered actions

Each action step should include:

- unique identifier
- user-facing label
- enabled state
- action kind
- timing configuration

## Supported Action Types

V1 should prioritize the smallest useful set:

- `click`
- `wait`

The architecture should leave room for optional future action kinds such as:

- `keyPress`
- `mouseMove`

### Click Action

The click action should support:

- left or right mouse button
- coordinate mode
- stored coordinates
- optional jitter values
- delay configuration

Coordinate modes:

- absolute screen coordinates
- RuneLite-window-relative coordinates

The default and recommended mode is window-relative so presets continue to work if the RuneLite window moves or resizes.

### Wait Action

The wait action should support:

- fixed duration
- randomized minimum and maximum duration

Randomized range should be the default timing mode for action delays, while fixed timing remains available.

## Execution Model

The runner should support:

- run once
- repeat a fixed number of times
- run until stopped

This keeps the first version powerful enough for typical OSRS loops without turning the app into a scripting system.

## Interface Design

The recommended app structure is a three-area layout:

- left sidebar for preset management
- main editor for preset settings and ordered action steps
- persistent run area for status, controls, and logs

### Sidebar

The sidebar should provide:

- preset list
- create preset
- duplicate preset
- delete preset
- last selection persistence across launches

### Main Editor

The main editor should show:

- preset title and notes
- target window settings
- loop mode settings
- ordered action list
- add action controls

Action rows should be easy to scan and easy to edit inline. Reordering should feel direct and tactile.

### Run Area

The run area should remain visible while editing and running. It should provide:

- current run state
- current preset name
- current action label
- current loop count
- start control
- stop control
- recent log lines

## Visual Direction

The app should feel like a polished Mac utility instead of a plain settings form.

Recommended visual language:

- warm dark graphite background
- brass or gold accents
- elevated card surfaces
- strong spacing and typography hierarchy
- large preset title treatment
- compact control chips for timing and action mode

The desired impression is a focused power tool for OSRS workflows on macOS.

## macOS Architecture

The UI should be decoupled from window capture and input execution. The app should be split into services with clear responsibilities.

### Recommended Services

- `PresetStore`
- `Runner`
- `WindowLocator`
- `CaptureService`
- `InputExecutor`
- `PermissionManager`

### Service Responsibilities

`PresetStore`

- load presets from disk
- save and autosave edits
- track selection state

`Runner`

- execute steps in order
- manage loop state
- publish current action and logs
- stop cleanly on user request or runtime errors

`WindowLocator`

- locate the RuneLite window
- resolve relative coordinates into screen coordinates
- validate target window availability

`CaptureService`

- capture current mouse position
- capture RuneLite-relative mouse position

`InputExecutor`

- synthesize mouse events
- leave space for future keyboard support

`PermissionManager`

- check accessibility permission
- detect other required permissions
- expose permission state to the UI

## Permissions And Safety

The app should verify prerequisites before starting a run.

Required runtime checks:

- accessibility permission for input automation
- target RuneLite window availability when using relative coordinates
- coordinate validity before each click execution

The app should stop with clear user-facing reasons when:

- permissions are missing
- RuneLite cannot be found
- coordinates cannot be resolved
- the user presses stop

Safety controls should include:

- prominent stop button
- clear status messaging
- optional `Esc` emergency stop if permission constraints allow it

## Persistence

Presets should be stored locally in JSON under the user Application Support directory.

The persistence layer should support:

- autosave
- preset create
- preset duplicate
- preset delete
- clean format ready for future import/export

## Recommended Scope For V1

Ship the first usable version with:

- native SwiftUI macOS shell
- preset CRUD
- click and wait steps
- absolute and RuneLite-relative capture
- fixed and random timing
- run once, repeat count, and run-until-stopped modes
- runtime logs
- permissions UX

Add `keyPress` after the first stable version.
