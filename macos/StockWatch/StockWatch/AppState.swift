import Foundation
import SwiftUI

@MainActor
final class AppState: ObservableObject {
    @Published var products: [Product] = []
    @Published var pokemonCenter = PokemonCenterStatus(
        queueActive: false,
        status: "unknown",
        detail: nil,
        checkedAt: nil
    )
    @Published var isBackendOnline = false
    @Published var isLoading = false
    @Published var isScanning = false
    @Published var errorMessage: String?
    @Published var filter: StockFilter = .all
    @Published var apiBaseURL: String = UserDefaults.standard.string(forKey: "apiBaseURL")
        ?? "http://127.0.0.1:8765"

    private var client: APIClient { APIClient(baseURL: URL(string: apiBaseURL)!) }
    private var webSocketTask: Task<Void, Never>?

    func bootstrap() {
        webSocketTask?.cancel()
        webSocketTask = Task { await listenWebSocket() }
        Task { await refreshAll() }
    }

    func refreshAll() async {
        isLoading = true
        defer { isLoading = false }
        do {
            isBackendOnline = try await client.health()
            products = try await client.fetchProducts()
            pokemonCenter = try await client.fetchPokemonCenter()
            errorMessage = nil
        } catch {
            isBackendOnline = false
            errorMessage = error.localizedDescription
        }
    }

    func scanJohnLewis() async {
        isScanning = true
        defer { isScanning = false }
        do {
            let result = try await client.scanJohnLewis()
            products = try await client.fetchProducts()
            errorMessage = "Found \(result.discovered) pokemon-tcg URLs"
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func addProduct(name: String, url: String) async {
        do {
            _ = try await client.createProduct(name: name, url: url)
            products = try await client.fetchProducts()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func deleteProduct(_ product: Product) async {
        do {
            try await client.deleteProduct(product.id)
            products.removeAll { $0.id == product.id }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func checkProduct(_ product: Product) async {
        do {
            let updated = try await client.checkProduct(product.id)
            if let idx = products.firstIndex(where: { $0.id == product.id }) {
                products[idx] = updated
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func saveProduct(_ product: Product, name: String, url: String, sku: String) async {
        var patch = APIClient.ProductPatch()
        patch.name = name
        patch.url = url
        patch.sku = sku.isEmpty ? nil : sku
        do {
            let updated = try await client.updateProduct(product.id, patch: patch)
            if let idx = products.firstIndex(where: { $0.id == product.id }) {
                products[idx] = updated
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func checkPokemonCenter() async {
        do {
            pokemonCenter = try await client.checkPokemonCenter()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    var filteredProducts: [Product] {
        switch filter {
        case .all: return products
        case .inStock: return products.filter(\.isInStock)
        case .outOfStock: return products.filter { $0.available == false }
        }
    }

    private func listenWebSocket() async {
        guard var components = URLComponents(string: apiBaseURL) else { return }
        components.scheme = (components.scheme == "https") ? "wss" : "ws"
        guard let wsURL = components.url?.appending(path: "ws") else { return }
        while !Task.isCancelled {
            do {
                let session = URLSession(configuration: .default)
                let socket = session.webSocketTask(with: wsURL)
                socket.resume()
                isBackendOnline = true
                while !Task.isCancelled {
                    let message = try await socket.receive()
                    if case .string(let text) = message,
                       let data = text.data(using: .utf8),
                       let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                       let type = json["type"] as? String {
                        await handleWS(type: type)
                    }
                }
            } catch {
                isBackendOnline = false
                try? await Task.sleep(nanoseconds: 2_000_000_000)
            }
        }
    }

    private func handleWS(type: String) async {
        switch type {
        case "product_updated", "scan_complete", "tick":
            await refreshAll()
        case "pokemoncenter_updated":
            if let pc = try? await client.fetchPokemonCenter() {
                pokemonCenter = pc
            }
        default:
            break
        }
    }
}

