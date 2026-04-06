# Swift OSRS Workflow App Implementation Plan

## Goal

Implement a native SwiftUI macOS app that lets the user build OSRS presets from ordered click and wait actions, save those presets locally, and run them safely against RuneLite.

## Delivery Strategy

Build the app in vertical slices so there is a working product early. Each phase should produce a testable milestone instead of leaving most value until the end.

## Phase 1: App Skeleton And Data Model

### Objectives

- create the macOS SwiftUI app target
- define the core domain models
- establish local persistence
- render the main three-area layout

### Tasks

- scaffold a native SwiftUI macOS app in a new `macos_app` or `OSRSWorkflowApp` folder
- define `Preset`, `ActionStep`, `ActionKind`, `LoopMode`, `TimingMode`, and coordinate model types
- implement JSON encoding and decoding
- implement `PresetStore` backed by Application Support
- persist the selected preset id
- build the base sidebar, editor shell, and run bar

### Exit Criteria

- app launches on macOS
- user can create, rename, duplicate, and delete presets
- presets persist across relaunch
- UI layout matches the approved structure

## Phase 2: Preset Editor And Action Builder

### Objectives

- make presets editable
- support ordered click and wait actions
- keep editing quick and visual

### Tasks

- build preset detail editor for name, notes, and loop mode
- build action list with add, remove, toggle enabled, and reorder support
- add click action editor with button type, coordinate mode, coordinate display, and jitter fields
- add wait action editor with fixed and random interval modes
- create compact timing chips and summary text for each step
- autosave edits through `PresetStore`

### Exit Criteria

- user can fully define a preset without touching files
- action rows are reorderable and editable inline
- click and wait actions serialize correctly

## Phase 3: Window Resolution And Position Capture

### Objectives

- support current cursor capture
- support RuneLite-relative capture
- validate target window presence

### Tasks

- implement `WindowLocator` using Quartz window APIs
- detect the RuneLite window by owner/title rules
- translate screen points to RuneLite-relative coordinates
- translate RuneLite-relative coordinates back to screen points
- implement `CaptureService` for absolute capture
- implement `CaptureService` for RuneLite-relative capture
- surface capture failures in the UI

### Exit Criteria

- user can press a capture button and store absolute coordinates
- user can press a capture button and store RuneLite-relative coordinates
- relative coordinates resolve correctly after window movement or resize

## Phase 4: Permissions And Execution Engine

### Objectives

- safely run presets
- expose clear permission state
- make stop behavior reliable

### Tasks

- implement `PermissionManager` for Accessibility checks
- add permission onboarding and status banners
- implement `InputExecutor` for mouse movement and click injection
- implement `Runner` as an observable service with background execution
- support run once, repeat count, and run-until-stopped modes
- add structured log events and current-step reporting
- stop the run cleanly on errors, missing window, or user stop

### Exit Criteria

- app can execute click and wait presets successfully
- run state is always visible in the UI
- stop button works consistently
- failure reasons are shown to the user instead of only logging internally

## Phase 5: Interface Polish

### Objectives

- make the tool feel production-ready
- improve editing speed and scanability

### Tasks

- apply the dark graphite and brass visual system
- refine cards, spacing, and hierarchy
- add a stronger preset title area
- add action icons, chips, and subtle hover states
- polish the persistent run bar and recent log panel
- improve empty states for no presets and no actions

### Exit Criteria

- interface feels intentional and cohesive
- primary actions are easy to discover
- common editing tasks are fast

## Phase 6: Validation And Packaging

### Objectives

- reduce regressions
- confirm the app works on the target MacBook environment

### Tasks

- add unit tests for model encoding, timing rules, and coordinate conversion
- add integration tests for `PresetStore`
- manually test capture and runtime behavior against RuneLite on macOS
- verify Accessibility guidance on a clean setup
- document app structure and local run instructions

### Exit Criteria

- core models and persistence are covered by tests
- main runtime flows are manually validated
- repo contains clear instructions for building the app

## Suggested Initial File Structure

Recommended app structure:

- `OSRSWorkflowApp/App/`
- `OSRSWorkflowApp/Models/`
- `OSRSWorkflowApp/Services/`
- `OSRSWorkflowApp/ViewModels/`
- `OSRSWorkflowApp/Views/`
- `OSRSWorkflowApp/Design/`
- `OSRSWorkflowApp/Resources/`
- `OSRSWorkflowAppTests/`

## Recommended Build Order

1. create the SwiftUI macOS app shell
2. implement models and persistence
3. build the preset editor and action list
4. add RuneLite window resolution and capture
5. add the execution runner and permissions handling
6. polish the interface and validate on-device

## Risks

- Quartz event injection and permission behavior can be finicky on macOS
- relative coordinate logic can drift if window resolution assumptions are wrong
- it is easy for the UI to become form-heavy without deliberate design work
- global emergency stop support may require careful permission handling

## Risk Mitigations

- keep execution services separate from the UI for easier testing
- test capture and coordinate transforms early, before building deeper runtime logic
- ship click and wait first, then expand
- keep logs visible in the interface during all runtime phases

## Post-V1 Extensions

- optional `keyPress` action
- import and export presets
- preset folders or tags
- richer target window rules
- optional mouse move action
