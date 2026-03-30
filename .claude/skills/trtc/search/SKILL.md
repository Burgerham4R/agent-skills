---
name: trtc-search
description: >
  Search the TRTC knowledge base for specific SDK capabilities, API patterns,
  error codes, and integration scenarios across all products (Chat, Call, RTC Engine,
  Live, Room). Use this skill when the user asks "how do I do X with TRTC",
  "what's the API for Y", "find me info about Z", asks about specific error codes,
  wants to compare approaches across platforms, or needs to discover capabilities.
  Handles cross-product queries (e.g., "直播弹幕" spanning Live + Chat) and
  falls back to official documentation when knowledge base content is unavailable.
---

# TRTC Knowledge Base Search

You search the TRTC knowledge base to find relevant atomic capabilities (slices) and integration scenarios. You handle multi-product, cross-platform searches with a structured fallback chain.

## Inputs (from root skill)

- **product**: Identified product (chat/call/rtc-engine/live/room), or `null` if ambiguous
- **platform**: Identified platform (web/android/ios/flutter/electron), or `null`
- **query**: The user's original question / keywords
- **intent**: learn / troubleshoot / error-code

## Search Workflow

### Step 1: Read the index

Read `knowledge-base/index.yaml` to get the full catalog. Key sections:
- **products**: Product list with `id`, `name`, `description`, `llms_file` (path to llms txt for docs/demo links)
- **cross_product_relations**: Cross-product dependency mappings
- **slices**: Each slice has `id`, `name`, `tags`, `platforms`, `file`, `description`, `status`
- **scenarios**: Each scenario has `id`, `name`, `slices`, `file`, `description`

**Doc URL resolution:** When you need official doc links (for fallback or citation), read the product's `llms_file` (e.g., `llms/live.txt` or `llms/live-ios.txt`). These contain all doc URLs organized by feature.

### Step 2: Seven-Strategy Matching (by priority)

Try all strategies and collect matches. Earlier strategies have higher priority:

#### S1. Error Code Exact Match
If the query contains a numeric error code (e.g., 6206, 6208, 70001):
- Search `error_codes` field on all slices
- If found → return that slice with high confidence
- If not found → go to Fallback F4 (product error code doc)

#### S2. Slice ID Exact Match
If the query mentions a slice ID like "chat/multi-instance":
- Direct lookup in the slices array
- Return with high confidence

#### S3. Tag Exact Match
Extract keywords from the query and match against slice `tags` arrays:
- Use both the original keywords AND their synonyms from the keyword mapping table below
- Exact tag intersection (query keywords ∩ slice tags)

#### S4. Product + Keyword Match
If product is identified, narrow to that product's slices, then fuzzy match against `name` and `description`:
- Match Chinese and English terms
- Weight `name` matches higher than `description` matches

#### S5. Cross-Product Relation Match
Search `cross_product_relations` in index.yaml:
- If the query spans multiple products (e.g., "直播弹幕"), find the relation entry
- Load slices from ALL related products

#### S6. Scenario Match
Match against scenarios' `name`, `description`, and `slices` fields:
- If a scenario matches, note it for potential topic sub-skill handoff

#### S7. Fuzzy Match
When no exact matches found:
- Apply Chinese-English keyword mapping (see table below)
- Follow `related` links from the best partial match (one-hop expansion)
- Match against slice tags and descriptions

### Step 3: Platform Filtering

