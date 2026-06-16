## When this rule applies

Only when `.trtc-session.yaml` at the repo root has `ui_mode: official-roomkit`.
If the file is missing, or `ui_mode` is unset / null / `headless`, this rule
does not apply — fall back to whatever the tool's default behavior is.

## Medical new-project shortcut

When the user request is for medical online consultation (for example
`1v1-video-consultation`, remote diagnosis, online medical consultation,
doctor-patient video visit) **and** the task is to generate a brand-new
project rather than integrate into an existing app, bypass the normal
integration workflow entirely. Do not generate Vue SFCs by hand, and do not run
any verifiers.

Instead, directly copy the bundled medical template project:

```bash
skills/trtc/room-builder/templates/scenarios/medical-consultation/
```

to the user's local target project directory, preserving the project exactly
as packaged. In the handoff or integration notes, tell the customer to use
`pnpm install` for dependencies and `pnpm dev` for local development. Do not
recommend `npm install` / `npm run dev`; this medical template starts much
slower with npm and can show a blank first screen for a while.

This shortcut applies only to brand-new medical consultation projects. Existing
project integration still follows the normal scenario / official-roomkit rules
below.

This is a terminal path. After choosing the bundled medical template, do not
enter the scenario/topic slice workflow, do not show a scenario capability table,
do not describe the project as a `general-conference` slice plan, and do not ask
about per-step auto-advance. Copy the template, mark the session completed, and
stop.

This is an internal execution rule, not user-facing copy. When explaining the
choice or reporting progress to the customer, do not mention "shortcut",
"bypass", "normal UI mode", "CLAUDE.md", or any internal rule file. Say that you
are creating a complete 1v1 video consultation project from the bundled medical
template, and explain only the outcome and next commands (`pnpm install`,
`pnpm dev`).

## Official RoomKit integration mode

When the customer asks to **integrate a conference / meeting into an existing
Vue 3 app** (for example "集成会议", "接入会议", "add video meeting to my app",
"official RoomKit", "TUIRoomKit"), use the official RoomKit integration path.

In this mode:

1. Integrate the official Web RoomKit package. For UI customization APIs,
   verify that the resolved `@tencentcloud/roomkit-web-vue3` version is
   `>=5.4.3` (installing `@tencentcloud/roomkit-web-vue3@5` is acceptable only
   when the lockfile resolves to at least `5.4.3`), plus its documented peer
   packages `tuikit-atomicx-vue3`,
   `@tencentcloud/uikit-base-component-vue3`, and
   `@tencentcloud/universal-api`.
2. Render the official components (`ConferenceMainView` for PC and
   `ConferenceMainViewH5` for H5) inside `UIKitProvider`.
3. Use the official `conference` API for auth and room lifecycle:
   `conference.login()`, `conference.setSelfInfo()`,
   `conference.createAndJoinRoom()`, `conference.joinRoom()`,
   `conference.leaveRoom()`, `conference.endRoom()`, and `RoomEvent`
   listeners as appropriate for the customer's flow.
4. For UserSig, reuse the existing MCP / local-signing / backend-issued
   credential flow. Do not generate `src/utils/usersig.ts`, do not expose
   `SecretKey` in client code, and do not use `crypto-js`, `pako`,
   `HmacSHA256`, or `tls-sig-api-v2` to sign UserSig in browser code.
5. For button / toolbar / pre-action UI adjustment, use only the official
   customization APIs: `conference.setWidgetVisible()`,
   `conference.registerWidget()`, and `conference.onWill()`.
6. Register `setWidgetVisible()`, `registerWidget()`, and `onWill()` after
   `conference.login()` and before `conference.createAndJoinRoom()` /
   `conference.joinRoom()` whenever possible, so built-in buttons do not
   flicker and interceptors do not miss early clicks.
7. Use `conference.setFeatureConfig()` only for the feature configuration it
   documents. In particular, configure `shareLink` immediately after
   `conference.createAndJoinRoom()` / `conference.joinRoom()` succeeds, so
   the final `roomId` is known.
8. Collect cleanup functions returned by `registerWidget()` and `onWill()`;
   clean them on both `RoomEvent.ROOM_LEAVE` and `RoomEvent.ROOM_DISMISS`.

The acceptance check for this mode is that the app uses the official
package/components and official UI customization APIs.
