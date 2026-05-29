import SwiftUI

@main
struct StockWatchApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(appState)
                .frame(minWidth: 960, minHeight: 640)
        }
        .windowToolbarStyle(.unified)
        .commands {
            CommandGroup(replacing: .newItem) {}
        }
    }
}
