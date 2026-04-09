import SwiftUI

struct EditableDoubleField: View {
    let title: String
    @Binding var value: Double
    let maxFractionDigits: Int

    @FocusState private var isFocused: Bool
    @State private var draft: String = ""

    var body: some View {
        TextField(title, text: $draft)
            .textFieldStyle(.roundedBorder)
            .focused($isFocused)
            .onAppear {
                syncDraftFromValue()
            }
            .onChange(of: value) { _, newValue in
                guard !isFocused else { return }
                draft = formattedString(for: newValue)
            }
            .onChange(of: isFocused) { _, focused in
                if focused {
                    draft = editableString(for: value)
                } else {
                    commitDraft()
                }
            }
            .onChange(of: draft) { _, newDraft in
                guard isFocused else { return }
                updateValueIfPossible(from: newDraft)
            }
            .onSubmit {
                commitDraft()
            }
    }

    private func syncDraftFromValue() {
        draft = formattedString(for: value)
    }

    private func commitDraft() {
        let trimmed = draft.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !trimmed.isEmpty else {
            syncDraftFromValue()
            return
        }

        guard let parsedValue = parsedDouble(from: trimmed) else {
            syncDraftFromValue()
            return
        }

        value = parsedValue
        draft = formattedString(for: parsedValue)
    }

    private func updateValueIfPossible(from string: String) {
        let trimmed = string.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !trimmed.isEmpty else {
            return
        }

        guard !["-", ".", ",", "-.", "-,"].contains(trimmed) else {
            return
        }

        guard let parsedValue = parsedDouble(from: trimmed) else {
            return
        }

        value = parsedValue
    }

    private func parsedDouble(from string: String) -> Double? {
        let normalized = string
            .replacingOccurrences(of: ",", with: ".")
            .replacingOccurrences(of: " ", with: "")

        return Double(normalized)
    }

    private func editableString(for value: Double) -> String {
        let wholeValue = value.rounded(.towardZero)
        if abs(value - wholeValue) < 0.000_000_1 {
            return String(Int(wholeValue))
        }

        return formattedString(for: value)
    }

    private func formattedString(for value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        formatter.locale = .current
        formatter.minimumFractionDigits = 0
        formatter.maximumFractionDigits = maxFractionDigits
        formatter.usesGroupingSeparator = false

        return formatter.string(from: NSNumber(value: value)) ?? "\(value)"
    }
}
