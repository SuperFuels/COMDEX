# Tessaris Spatial Boardroom MVP

This is the free, dependency-free Unity 6 proof of concept for the native
Spatial Boardroom. It is a visual performance surface for the existing AION
Boardroom; it is not a second business brain.

## Included in the first scene

- Founder-view cinematic camera and overview.
- Futuristic robotics-headquarters room, illuminated executive table and
  evidence display.
- Original white humanoid robotic AION, Sales, Finance, Marketing and People
  representatives seated around the table.
- Active-speaker highlighting and smooth camera focus.
- Operations can be called into the room and walks to its seat.
- Keyboard and on-screen demonstration controls.
- Authenticated loopback-only Tessaris event and action bridge.
- Connected AION/provider roster supplied by the live Tessaris Boardroom.
- Clicking a provider opens its existing governed Tessaris direct-line chat;
  clicking a department opens its existing executive-agent chat.
- No paid assets, cloud dependency, credentials or live execution authority.

## Open and run

1. Connect the SD card named `Install macOS Sonoma`.
2. Open the project with the portable Unity 6 editor stored at
   `Tessaris/Unity/Editors/6000.0.79f1/Unity/Unity.app` on that card.
3. The project creates `Assets/Scenes/SpatialBoardroom.unity` automatically.
4. Press Play.
5. Use `1`–`5` to focus advisers, `O` to call Operations and `Escape` for the
   overview.

To produce the native macOS application, use:

`Tessaris > Build Spatial Boardroom > macOS Apple Silicon`

The SD-card copy also includes three double-clickable helpers in `Scripts`:

- `open-editor.command` opens the correct portable Unity editor and project.
- `build-macos.command` creates the standalone application under
  `Builds/macOS` after Unity Personal has been activated.
- `activate-license.command` applies the `.ulf` response file after it has
  been saved in `Tessaris/Unity/Licensing`.

## One-time Unity Personal activation

The free Unity Personal licence is issued to the owner's Unity account. The
manual activation request is stored beside the editor under
`Tessaris/Unity/Licensing`. Upload its `.alf` file at Unity's manual activation
page, download the resulting `.ulf` licence file to the same folder, and apply
it with Unity's `-manualLicenseFile` command. No Tessaris or business data is
sent as part of this editor-licensing step.

## Tessaris event boundary

The desktop launcher passes only an opaque per-run session token and two
loopback URLs:

`--tessaris-session=<opaque-token>`

`--tessaris-endpoint=http://127.0.0.1:<port>/events`

`--tessaris-actions=http://127.0.0.1:<port>/actions`

Supported MVP event types are `focus_agent`,
`operations_agent_requested`, `meeting_overview`, `caption` and
`board_members_snapshot`. The only accepted return actions are selecting a
connected Board member, selecting an executive agent, and returning to the
meeting overview. Tessaris—not Unity—opens the canonical chat and calls the
provider through the encrypted mother-brain vault. The Unity runtime never
receives provider keys, unrestricted business records, conversation history or
direct execution authority.

## Relationship to the existing Boardroom

The native room is an additional presentation surface. It does not replace the
Boardroom page, provider header, Business Map governance, Board Meetings list or
the text meeting terminal. `Open Native Boardroom World` starts the Unity app;
`Preview current web world` retains the previous browser-rendered world as an
explicit fallback.

## Visual target

The concept image is stored in `Docs/spatial-boardroom-unity-mvp-concept.png`.
The procedural prototype intentionally proves interaction before final
characters and environment art are selected.

## Storage layout

The source-of-truth project also lives in the COMDEX Git repository. Unity's
large editor, generated Library cache and macOS builds live on the SD card so
they do not consume the Mac's internal storage or enter Git.
