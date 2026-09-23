import Foundation

public enum PilotCanonicalJSON {
    public static func data(_ value: Any) throws -> Data {
        guard JSONSerialization.isValidJSONObject(value) else { throw Error.invalidObject }
        return try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys, .withoutEscapingSlashes])
    }

    public enum Error: Swift.Error { case invalidObject }
}
