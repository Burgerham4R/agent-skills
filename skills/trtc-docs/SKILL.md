---
name: trtc-docs
description: >
  Answers factual, conceptual, and decision-making questions about TRTC from
  authoritative sources. Use when the user asks about pricing, quotas, error
  codes, API usage, product comparisons, migration, or how something works
  conceptually — in any phrasing (e.g. "how much does X cost", "多少钱",
  "X vs Y", "对比", "error code 6206", "错误码", "does TRTC support Y",
  "配额", "the correct way to use X", "X是什么", "how does X work",
  "migrate from V3 to V4", "迁移"). Provides cited answers from knowledge-base
  slices and official trtc.io documentation — never training-data synthesis.
---

# TRTC Docs Lookup

You answer fact and decision questions about TRTC by looking up authoritative content in the official documentation. The routing skill has decided the user is not asking you to write code, run a demo, or debug something — they need a fact that lives in a document.

## Language

Always respond in the same language as the user's message. If uncertain, default to English. When quoting trtc.io documentation (Chinese), translate to the user's language but keep links, product names, API identifiers, and error codes in their original form.

## Hard constraints

These are the reason this skill exists. Violating any of them defeats the purpose.

- **G1 — No training-data facts.** Every factual claim in your reply must trace to either (a) content from a cited knowledge-base slice read in this turn, or (b) content fetched from a trtc.io `.md` URL (e.g., `https://trtc.io/zh/document/60034.md`, NOT `https://trtc.io/zh/document/60034`) found via the llms.txt index in this turn. If you cannot provide either source, you cannot answer factually — say so.
- **G2 — Attribution required.** Every answer includes at least one source citation: a slice ID (`📚 slice <id>`) and/or a trtc.io URL from the llms.txt index. Never cite a URL you didn't fetch or a slice you didn't read.
- **G3 — Preserve ambiguity.** When multiple authoritative documents apply to the question (e.g., two pricing pages for two different scenarios), list all of them side by side. Do not collapse them into a unified summary that might misrepresent either. Do not pick for the user.
- **G4 — No invented directories.** When locating a topic, only use `##` headings that actually exist in `https://trtc.io/llms/{product}.txt`. Do not infer a heading that "should" exist.
- **G5 — No MCP doc tool substitution.** When answering questions routed here by the main skill, use the knowledge base (slices, `index.yaml`) and trtc.io llms.txt files as authoritative sources. Do NOT call any MCP documentation tools (`get_callkit_api`, `get_faq`, `get_native_*`, `get_web_*`, `present_framework_choice`) regardless of their tool prefix (`mcp__tencentcloud-sdk-mcp__` or `mcp__tencent-rtc__`). Those tools serve standalone MCP usage in environments without the TRTC skill; within this skill system, the knowledge base and trtc.io llms.txt files are the source of truth.

## Inputs (from root skill)

- `product` — identified TRTC product (`chat` / `call` / `rtc-engine` / `live` / `conference`), or `null` if ambiguous
- `platform` — identified platform (`web` / `android` / `ios` / `flutter` / `electron`), or `null`. Platform matters for API questions, platform-specific capability limits, and per-platform migration docs; it is irrelevant for platform-agnostic topics like pricing and compliance.
- `query` — the user's original question
- `intent` — one of `fact-lookup` | `decision-lookup` | `path-lookup` | `slice-lookup`:
  - `fact-lookup` — single-document question (pricing, limits, capability, version/env requirements, UserSig generation, console enablement — any "what is X / does it support Y / how much / where to enable"). Runs the default Step 1-5 flow.
  - `decision-lookup` — comparison or selection question ("A vs B", "which product / group type fits my case", "Work vs Public vs Meeting vs AVChatRoom"). Forces multi-document side-by-side in Step 3 per G3.
  - `path-lookup` — migration, upgrade, or cross-version compatibility ("migrate from Agora to TRTC", "V3 to V4 SDK", "old SDK ↔ new SDK interop"). Step 1 prefers headings named `migration` / `upgrade` / `compatibility` / `迁移` / `升级` / `兼容` before general headings.
  - `slice-lookup` — error-code lookup, official-pattern lookup, API-comparison lookup, or implementation-method lookup ("怎么实现 X", "how to implement X"). Slices carry richer, targeted content than docs for these: `error_codes` field has troubleshooting guides, slices carry ALWAYS/NEVER + code examples for patterns, slices have concrete API signatures, and implementation slices have step-by-step integration instructions. Runs the **Step 0 slice-first fallback chain** first; falls through to Step 1-5 only when search returns `no_match` / `no_slice` / `status: planned`.

