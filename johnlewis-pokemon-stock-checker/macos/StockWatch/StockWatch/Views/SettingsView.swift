import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState
    @Environment(\.dismiss) private var dismiss

    @State private var apiURL = ""
    @State private var pollInterval = "2"
    @State private var telegramToken = ""
    @State private var telegramChatId = ""

    var body: some View {
        Form {
            Section("Backend") {
                TextField("API URL", text: $apiURL)
                Text("Run from project folder: `./run_api.sh`")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Section("Polling") {
                TextField("Interval (seconds)", text: $pollInterval)
            }
            Section("Telegram (optional)") {
                SecureField("Bot token", text: $telegramToken)
                TextField("Chat ID", text: $telegramChatId)
            }
        }
        .formStyle(.grouped)
        .frame(width: 480, height: 320)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button("Close") { dismiss() }
            }
            ToolbarItem(placement: .confirmationAction) {
                Button("Save") { Task { await save() } }
            }
        }
        .onAppear {
            apiURL = appState.apiBaseURL
            Task { await loadSettings() }
        }
    }

    private func loadSettings() async {
        let client = APIClient(baseURL: URL(string: appState.apiBaseURL)!)
        guard let settings = try? await client.fetchSettings() else { return }
        pollInterval = settings["poll_interval"] ?? settings["poll_interval_seconds"] ?? "2"
        telegramToken = settings["telegram_bot_token"] ?? ""
        telegramChatId = settings["telegram_chat_id"] ?? ""
    }

    private func save() async {
        appState.apiBaseURL = apiURL
        UserDefaults.standard.set(apiURL, forKey: "apiBaseURL")
        let client = APIClient(baseURL: URL(string: apiURL)!)
        var payload = SettingsPayload()
        payload.pollIntervalSeconds = Double(pollInterval)
        payload.telegramBotToken = telegramToken.isEmpty ? nil : telegramToken
        payload.telegramChatId = telegramChatId.isEmpty ? nil : telegramChatId
        _ = try? await client.saveSettings(payload)
        appState.bootstrap()
        dismiss()
    }
}
