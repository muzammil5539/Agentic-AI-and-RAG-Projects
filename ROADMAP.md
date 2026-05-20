# 🗺️ AI Engineering Universe — Roadmap

## Master Dependency Graph

```mermaid
graph TD
    %% Phase 1 - Beginner (Green)
    P1["✅ 1. RAG LangChain"]:::done
    P2["✅ 2. RAG Custom"]:::done
    P3["🟡 3. Conv. AI Agent"]:::beginner
    P4["4. Doc Summarizer"]:::beginner
    P5["5. Prompt Lab"]:::beginner

    %% Phase 2 - Intermediate (Blue)
    P6["6. Multi-Agent Research"]:::intermediate
    P7["7. Code Review Agent"]:::intermediate
    P8["8. Voice AI"]:::intermediate
    P9["9. Knowledge Graph RAG"]:::intermediate
    P10["10. Workflow Automation"]:::intermediate
    P11["11. Memory System"]:::intermediate

    %% Phase 3 - Advanced (Orange)
    P12["12. Browser Agent"]:::advanced
    P13["13. AI SaaS Platform"]:::advanced
    P14["14. Vision AI"]:::advanced
    P15["15. Fine-Tuning Pipeline"]:::advanced
    P16["16. DevOps Agent"]:::advanced
    P17["17. Local LLM Platform"]:::advanced

    %% Phase 4 - Enterprise (Red)
    P18["18. Enterprise RAG"]:::enterprise
    P19["19. AI Eval Framework"]:::enterprise
    P20["20. Multi-Agent Orchestrator"]:::enterprise
    P21["21. Security Agent"]:::enterprise

    %% Phase 5 - Research (Purple)
    P22["22. Self-Improving Agent"]:::research
    P23["23. Agent Marketplace"]:::research
    P24["24. Edge AI"]:::research
    P25["25. Finance Agent"]:::research

    %% Dependencies
    P1 --> P6
    P2 --> P9
    P3 --> P6
    P3 --> P7
    P3 --> P8
    P3 --> P12
    P4 --> P14
    P5 --> P19
    P6 --> P20
    P7 --> P16
    P8 --> P13
    P9 --> P18
    P10 --> P20
    P11 --> P22
    P12 --> P23
    P13 --> P23
    P15 --> P17
    P16 --> P21
    P17 --> P24
    P18 --> P25
    P20 --> P23
    P22 --> P23

    %% Styling
    classDef done fill:#22c55e,stroke:#16a34a,color:#fff
    classDef beginner fill:#4ade80,stroke:#22c55e,color:#000
    classDef intermediate fill:#60a5fa,stroke:#3b82f6,color:#fff
    classDef advanced fill:#f59e0b,stroke:#d97706,color:#000
    classDef enterprise fill:#ef4444,stroke:#dc2626,color:#fff
    classDef research fill:#a855f7,stroke:#9333ea,color:#fff
```

---

## Phase Timeline

```mermaid
gantt
    title AI Engineering Universe - Implementation Timeline
    dateFormat  YYYY-MM-DD
    axisFormat  %b %Y

    section Phase 1: Beginner
    RAG LangChain (Done)        :done, p1, 2025-01-01, 2025-02-01
    RAG Custom (Done)           :done, p2, 2025-02-01, 2025-03-15
    Conversational AI Agent     :p3, 2025-06-01, 14d
    Document Summarizer         :p4, after p3, 14d
    Prompt Engineering Lab      :p5, after p4, 14d

    section Phase 2: Intermediate
    Multi-Agent Research Crew   :p6, after p5, 21d
    AI Code Review Agent        :p7, after p6, 18d
    Voice AI Assistant          :p8, after p7, 21d
    Knowledge Graph RAG         :p9, after p8, 21d
    AI Workflow Automation       :p10, after p9, 21d
    Agent Memory System         :p11, after p10, 18d

    section Phase 3: Advanced
    Autonomous Browser Agent    :p12, after p11, 25d
    AI SaaS Platform            :p13, after p12, 28d
    Vision AI Processor         :p14, after p13, 21d
    LLM Fine-Tuning Pipeline    :p15, after p14, 25d
    AI DevOps Agent             :p16, after p15, 25d
    Local LLM Platform          :p17, after p16, 21d

    section Phase 4: Enterprise
    Enterprise RAG Platform     :p18, after p17, 28d
    AI Eval Framework           :p19, after p18, 25d
    Multi-Agent Orchestrator    :p20, after p19, 28d
    AI Security Agent           :p21, after p20, 25d

    section Phase 5: Research
    Self-Improving Agent        :p22, after p21, 28d
    AI Agent Marketplace        :p23, after p22, 28d
    Edge AI System              :p24, after p23, 25d
    AI Finance Agent            :p25, after p24, 25d
```