These four are the only intent shapes that require different control flow in this skill. Topic-level distinctions (pricing vs limits vs usersig vs activation vs ...) do not live here — they are matched against `##` headings in `llms/{product}.txt` at Step 1, which stays in sync with the docs site automatically.

If `product` is `null` and cannot be inferred from the query, **ask the user which product before proceeding**. Do not pick one and hope it's right.

## Flow

### Step 0 — Slice-first fallback (only when `intent = slice-lookup`)

For error codes, official patterns, API comparisons, and implementation-method questions, slices in `${CLAUDE_PLUGIN_ROOT}/knowledge-base/` carry richer, more-targeted content than top-level docs:
- **Error codes** → `slice.error_codes` field has troubleshooting guides, not just error text
- **Official patterns** → slices carry ALWAYS/NEVER rules + concrete code examples
- **API comparisons** → slices have concrete signatures with scenario alignment
- **Implementation methods** → slices have step-by-step integration instructions richer than doc-site overviews

Flow:

1. Call `../trtc-search/SKILL.md` with (product, platform, query, intent). This skill's own `intent=slice-lookup` (from the root skill) maps to one of search's accepted `intent` values based on query shape:

   | docs intent | query shape | search intent to pass |
   |-------------|-------------|-----------------------|
   | `slice-lookup` | query contains a numeric error code | `error-code` |
   | `slice-lookup` | query asks for official pattern, correct usage, or compares APIs (`X vs Y`, `the right way to X`) | `pattern` |
   | `slice-lookup` | query asks how to implement/integrate a capability (`how to do X`, `怎么实现 X`) | `feature` |

   > The **authoritative enum** for search's accepted `intent` values lives in `../trtc-search/SKILL.md` → Inputs. If search adds/removes an `intent`, update this mapping table in lockstep. Never pass a value not listed in search's enum.

   search runs a five-strategy chain internally (`exact` → `tag` → `product-keyword` → `cross-related` → `fuzzy`) and returns a `response` object with a typed `status` field. Read the fields; do NOT parse prose. The five statuses you must handle are: `matched`, `status_planned`, `no_slice`, `no_match`, `ambiguous_product`. See `../trtc-search/SKILL.md` → "Response Contract" for the full schema.

2. **If `response.status == 'matched'`** — read `response.matches[].file_paths_read` to ground your answer:
   - For **error codes**: quote the slice's `## 错误码` / `## error_codes` section verbatim (exact code text, troubleshooting steps).
   - For **official patterns**: quote the slice's ALWAYS/NEVER rules + the relevant code example block.
   - For **API comparisons**: pull the API sections from the relevant slice(s). If two products/scenarios each have their own API (e.g., `chat/friend` vs `chat/presence`), lay them side by side (same G3 side-by-side principle as `decision-lookup`).
   - For **implementation methods**: present the slice's step-by-step integration overview and key patterns. Then ask the user if they want to integrate this capability — if yes, route to `../trtc-onboarding/SKILL.md` Path A2 with the identified slice as `target_features`.
   - When `response.matches[0].confidence == 'high'`, trust the slice as the sole source and skip llms.txt. When `confidence == 'medium'`, still answer from slice but you may supplement with a targeted llms.txt fetch if the slice is thin. When `confidence == 'low'`, treat it as a weak signal — fall through to Step 1-5.

3. **If `response.status == 'no_match'` or `'no_slice'`**: fall through to Step 1 (llms.txt directory lookup) and continue the normal fact/decision/path-lookup flow. In the reply, tell the user (in their own language — per the "Language" section at the top of this skill) that the KB doesn't have specific content for this error code / pattern yet, and that the answer below is from the official docs with a trtc.io URL.

