import SwiftUI

@main
struct OSRSClickerApp: App {
    var body: some Scene {
        WindowGroup("OSRS Clicker") {
            ContentView()
                .frame(minWidth: 860, minHeight: 680)
        }
        .windowStyle(.hiddenTitleBar)
        .defaultSize(width: 1280, height: 860)
    }
}
