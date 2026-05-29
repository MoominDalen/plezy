import SwiftUI

struct ProductCardView: View {
    let product: Product
    let onEdit: () -> Void
    let onCheck: () -> Void
    let onDelete: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            ZStack(alignment: .topTrailing) {
                productImage
                statusBadge
                    .padding(8)
            }
            .frame(height: 160)
            .clipped()

            VStack(alignment: .leading, spacing: 6) {
                Text(product.name)
                    .font(.headline)
                    .lineLimit(2)
                Text(product.statusMessage ?? "Not checked yet")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)

                HStack {
                    Button("Edit", action: onEdit)
                    Button("Check", action: onCheck)
                    Spacer()
                    Button(role: .destructive, action: onDelete) {
                        Image(systemName: "trash")
                    }
                }
                .controlSize(.small)
            }
            .padding(10)
        }
        .background(Color(nsColor: .controlBackgroundColor))
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .stroke(borderColor, lineWidth: 2)
        )
        .shadow(color: .black.opacity(0.08), radius: 4, y: 2)
    }

    @ViewBuilder
    private var productImage: some View {
        if let urlString = product.imageUrl, let url = URL(string: urlString) {
            AsyncImage(url: url) { phase in
                switch phase {
                case .success(let image):
                    image.resizable().scaledToFill()
                case .failure:
                    placeholder
                default:
                    ProgressView()
                }
            }
        } else {
            placeholder
        }
    }

    private var placeholder: some View {
        ZStack {
            LinearGradient(
                colors: [Color.blue.opacity(0.35), Color.purple.opacity(0.35)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            Image(systemName: "square.stack.3d.up.fill")
                .font(.system(size: 40))
                .foregroundStyle(.white.opacity(0.8))
        }
    }

    private var statusBadge: some View {
        Text(product.isInStock ? "IN STOCK" : "OUT")
            .font(.caption2.bold())
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(product.isInStock ? Color.green : Color.gray.opacity(0.85))
            .foregroundStyle(.white)
            .clipShape(Capsule())
    }

    private var borderColor: Color {
        if product.isInStock { return .green }
        if product.available == false { return .red.opacity(0.5) }
        return .clear
    }
}
