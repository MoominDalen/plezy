import SwiftUI

@main
struct StockWatchApp: App {
    @StateObject private var appState = AppState()
    @StateObject private var backend = BackendProcess()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(appState)
                .environmentObject(backend)
                .frame(minWidth: 960, minHeight: 640)
                .task {
                    backend.startIfNeeded()
                    await waitForBackend(appState: appState)
                }
        }
        .windowToolbarStyle(.unified)
        .commands {
            CommandGroup(replacing: .newItem) {}
        }
    }

    private func waitForBackend(appState: AppState) async {
        for _ in 0..<30 {
            await appState.refreshAll()
            if appState.isBackendOnline { return }
            try? await Task.sleep(nanoseconds: 500_000_000)
        }
    }
}
