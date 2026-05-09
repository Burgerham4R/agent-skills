# UIKit Class → AtomicXCore Composable Bindings

> **Internal asset.** Consumed by `topic/SKILL.md` when generating full-ui
> Vue SFCs. Maps UIKit component class names (defined in
> `uikit/references/component-catalog.md`) to AtomicXCore composables and
> reactive Vue bindings. Users never read this file.

> **Caveat:** composable names below are assumed based on the AtomicXCore Vue 3
> SDK surface (`useLoginState` / `useRoomState` / `useDeviceState` /
> `useRoomParticipantState`). Verify against the actual installed SDK version
> before generation and adjust as needed.

## Device controls

| UIKit class pattern | Composable | Vue binding example |
|---|---|---|
| `.ui-icon-button.is-off` (mic) | `useDeviceState()` | `:class="{ 'is-off': isMicOff }" @click="toggleMic"` |
| `.ui-icon-button.is-off` (camera) | `useDeviceState()` | `:class="{ 'is-off': isCameraOff }" @click="toggleCamera"` |
| `.ui-icon-button` (screen share) | `useDeviceState()` | `:class="{ 'is-active': isScreenSharing }" @click="toggleScreenShare"` |

## Room state

| UIKit class pattern | Composable | Vue binding example |
|---|---|---|
| `.ui-topbar__title` | `useRoomState()` | `{{ roomName }}` |
| `.ui-topbar__time` | `useRoomState()` | `{{ elapsed }}` |
| `.ui-btn--end` (leave button) | `useRoomState()` | `@click="leaveRoom"` |

## Participants

| UIKit class pattern | Composable | Vue binding example |
|---|---|---|
| `.ui-stage__tile` (video tile) | `useRoomParticipantState()` | `v-for="p in participants" :key="p.userId"` |
| `.ui-list-row` (member row) | `useRoomParticipantState()` | `v-for="p in participants" :key="p.userId"` |
| `.ui-video-badge__name` | `useRoomParticipantState()` | `{{ p.userName }}` |
| `.ui-avatar` (dynamic avatar) | `useRoomParticipantState()` | `:style="{ backgroundImage: 'url(' + p.avatar + ')' }"` |

## Side panels

| UIKit class pattern | Vue state | Vue binding example |
|---|---|---|
| `.ui-side-panel.is-open` | `const activePanel = ref(null)` | `:class="{ 'is-open': activePanel }"` |
| `.ui-side-panel__close` | same | `@click="activePanel = null"` |
| `.mc-app.is-panel-open` | same | `:class="{ 'is-panel-open': activePanel }"` |

## Static-to-reactive replacement rules

1. Any `.is-off` / `.is-on` / `.is-open` / `.is-active` static class →
   `:class="{ '<class>': <reactive state> }"`
2. Any hardcoded participant data (avatar URL / name / message) →
   `v-for` + a reactive array returned by the mapped composable
3. Every button → `@click` binding to the corresponding composable action
4. Retain as static (do NOT replace): layout / size / color classes that carry
   no state (e.g. `.ui-icon-button`, `.ui-icon-button__iconrow`,
   `.ui-icon--lg`)
5. Inline styles are retained only for the three data-driven cases listed in
   `uikit/references/token-contract.md` (`background-image`, `--level`,
   `--stage-off-avatar`)

## Fallback when a composable is absent from the scenario

If the scenario's slice list does not cover a given composable (e.g.
`general-meeting` has no raise-hand), topic either (a) omits the corresponding
UI region, or (b) keeps a static placeholder. Topic chooses based on whether
the region is structurally essential (toolbar / stage → keep placeholder;
side-panel tab → omit).
