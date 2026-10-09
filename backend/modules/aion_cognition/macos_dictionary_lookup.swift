import CoreServices
import Foundation

// Read the same local Dictionary Services data used by Dictionary.app.  The
// query is supplied as a process argument so it is never interpolated into
// source code or a shell command.
guard CommandLine.arguments.count > 1 else {
    exit(2)
}

let query = CommandLine.arguments[1] as CFString
let range = CFRange(location: 0, length: CFStringGetLength(query))
if let value = DCSCopyTextDefinition(nil, query, range) {
    print(value.takeRetainedValue())
    exit(0)
}
exit(1)
