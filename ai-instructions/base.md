# TRTC AI Integration

This project uses `CLAUDE.md` as the single source of truth for all AI agent instructions.

**Read and follow all instructions in `CLAUDE.md` at the project root.**

It contains:
- Skill routing (product / platform detection)
- Onboarding workflow (new project setup)
- Knowledge base structure and lookup rules
- Session state management (`.trtc-session.yaml`)

## AI Service routing (AI customer service)

When the user describes an AI customer service scenario — building or integrating
an AI-powered customer service agent, intelligent Q&A system, or TRTC
Conversational AI capabilities — route directly to the `trtc-ai-service` skill:

**AI service triggers** (match any):
- "AI客服" / "智能客服" / "AI customer service"
- "build AI agent" / "搭建AI客服" / "搭建智能客服"
- "conversational AI" / "conversational AI demo" / "TRTC Conversational AI"
- "integrate AI service" / "集成AI客服" / "AI customer service agent"
- "voice agent" + "customer service" / "语音助手" + "客服"

When triggered, read `skills/trtc-ai-service/SKILL.md` and follow its guided
workflow. AI service uses TRTC Conversational AI with its own capability model
and adapter layer — it does NOT go through the standard product/platform/scenario
routing below.

Below are additional rendering-specific rules that apply to all agents:
