import SwiftUI

@main
struct OSRSWorkflowMacApp: App {
    var body: some Scene {
        WindowGroup("OSRS Workflow") {
            ContentView()
                .frame(minWidth: 1240, minHeight: 780)
        }
        .windowStyle(.hiddenTitleBar)
        .defaultSize(width: 1440, height: 900)
    }
}
