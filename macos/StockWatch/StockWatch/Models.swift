import Foundation

struct Product: Identifiable, Codable, Hashable {
    let id: Int
    let source: String
    let name: String
    let url: String
    let sku: String?
    let imageUrl: String?
    let enabled: Bool
    let available: Bool?
    let statusMessage: String?
    let lastChecked: String?

    enum CodingKeys: String, CodingKey {
        case id, source, name, url, sku, enabled, available
        case imageUrl = "image_url"
        case statusMessage = "status_message"
        case lastChecked = "last_checked"
    }

    var isInStock: Bool { available == true }
}

struct PokemonCenterStatus: Codable {
    let queueActive: Bool
    let status: String
    let detail: String?
    let checkedAt: String?

    enum CodingKeys: String, CodingKey {
        case status, detail
        case queueActive = "queue_active"
        case checkedAt = "checked_at"
    }

    init(queueActive: Bool, status: String, detail: String?, checkedAt: String?) {
        self.queueActive = queueActive
        self.status = status
        self.detail = detail
        self.checkedAt = checkedAt
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        queueActive = (try? c.decode(Bool.self, forKey: .queueActive))
            ?? ((try? c.decode(Int.self, forKey: .queueActive)) == 1)
        status = (try? c.decode(String.self, forKey: .status)) ?? "unknown"
        detail = try? c.decode(String.self, forKey: .detail)
        checkedAt = try? c.decode(String.self, forKey: .checkedAt)
    }
}

struct ScanResult: Codable {
    let discovered: Int
    let products: [Product]
}

struct SettingsPayload: Codable {
    var pollIntervalSeconds: Double?
    var telegramBotToken: String?
    var telegramChatId: String?
    var telegramEnabled: Bool?

    enum CodingKeys: String, CodingKey {
        case pollIntervalSeconds = "poll_interval_seconds"
        case telegramBotToken = "telegram_bot_token"
        case telegramChatId = "telegram_chat_id"
        case telegramEnabled = "telegram_enabled"
    }
}

struct WSMessage: Codable {
    let type: String
}

enum StockFilter: String, CaseIterable, Identifiable {
    case all = "All"
    case inStock = "In stock"
    case outOfStock = "Out of stock"

    var id: String { rawValue }
}
