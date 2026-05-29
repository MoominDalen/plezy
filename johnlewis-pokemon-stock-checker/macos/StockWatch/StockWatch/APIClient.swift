import Foundation

enum APIError: LocalizedError {
    case badURL
    case offline
    case http(Int)

    var errorDescription: String? {
        switch self {
        case .badURL: return "Invalid URL"
        case .offline: return "Backend offline — run ./run_api.sh"
        case .http(let code): return "HTTP \(code)"
        }
    }
}

final class APIClient {
    var baseURL: URL

    init(baseURL: URL = URL(string: "http://127.0.0.1:8765")!) {
        self.baseURL = baseURL
    }

    func health() async throws -> Bool {
        let (_, response) = try await URLSession.shared.data(from: baseURL.appending(path: "/health"))
        return (response as? HTTPURLResponse)?.statusCode == 200
    }

    func fetchProducts() async throws -> [Product] {
        try await get(path: "/products")
    }

    func createProduct(name: String, url: String, source: String = "johnlewis") async throws -> Product {
        struct Body: Encodable {
            let name, url, source: String
        }
        return try await post(path: "/products", body: Body(name: name, url: url, source: source))
    }

    func updateProduct(_ id: Int, patch: ProductPatch) async throws -> Product {
        try await put(path: "/products/\(id)", body: patch)
    }

    func deleteProduct(_ id: Int) async throws {
        var request = URLRequest(url: baseURL.appending(path: "/products/\(id)"))
        request.httpMethod = "DELETE"
        let (_, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw APIError.http((response as? HTTPURLResponse)?.statusCode ?? 0)
        }
    }

    func scanJohnLewis() async throws -> ScanResult {
        try await post(path: "/scan/johnlewis", body: EmptyBody())
    }

    func checkProduct(_ id: Int) async throws -> Product {
        try await post(path: "/products/\(id)/check", body: EmptyBody())
    }

    func fetchPokemonCenter() async throws -> PokemonCenterStatus {
        try await get(path: "/pokemoncenter")
    }

    func checkPokemonCenter() async throws -> PokemonCenterStatus {
        try await post(path: "/pokemoncenter/check", body: EmptyBody())
    }

    func fetchSettings() async throws -> [String: String] {
        try await get(path: "/settings")
    }

    func saveSettings(_ payload: SettingsPayload) async throws -> [String: String] {
        try await put(path: "/settings", body: payload)
    }

    private struct EmptyBody: Encodable {}

    struct ProductPatch: Encodable {
        var name: String?
        var url: String?
        var sku: String?
        var imageUrl: String?
        var enabled: Bool?

        enum CodingKeys: String, CodingKey {
            case name, url, sku, enabled
            case imageUrl = "image_url"
        }
    }

    private func get<T: Decodable>(path: String) async throws -> T {
        let (data, response) = try await URLSession.shared.data(from: baseURL.appending(path: path))
        try validate(response)
        return try JSONDecoder().decode(T.self, from: data)
    }

    private func post<T: Decodable, B: Encodable>(path: String, body: B) async throws -> T {
        var request = URLRequest(url: baseURL.appending(path: path))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(body)
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response)
        return try JSONDecoder().decode(T.self, from: data)
    }

    private func put<T: Decodable, B: Encodable>(path: String, body: B) async throws -> T {
        var request = URLRequest(url: baseURL.appending(path: path))
        request.httpMethod = "PUT"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(body)
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response)
        return try JSONDecoder().decode(T.self, from: data)
    }

    private func validate(_ response: URLResponse) throws {
        guard let http = response as? HTTPURLResponse else { throw APIError.offline }
        guard (200..<300).contains(http.statusCode) else { throw APIError.http(http.statusCode) }
    }
}
