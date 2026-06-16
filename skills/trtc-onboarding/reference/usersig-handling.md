# UserSig Handling (Console-issued test UserSig)

> Referenced during login code generation in A2-Q3 (when processing a login-auth
> slice) and A1 (when configuring demo credentials).
>
> **There is NO automatic UserSig generation path.** The skill does NOT generate
> UserSig — not via MCP, not via client-side signing, not via any local script.
> Test UserSig is ALWAYS obtained by the user from the TRTC console and pasted in.
> Your job is to (1) emit placeholders, (2) wire up input fields, and (3) hand
> off clear "how to get & fill UserSig" instructions.

## Why no auto-generation

- **No MCP path.** Do NOT call any `get_usersig` MCP tool. Do NOT tell the user
  "I'll generate a UserSig for you via MCP." This capability is intentionally not
  part of the flow — never reference it, never attempt it, never imply it.
- **No client-side signing.** Generating UserSig in the browser/client requires
  the `SecretKey`, which must never be shipped to a client. Forbidden (see § Never).
- **Production** UserSig MUST be issued by the developer's own backend.

## Generation Protocol (placeholder + console handoff)

### Step 1: Decide the test userID(s)

Use `userXXX` (zero-padded 3-digit), default `user001`. If the scenario needs
two participants (caller + callee, host + audience), also prepare `user002`.
Honor any userID/naming preference the user already expressed.

### Step 2: Emit placeholder credentials in the generated code

Do NOT fill a real UserSig. Emit clearly-marked placeholders:

```typescript
// ================================================
// Test credentials (development only)
// ================================================
const SDK_APP_ID = {sdkAppId};        // your SDKAppID (numeric; 0 if unknown)
const USER_ID = 'user001';            // test user
const USER_SIG = 'YOUR_USERSIG';      // ← paste a test UserSig from the TRTC console

// ⚠️ A console-issued test UserSig is for development only and expires
//    (typically ~24h–7d depending on the console setting).
//    For production, issue UserSig from YOUR OWN backend.
//    See: https://trtc.io/document/34385
```

If the SDKAppID is known (the user provided it during onboarding), fill it in.
Otherwise leave the `0` / `YOUR_SDKAPPID` placeholder. The UserSig is ALWAYS a
placeholder.

### Step 3: Provide a user-input entry

The generated login page / component MUST include input fields (or a config
mechanism) that let the user paste their own userID and userSig at runtime.

**For Web (Vue/React):**
- Input fields for userID and userSig in the login form
- Pre-fill userID with `user001`; leave userSig empty or `YOUR_USERSIG`
- Allow the user to type their own values before clicking login

**For Native (iOS/Android/Flutter):**
- A config struct/object with the test defaults and a placeholder userSig
- Clear comments marking where to paste the console-issued UserSig
- Optionally: text fields on the login screen if the UI supports it

**Template pattern (Web Vue example):**

```vue
<template>
  <div class="login-form">
    <input v-model="userId" placeholder="UserID" />
    <input v-model="userSig" placeholder="Paste UserSig from TRTC console" type="password" />
    <button @click="handleLogin">Login</button>
  </div>
</template>

<script setup>
import { ref } from 'vue';

// Pre-filled test userID; UserSig must be pasted from the console
const userId = ref('user001');
const userSig = ref(''); // ← paste a console-issued test UserSig

// SDKAppID (numeric); fill from your TRTC console
const sdkAppId = {sdkAppId};

async function handleLogin() {
  // login logic using userId.value, userSig.value, sdkAppId
}
</script>
```

### Step 4: Multiple test users (optional)

If the scenario needs multiple users, emit a placeholder slot for each, clearly
labeled. The user generates one UserSig per userID in the console:

```typescript
// User A (e.g., host / caller)
const USER_A_ID = 'user001';
const USER_A_SIG = 'YOUR_USERSIG_FOR_user001';  // ← from console

// User B (e.g., audience / callee) — use in a second browser tab or device
const USER_B_ID = 'user002';
const USER_B_SIG = 'YOUR_USERSIG_FOR_user002';  // ← from console
```

## Completion handoff — UserSig fill guidance (MUST surface to the user)

Code comments alone are not enough. Because the generated login code NEVER
contains a working pre-filled UserSig, you MUST — at the end of the integration
(topic Step 4 area / official-roomkit completion / `integrate-feature` A2-Q4) —
include a short, explicit **"如何获取并填入 UserSig"** block in the chat handoff,
not buried in code comments. Template (translate to the user's language):

```
⚠️ 还差一步才能登录:这套代码里的 userSig 是占位符,需要你从控制台获取真实值后填入。

获取测试 userSig(开发联调用):
1. 打开 https://console.trtc.io/  →  选择你的应用
2. 进入「快速跑通 / UserSig 生成&校验」,输入一个 userId(如 user001)生成 UserSig
3. 把生成的 userSig 填到 <文件路径>:<行号>(变量 `USER_SIG` / 登录表单的 UserSig 输入框)
   SDKAppID 填到 <文件路径>(变量 `SDK_APP_ID`)

注意:控制台生成的 userSig 仅用于开发联调,会过期(约 24h–7d);生产环境必须由你的后端签发。
```

Fill in the real `<文件路径>:<行号>` from the code you just generated. Never claim
the userSig was auto-generated — it is always a placeholder the user must fill.

## Never

- **Never call any `get_usersig` MCP tool**, and never tell the user the skill can
  generate a UserSig for them via MCP. This path does not exist.
- Never hardcode a real `SecretKey` in generated code (client OR sample).
- Never generate userSig manually (HMAC-SHA256) in client code, and never add
  browser-side signing dependencies (`crypto-js`, `pako`, `tls-sig-api-v2`).
- Never create a `**/usersig.*` or `**/generate-usersig.*` signer file.
- Never present a test userSig as "production-ready" — always mark it test/dev
  only with an expiry warning, and direct production issuance to the user's backend.
