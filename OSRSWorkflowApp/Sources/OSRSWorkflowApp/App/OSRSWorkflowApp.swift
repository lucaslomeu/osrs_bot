import SwiftUI

@main
struct OSRSWorkflowMacApp: App {
    var body: some Scene {
        WindowGroup("OSRS Clicker") {
            ContentView()
                .frame(minWidth: 960, minHeight: 720)
        }
        .windowStyle(.hiddenTitleBar)
        .defaultSize(width: 1280, height: 860)
    }
}