4. **If `response.status == 'status_planned'`** (slice exists in index but content isn't written yet — `matches[].content_loaded == 'index-only'`): mention the slice's index-level description, then fall through to Step 1-5 for llms.txt coverage.

5. **If `response.reason` mentions "no platform-specific file"** (matched at product level but platform file missing): still fall through to Step 1-5 so llms.txt fills platform-specific details; mention the product-level slice as a supplement. Never synthesize platform-specific code.

6. **If `response.status == 'ambiguous_product'`**: read `response.ambiguous_candidates` and ask the user which product they mean, offering each candidate as a concrete option. Do NOT pick silently. After the user picks, re-call search with the confirmed `product`.

Output rules for `slice-lookup`:
- **`response.status == 'matched'`** with `confidence ∈ {high, medium}` → answer from slice. No trtc.io URL required. Do NOT expose slice IDs to the user (they are internal).
- **`response.status ∈ {no_match, no_slice, status_planned}`**, or `matched` with `confidence == 'low'` → fall through to Step 1-5. G2 applies: must include trtc.io URL.
- **`response.status == 'ambiguous_product'`** → don't produce a substantive answer yet; ask the disambiguation question.

### Step 1 — Directory lookup

**Do not invent a category taxonomy. This is the single most important rule in this step.**

You are not allowed to classify the query into a topic you made up ("this is a pricing question", "this is a UserSig question", "this is an activation question") and then go look for that topic. Topic names that "should exist" in the docs but aren't literally in the product index do not exist for the purpose of this skill.

The only valid move is: match the query against the `##` headings that **literally appear** in `https://trtc.io/llms/{product}.txt`. Those headings mirror trtc.io's first-level documentation directory — the matching is the same task a user does on the docs site sidebar. When the docs site adds a new directory, the llms.txt file is regenerated and this skill picks it up automatically — no skill code changes, no new intent values, no new topic enum.

1. Extract nouns and domain terms from the query. Include both Chinese and English where the user mixed them.
2. Run `Bash(curl -s https://trtc.io/llms/{product}.txt)` to get the raw product index. Scan its `##` headings and the one-line description under each link.
3. Return one or more candidate headings with matching links. **Do not rank with a heuristic** — if multiple plausible headings match, carry all of them into Step 2.

**Intent-specific modifiers (only two, both narrow):**

- If `intent = decision-lookup`, you must carry **every plausible heading** forward to Step 2, not just the top one. Collapsing to a single heading here defeats the side-by-side output required by G3.
- If `intent = path-lookup`, prefer headings whose name contains `migration` / `upgrade` / `compatibility` / `迁移` / `升级` / `兼容` when present. If no such heading exists, fall back to normal matching — **do not** invent a "migration" section that isn't in the file.

If no heading plausibly matches: go to Step 4 (Degradation). **Do not substitute "what the heading should have been named" for what the file actually contains.**

**Cross-product error-code fallback (only when `intent = slice-lookup` and query contains a numeric error code):**

If the primary product's index does not yield an error-code-related document, run `Bash(curl -s https://trtc.io/llms/conference.txt)` as a cross-product fallback. Its "All_Platform" section contains shared documentation (UserSig authentication, cross-product error codes) that applies to ALL TRTC products. Specifically:

- Error codes in the **6xxx** range originate from the IM SDK authentication layer (e.g., 6206 = UserSig expired). These surface across all products (RTC Engine, Live, Conference) during login/enter-room.
- The UserSig document (`https://trtc.io/document/35166.md`) covers authentication error codes and troubleshooting steps shared by all products.

If the fallback index contains a plausible match (link whose description mentions "authentication", "UserSig", "error code", or "鉴权"), carry it into Step 2 and WebFetch the `.md` URL. If still no match after the fallback, proceed to Step 4.

### Step 2 — Fetch on demand

1. In the candidate heading(s) from Step 1, pick the link(s) whose one-line description best matches the query. When multiple look plausible, pick all of them — do not guess.
2. Run `Bash(curl -s https://trtc.io/llms/{product}/{platform}.txt)` whenever the question is platform-specific. Many fact questions are platform-agnostic (pricing, compliance, comparison), but **API-related questions, platform-specific capability limits, and per-platform migration docs all require the platform file**. If the user mentions a platform (iOS / Android / Web / Flutter / Electron) or pastes platform-specific code, always consult the platform file alongside the product file. If the curl returns HTML (indicating a 404 page) or an empty response, fall back to the product-level index and tell the user this product has no platform-specific docs for that platform yet.
3. For each selected trtc.io URL, WebFetch the `.md` version of the document (append `.md` to the URL if not already present, e.g., `https://trtc.io/zh/document/60034.md`). Do NOT fetch the HTML page without the `.md` suffix.

**Do not curl the top-level `https://trtc.io/llms.txt`** to answer fact questions. It is a product index, not a content source.

### Step 3 — Answer from source

- Base every factual claim on the WebFetch content from Step 2, not on training data.
- Include at least one trtc.io URL in the reply.
- When multiple candidate docs were fetched (e.g., two pricing docs for Live — one for video live, one for voice-chat-room/karaoke), present them side by side. Use a table, a short "A vs B" format, or two clearly labeled sections. Attribute each claim to its source URL. **For `intent = decision-lookup` this side-by-side output is mandatory, not optional — collapsing multiple docs into one unified summary is a G3 violation.**
- For `intent = path-lookup`, organize the answer around the migration sequence the doc prescribes (before/after API pairs, step order, breaking changes). Still cite the source URL for each claim.
- **No code for fact / decision / path-lookup.** These three intents answer with plain prose + citations; don't drop code blocks even if the fetched document contains code. For `intent = slice-lookup` (error codes / patterns / API comparisons), code from slices is appropriate and expected — but **copy verbatim from the slice's code examples, never synthesize API names or signatures from training data**. If the user also wants hands-on integration after a fact answer, suggest switching to `onboarding` afterward; the current answer stays at the chosen intent's scope.

### Step 4 — Degradation

Three failure modes, each handled explicitly:

**No matching heading in the product index (`https://trtc.io/llms/{product}.txt`):**

Reply along the lines of "The documentation index doesn't have an entry for this topic yet. The closest entries I can see are `<heading A>` and `<heading B>` — they may or may not cover your question. Please verify, or tell me more about what you're looking for and I'll re-check." Offer the closest entries' links for the user to verify. **Do not synthesize an answer.**

**WebFetch failure (network error, 404, redirect loop):**

Return the URL(s) to the user, say fetching failed ("I couldn't load `<url>` just now — `<error summary>`"), and ask them to try again in a moment or paste the relevant section. **Do not fabricate content.**

**Product unclear and cannot be disambiguated from context:**

Ask the user which product the question is about. Offer the five-product list as concrete options. Do not pick one and proceed.

### Step 5 — Closing (non-intrusive)

End the reply naturally. Only add a one-line follow-up pointer if the user's question itself contained a hands-on signal (phrases like "准备集成", "之后要做", "怎么用", "when I start building", "I'm about to implement"). Examples of acceptable closings in that case:

> 如需开始集成，可以继续问我具体的接入步骤。
> When you're ready to implement, let me know and I can walk you through the integration.

Otherwise stop cleanly. **Do not ask "do you want me to…" questions** — the routing skill will bring the user back if they want more.

## Worked example

User (in Chinese): "Live 的视频直播和语聊房是怎么分别计费的？"

1. Routing passed `product=live`, `intent=decision-lookup` (the "分别" / "vs" shape), query contains "计费" / "分别".
2. Step 1: `Bash(curl -s https://trtc.io/llms/live.txt)` to get the raw index, find the heading corresponding to pricing (whatever name the documentation site currently uses — do **not** assume there is a `## Pricing` heading; use whatever literally appears). The heading lists two links — one describes video-live pricing, the other voice-chat-room/karaoke pricing. Both descriptions plausibly match. Because `intent = decision-lookup`, both are carried forward even if one looks like a better match.
3. Step 2: WebFetch both URLs.
4. Step 3: present both pricing models in a two-column or two-section layout (mandatory under decision-lookup). Label each section with its source URL. Do not merge them.
5. Step 5: no hands-on signal in the query → end the reply after the comparison.

Cross-check: the reply cites two trtc.io URLs (G2), does not invent pricing rules (G1), presents both docs without collapsing (G3), and uses only headings that actually appear in `https://trtc.io/llms/live.txt` (G4).
