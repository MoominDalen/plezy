import SwiftUI

struct RootView: View {
    @EnvironmentObject private var appState: AppState
    @State private var showAdd = false
    @State private var showSettings = false
    @State private var selectedProduct: Product?

    var body: some View {
        NavigationSplitView {
            sidebar
        } detail: {
            productGrid
        }
        .sheet(isPresented: $showAdd) {
            AddProductSheet()
        }
        .sheet(isPresented: $showSettings) {
            SettingsView()
        }
        .sheet(item: $selectedProduct) { product in
            EditProductSheet(product: product)
        }
        .onAppear { appState.bootstrap() }
        .navigationTitle("StockWatch")
    }

    private var sidebar: some View {
        List {
            Section("Status") {
                backendRow
                pokemonCenterRow
            }
            Section("Filters") {
                Picker("Show", selection: $appState.filter) {
                    ForEach(StockFilter.allCases) { f in
                        Text(f.rawValue).tag(f)
                    }
                }
                .pickerStyle(.radioGroup)
            }
            Section("Actions") {
                Button {
                    Task { await appState.scanJohnLewis() }
                } label: {
                    Label("Scan John Lewis (pokemon-tcg)", systemImage: "magnifyingglass.circle")
                }
                .disabled(appState.isScanning || !appState.isBackendOnline)

                Button { showAdd = true } label: {
                    Label("Add product URL", systemImage: "plus.circle")
                }
                Button { showSettings = true } label: {
                    Label("Settings", systemImage: "gearshape")
                }
            }
        }
        .listStyle(.sidebar)
        .frame(minWidth: 260)
    }

    private var backendRow: some View {
        HStack {
            Circle()
                .fill(appState.isBackendOnline ? Color.green : Color.red)
                .frame(width: 10, height: 10)
            Text(appState.isBackendOnline ? "Backend connected" : "Backend offline")
                .font(.subheadline)
        }
    }

    private var pokemonCenterRow: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Image(systemName: "flag.fill")
                    .foregroundStyle(.orange)
                Text("Pokemon Center UK")
                    .font(.headline)
            }
            HStack {
                Circle()
                    .fill(appState.pokemonCenter.queueActive ? Color.orange : Color.green)
                    .frame(width: 10, height: 10)
                Text(appState.pokemonCenter.queueActive ? "Queue active" : "No queue")
                    .font(.subheadline.weight(.semibold))
            }
            if let detail = appState.pokemonCenter.detail {
                Text(detail)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Link("Open en-gb site", destination: URL(string: "https://www.pokemoncenter.com/en-gb")!)
                .font(.caption)
            Button("Check now") {
                Task { await appState.checkPokemonCenter() }
            }
            .controlSize(.small)
        }
        .padding(.vertical, 4)
    }

    private var productGrid: some View {
        ScrollView {
            if appState.isLoading && appState.products.isEmpty {
                ProgressView("Loading…")
                    .padding(40)
            } else if appState.filteredProducts.isEmpty {
                ContentUnavailableView(
                    "No products",
                    systemImage: "shippingbox",
                    description: Text("Tap Scan to find pokemon-tcg items on John Lewis, or add a URL.")
                )
                .padding(40)
            } else {
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 220), spacing: 16)], spacing: 16) {
                    ForEach(appState.filteredProducts) { product in
                        ProductCardView(product: product) {
                            selectedProduct = product
                        } onCheck: {
                            Task { await appState.checkProduct(product) }
                        } onDelete: {
                            Task { await appState.deleteProduct(product) }
                        }
                    }
                }
                .padding()
            }
        }
        .toolbar {
            ToolbarItemGroup(placement: .primaryAction) {
                if appState.isScanning {
                    ProgressView().controlSize(.small)
                }
                Button {
                    Task { await appState.refreshAll() }
                } label: {
                    Image(systemName: "arrow.clockwise")
                }
            }
        }
        .overlay(alignment: .bottom) {
            if let msg = appState.errorMessage {
                Text(msg)
                    .font(.caption)
                    .padding(8)
                    .background(.ultraThinMaterial)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                    .padding()
            }
        }
    }
}
