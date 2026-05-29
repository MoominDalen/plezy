import SwiftUI

struct AddProductSheet: View {
    @EnvironmentObject private var appState: AppState
    @Environment(\.dismiss) private var dismiss

    @State private var name = ""
    @State private var url = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Add product").font(.title2.bold())
            TextField("Name", text: $name)
            TextField("John Lewis URL", text: $url)
            Text("Use a full product link containing /p…")
                .font(.caption)
                .foregroundStyle(.secondary)
            HStack {
                Spacer()
                Button("Cancel") { dismiss() }
                Button("Add") {
                    Task {
                        await appState.addProduct(
                            name: name.isEmpty ? "New product" : name,
                            url: url
                        )
                        dismiss()
                    }
                }
                .keyboardShortcut(.defaultAction)
                .disabled(url.isEmpty)
            }
        }
        .padding(24)
        .frame(width: 440)
    }
}

struct EditProductSheet: View {
    @EnvironmentObject private var appState: AppState
    @Environment(\.dismiss) private var dismiss

    let product: Product
    @State private var name: String
    @State private var url: String
    @State private var sku: String

    init(product: Product) {
        self.product = product
        _name = State(initialValue: product.name)
        _url = State(initialValue: product.url)
        _sku = State(initialValue: product.sku ?? "")
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Edit product").font(.title2.bold())
            TextField("Name", text: $name)
            TextField("URL", text: $url)
            TextField("SKU (optional)", text: $sku)
            HStack {
                Spacer()
                Button("Cancel") { dismiss() }
                Button("Save") {
                    Task {
                        await appState.saveProduct(product, name: name, url: url, sku: sku)
                        dismiss()
                    }
                }
                .keyboardShortcut(.defaultAction)
            }
        }
        .padding(24)
        .frame(width: 480)
    }
}