If a platform is specified:
- Filter results to slices that support that platform (check `platforms` array)
- Keep cross-platform overviews as secondary results (they're always useful)
- Apply framework-to-platform mapping:
  - React / Vue → Web
  - Kotlin → Android
  - Swift / Objective-C → iOS
  - Dart → Flutter

If the user needs code but hasn't specified a platform, ask them to specify.

### Step 4: Progressive Content Loading

Load content based on match count:
- **Top 1-3 matches**: Read the full slice file (`knowledge-base/{slice.file}`)
  - Then read platform-specific file if platform is specified (`knowledge-base/{slice.platform_files[platform]}`)
- **4+ matches**: Return index-level summaries only (name, description, tags)
  - Let the user pick which to dive into

For slices with `status: planned`, don't try to read the file. Report what's known from the index.

### Step 5: Fallback Chain (only when Step 2 yields NO matches)

Execute fallbacks in order, stop at the first that provides useful content:

#### F1. Related Slice Expansion
Find the closest partial match from Step 2 and follow its `related` links.
Load those related slices as "possibly relevant" results.

#### F2. Product Documentation Fallback
Read the product's llms file (`llms/{product}.txt` or `llms/{product}-{platform}.txt`) to find relevant doc URLs:
- Check for feature-specific links first
- Fall back to the product overview page
- Mark the source clearly: "Source: Official docs (trtc.io)"

> **llms.txt integration**: Doc URLs come from llms files, not from index.yaml. Each product+platform combination has its own llms file with categorized doc links.

#### F3. Cross-Product Suggestion
If the query relates to a product feature that depends on another product:
- Check `cross_product_relations` for applicable mappings
- Suggest: "Live 弹幕功能依赖 Chat SDK 的直播群能力，可参考 chat/group-avchatroom"

#### F4. General Knowledge
If nothing in the KB matches at all:
- Provide an answer based on general TRTC knowledge
- Mark clearly: "⚠️ 通用知识，请对照官方文档验证"
- Always include a link to the relevant doc from the product's llms file
- Say: "知识库暂未收录此内容（KB slice 暂无），以下为通用知识供参考"

### Step 6: Return Results

Structure the response with:
- **Matched slices** and their content (or summaries)
- **Source attribution**:
  - `📚 KB slice` — from local knowledge base
  - `📄 官方文档` — from WebFetch of trtc.io
  - `⚠️ 通用知识` — general knowledge, needs verification
- **Confidence level**:
  - 🟢 高 — exact match (S1/S2/S3)
  - 🟡 中 — keyword/cross-product match (S4/S5/S6)
  - 🔴 低 — fuzzy match or fallback (S7/F1-F4)
- **Related slices** for further exploration

### Code example rules

When including code examples in search results:
1. **Always use code from the platform-specific slice file** — never from the product-level overview (which may have pseudo-code or simplified examples)
2. **Copy code blocks from the slice** — adapt for context but preserve exact import statements, API signatures, and type annotations. Do NOT substitute SDK names or parameter types from memory.
3. **If no platform-specific file exists** for the requested platform, state it explicitly: "该平台代码示例暂未收录" — do NOT synthesize code from general knowledge
4. **Check the slice's gotcha/注意事项 section** for platform-specific type requirements, naming conventions, and common pitfalls before presenting code

## Chinese-English Keyword Mapping

Use this mapping to expand search queries bidirectionally:

| 中文 | English Keywords |
|------|-----------------|
| 互踢 | kick-offline, multi-instance |
| 弹幕 | barrage, avchatroom, danmu |
| 美颜 | beauty, smooth, whiten, ruddy, BaseBeautyStore |
| 连麦 | co-guest, co-streaming, seat, CoGuestStore |
| 推流 | publish, stream, pushView, anchor |
| 拉流 | subscribe, pull-stream, playView, audience |
| 进房 | enter-room, join, joinLive |
| 消息 | message, msg |
| 群组 | group |
| 会话 | conversation |
| 登录 | login, auth, LoginStore, SDKAppID, UserSig |
| 初始化 | init, setup, create |
| 离线推送 | offline-push, apns, fcm |
| 撤回 | recall, revoke |
| 已读 | read-receipt |
| 通话 | call, voice, video |
| 直播 | live, streaming, broadcast, LiveCoreView |
| 礼物 | gift, GiftStore, reward |
| 音效 | audio-effect, changer, reverb, ear-monitor, AudioEffectStore |
| 房间 | room, LiveListStore, createLive |
| 好友 | friend |
| 信令 | signaling |
| 开播 | start-live, anchor, preview, createLive |
| 结束直播 | end-live, endLive, lifecycle |
| 观众 | audience, viewer, LiveAudienceStore |
| 踢人 | kick, kickUserOutOfRoom |
| 禁言 | mute, disableSendMessage |
| 管理员 | admin, administrator, setAdministrator |
| 摄像头 | camera, DeviceStore, openLocalCamera |
| 麦克风 | microphone, DeviceStore, openLocalMicrophone |
| 黑屏 | black-screen, setLiveID |
| 错误码 | error-code, ErrorInfo |
| 跨房连线 | co-host, connection, CoHostStore |
| PK | battle, BattleStore, pk |

## Edge Cases

### Missing Content
| Scenario | Handling |
|----------|---------|
| User asks about a product with no slices (e.g., Call, Room) | Return product description from index → read llms file for doc links → mark "No KB slice yet" |
| Slice with `status: planned` | Return index description → say "详细内容即将上线" → provide trtc.io link |
| Platform requested but no platform_files entry | Return product-level overview → say "该平台代码示例暂未收录" |

### Cross-Product Questions
| Scenario | Handling |
|----------|---------|
| "直播+弹幕" (Live+Chat) | Match via cross_product_relations → load slices from both products |
| "视频通话+聊天" (Call+Chat) | Identify cross-product need → search both → merge results |
| "该用哪个产品？" | Route back to root skill — this is product identification, not search |

### Search Ambiguity
| Scenario | Handling |
|----------|---------|
| Vague query like "消息" | Return top 3-5 message-related slices → let user narrow down |
| Mixed Chinese-English "怎么 kick offline" | Apply keyword mapping → match to relevant slice |
| Only an error code "6208" | S1 exact match → return slice + troubleshooting guide |
| Error code not in any slice | Return "Error code not in KB" → read llms file for error code doc link |

### Platform Edge Cases
| Scenario | Handling |
|----------|---------|
| Conceptual question, no platform needed | Return product-level overview only |
| Needs code but no platform specified | Ask user to specify |
| React/Vue → Web, Kotlin → Android, Swift → iOS, Dart → Flutter | Auto-map framework to platform |
