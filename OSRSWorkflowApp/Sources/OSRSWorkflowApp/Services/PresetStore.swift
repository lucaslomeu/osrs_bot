import Foundation

@MainActor
final class PresetStore: ObservableObject {
    @Published var presets: [Preset]
    @Published var selectedPresetID: UUID?

    private let encoder: JSONEncoder
    private let decoder: JSONDecoder
    private let userDefaults: UserDefaults

    private enum Constants {
        static let selectedPresetDefaultsKey = "selectedPresetID"
    }

    init(userDefaults: UserDefaults = .standard) {
        self.encoder = JSONEncoder()
        self.decoder = JSONDecoder()
        self.userDefaults = userDefaults

        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]

        let loadedPresets = Self.loadPresets(using: decoder) ?? [Preset.starter()]
        self.presets = loadedPresets

        if let rawSelected = userDefaults.string(forKey: Constants.selectedPresetDefaultsKey),
           let uuid = UUID(uuidString: rawSelected),
           loadedPresets.contains(where: { $0.id == uuid }) {
            self.selectedPresetID = uuid
        } else {
            self.selectedPresetID = loadedPresets.first?.id
        }

        save()
    }

    var selectedIndex: Int? {
        guard let selectedPresetID else { return nil }
        return presets.firstIndex(where: { $0.id == selectedPresetID })
    }

    func select(_ id: UUID?) {
        selectedPresetID = id
        if let id {
            userDefaults.set(id.uuidString, forKey: Constants.selectedPresetDefaultsKey)
        } else {
            userDefaults.removeObject(forKey: Constants.selectedPresetDefaultsKey)
        }
    }

    func save() {
        do {
            let url = try Self.presetsFileURL()
            try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
            let data = try encoder.encode(presets)
            try data.write(to: url, options: .atomic)
        } catch {
            print("Failed to save presets: \(error.localizedDescription)")
        }

        if let selectedPresetID {
            userDefaults.set(selectedPresetID.uuidString, forKey: Constants.selectedPresetDefaultsKey)
        }
    }

    func addPreset() {
        let preset = Preset(
            id: UUID(),
            name: "New Preset",
            notes: "",
            targetWindow: .default,
            loop: .default,
            actions: [.clickStep()]
        )
        presets.insert(preset, at: 0)
        select(preset.id)
        save()
    }

    func duplicateSelectedPreset() {
        guard let selectedIndex else { return }
        var clone = presets[selectedIndex]
        clone.id = UUID()
        clone.name += " Copy"
        presets.insert(clone, at: selectedIndex + 1)
        select(clone.id)
        save()
    }

    func deleteSelectedPreset() {
        guard let selectedIndex else { return }
        presets.remove(at: selectedIndex)
        select(presets.first?.id)
        save()
    }

    private static func presetsFileURL() throws -> URL {
        let appSupport = try FileManager.default.url(
            for: .applicationSupportDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        )
        return appSupport
            .appendingPathComponent("OSRSWorkflowApp", isDirectory: true)
            .appendingPathComponent("presets.json", isDirectory: false)
    }

    private static func loadPresets(using decoder: JSONDecoder) -> [Preset]? {
        do {
            let url = try presetsFileURL()
            guard FileManager.default.fileExists(atPath: url.path) else {
                return nil
            }
            let data = try Data(contentsOf: url)
            return try decoder.decode([Preset].self, from: data)
        } catch {
            print("Failed to load presets: \(error.localizedDescription)")
            return nil
        }
    }
}