---

## Project Status Dashboard

| # | Project | Phase | Status | Dependencies | Key Skill |
|---|---------|-------|--------|--------------|-----------|
| 1 | RAG LangChain Chroma | 🟢 Beginner | ✅ Done | — | RAG, LangChain |
| 2 | RAG Custom Engine | 🟢 Beginner | ✅ Done | — | RAG internals |
| 3 | Conversational AI Agent | 🟢 Beginner | � In Progress | — | ReAct, tools |
| 4 | Document Summarizer | 🟢 Beginner | 🔴 Not Started | — | NLP pipelines |
| 5 | Prompt Engineering Lab | 🟢 Beginner | 🔴 Not Started | — | Prompt design |
| 6 | Multi-Agent Research Crew | 🔵 Intermediate | 🔴 Not Started | 1, 3 | Multi-agent |
| 7 | AI Code Review Agent | 🔵 Intermediate | 🔴 Not Started | 3 | Code analysis |
| 8 | Voice AI Assistant | 🔵 Intermediate | 🔴 Not Started | 3 | Voice, real-time |
| 9 | Knowledge Graph RAG | 🔵 Intermediate | 🔴 Not Started | 2 | Graph DB, multi-hop |
| 10 | AI Workflow Automation | 🔵 Intermediate | 🔴 Not Started | — | Workflow engines |
| 11 | Agent Memory System | 🔵 Intermediate | 🔴 Not Started | — | Memory architecture |
| 12 | Autonomous Browser Agent | 🟠 Advanced | 🔴 Not Started | 3 | Browser automation |
| 13 | AI SaaS Platform | 🟠 Advanced | 🔴 Not Started | 8 | SaaS, billing |
| 14 | Vision AI Processor | 🟠 Advanced | 🔴 Not Started | 4 | Vision, OCR |
| 15 | LLM Fine-Tuning Pipeline | 🟠 Advanced | 🔴 Not Started | — | Fine-tuning |
| 16 | AI DevOps Agent | 🟠 Advanced | 🔴 Not Started | 7 | DevOps, monitoring |
| 17 | Local LLM Platform | 🟠 Advanced | 🔴 Not Started | 15 | ML infra |
| 18 | Enterprise RAG Platform | 🔴 Enterprise | 🔴 Not Started | 9 | Enterprise arch |
| 19 | AI Eval Framework | 🔴 Enterprise | 🔴 Not Started | 5 | Testing, LLMOps |
| 20 | Multi-Agent Orchestrator | 🔴 Enterprise | 🔴 Not Started | 6, 10 | Orchestration |
| 21 | AI Security Agent | 🔴 Enterprise | 🔴 Not Started | 16 | AI security |
| 22 | Self-Improving Agent | 🟣 Research | 🔴 Not Started | 11 | Meta-learning |
| 23 | AI Agent Marketplace | 🟣 Research | 🔴 Not Started | 12, 13, 20 | Platforms |
| 24 | Edge AI System | 🟣 Research | 🔴 Not Started | 17 | Edge, federated |
| 25 | AI Finance Agent | 🟣 Research | 🔴 Not Started | 18 | FinTech |

---

## Skill Progression

```mermaid
graph LR
    subgraph "Foundation Skills"
        S1[Python/FastAPI]
        S2[RAG/Retrieval]
        S3[Prompt Engineering]
    end

    subgraph "Core AI Skills"
        S4[Agent Architecture]
        S5[Multi-Agent Systems]
        S6[Memory Systems]
    end

    subgraph "Advanced Skills"
        S7[Production Systems]
        S8[Infrastructure]
        S9[Security]
    end

    subgraph "Expert Skills"
        S10[Platform Engineering]
        S11[Research & Innovation]
    end

    S1 --> S4
    S2 --> S4
    S3 --> S4
    S4 --> S5
    S4 --> S6
    S5 --> S7
    S6 --> S7
    S7 --> S8
    S7 --> S9
    S8 --> S10
    S9 --> S10
    S10 --> S11
```

---

## Next Steps

1. **Start with Project 3** (Conversational AI Agent) — it unlocks the most downstream projects
2. Focus on one project at a time — depth beats breadth
3. Each project should be demo-ready before moving to the next
4. Update this roadmap as projects complete

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Completed |
| 🔴 | Not Started |
| 🟡 | In Progress |
| 🟢 | Beginner Phase |
| 🔵 | Intermediate Phase |
| 🟠 | Advanced Phase |
| 🔴 | Enterprise Phase |
| 🟣 | Research Phase |
