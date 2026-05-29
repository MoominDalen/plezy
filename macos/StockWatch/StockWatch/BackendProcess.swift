import Foundation


/// Launches the bundled PyInstaller backend inside StockWatch.app.
@MainActor
final class BackendProcess: ObservableObject {
    @Published private(set) var isRunning = false
    @Published private(set) var lastError: String?

    private var process: Process?

    var dataDirectory: URL {
        let base = FileManager.default.urls(
            for: .applicationSupportDirectory,
            in: .userDomainMask
        ).first!
        return base.appendingPathComponent("StockWatch/data", isDirectory: true)
    }

    func startIfNeeded() {
        guard !isRunning else { return }
        guard let executable = locateBackendExecutable() else {
            lastError = "Bundled backend not found. Reinstall StockWatch from the DMG."
            return
        }

        try? FileManager.default.createDirectory(
            at: dataDirectory,
            withIntermediateDirectories: true
        )

        let task = Process()
        task.executableURL = executable
        task.currentDirectoryURL = executable.deletingLastPathComponent()
        var env = ProcessInfo.processInfo.environment
        env["DATA_DIR"] = dataDirectory.path
        env["API_HOST"] = "127.0.0.1"
        env["API_PORT"] = "8765"
        task.environment = env
        task.standardOutput = FileHandle.nullDevice
        task.standardError = FileHandle.nullDevice
        task.terminationHandler = { [weak self] _ in
            Task { @MainActor in
                self?.isRunning = false
            }
        }

        do {
            try task.run()
            process = task
            isRunning = true
            lastError = nil
        } catch {
            lastError = error.localizedDescription
            isRunning = false
        }
    }

    func stop() {
        process?.terminate()
        process = nil
        isRunning = false
    }

    private func locateBackendExecutable() -> URL? {
        // Shipped layout: Contents/Resources/backend/stockwatch-backend
        if let url = Bundle.main.url(
            forResource: "stockwatch-backend",
            withExtension: nil,
            subdirectory: "backend"
        ), FileManager.default.isExecutableFile(atPath: url.path) {
            return url
        }
        // Dev fallback: repo dist folder next to project
        let dev = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("dist/stockwatch-backend/stockwatch-backend")
        if FileManager.default.isExecutableFile(atPath: dev.path) {
            return dev
        }
        return nil
    }

    deinit {
        stop()
    }
}
