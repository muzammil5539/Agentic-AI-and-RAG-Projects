# Research Notes

## Overview

This document tracks research papers, emerging technologies, and experimental ideas relevant to the AI Engineering Universe projects.

---

## Key Research Areas

### 1. Retrieval-Augmented Generation (RAG)

#### Foundational Papers
| Paper | Key Insight | Relevant Projects |
|-------|-------------|-------------------|
| [RAG: Retrieval-Augmented Generation for Knowledge-Intensive NLP](https://arxiv.org/abs/2005.11401) | Original RAG paper — retrieve then generate | 1, 2, 9, 18 |
| [Self-RAG: Learning to Retrieve, Generate, and Critique](https://arxiv.org/abs/2310.11511) | Agent decides when to retrieve, self-evaluates | 2, 18 |
| [RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval](https://arxiv.org/abs/2401.18059) | Hierarchical summarization for multi-level retrieval | 18 |
| [Corrective RAG (CRAG)](https://arxiv.org/abs/2401.15884) | Self-correcting retrieval with web fallback | 18 |

#### Advanced Techniques
- **Agentic RAG** — Agent decides retrieval strategy dynamically
- **Graph RAG** — Knowledge graph-enhanced retrieval (Project 9)
- **Multi-modal RAG** — Images, tables, code in retrieval
- **Adaptive RAG** — Route queries to different retrieval strategies

---

### 2. AI Agents & Multi-Agent Systems

#### Key Papers
| Paper | Key Insight | Relevant Projects |
|-------|-------------|-------------------|
| [ReAct: Synergizing Reasoning and Acting](https://arxiv.org/abs/2210.03629) | Think-Act-Observe loop | 3, 6, 7, 12 |
| [Toolformer](https://arxiv.org/abs/2302.04761) | LLMs learning to use tools | 3 |
| [AutoGen: Enabling Next-Gen LLM Applications](https://arxiv.org/abs/2308.08155) | Multi-agent conversation framework | 6, 20 |
| [Voyager: An Open-Ended Embodied Agent](https://arxiv.org/abs/2305.16291) | Self-improving agent with skill library | 22 |
| [Generative Agents: Interactive Simulacra](https://arxiv.org/abs/2304.03442) | Memory architecture for persistent agents | 11 |

#### Open Questions
- How to prevent agent loops and infinite recursion?
- What's the optimal communication protocol between agents?
- How to evaluate multi-agent system quality?
- When should agents delegate vs. do themselves?

---

### 3. Memory & Long-Term Learning

#### Architecture Patterns
```
Human Memory Model → AI Agent Memory:

Sensory Memory     → Input Buffer (raw user input)
Short-Term Memory  → Conversation Buffer (last N messages)
Working Memory     → Current Task Context (active retrieval)
Episodic Memory    → Experience Store (past interactions)
Semantic Memory    → Knowledge Base (learned facts)
Procedural Memory  → Skill Library (learned strategies)
```

#### Key Papers
| Paper | Key Insight |
|-------|-------------|
| [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560) | Virtual memory paging for infinite context |
| [Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366) | Learning from past failures |

---

### 4. Evaluation & Testing

#### Metrics for LLM Applications
| Metric | Measures | How |
|--------|----------|-----|
| Faithfulness | Does answer match sources? | LLM-as-Judge |
| Relevance | Is answer on-topic? | LLM-as-Judge |
| Coherence | Is answer well-structured? | LLM-as-Judge |
| Latency | Response time | Timer |
| Cost | API spend | Token counting |
| Hallucination Rate | False claims | Source verification |

#### Frameworks
- **RAGAS** — RAG evaluation metrics
- **DeepEval** — LLM testing framework
- **LangSmith** — Tracing and evaluation
- **Promptfoo** — Prompt testing

---

### 5. Edge AI & Optimization

#### Model Compression Techniques
| Technique | Size Reduction | Quality Loss | Speed Gain |
|-----------|---------------|--------------|------------|
| Quantization (INT8) | 4x | 1-2% | 2-3x |
| Quantization (INT4) | 8x | 3-5% | 3-5x |
| Pruning | 2-5x | 2-5% | 1.5-3x |
| Distillation | 10-100x | 5-15% | 10-50x |
| LoRA (fine-tune) | ~0x (adapter) | Improves | ~0x |

---

## Experimental Ideas

### For Future Projects
1. **Agent swarm optimization** — Agents that breed better prompts through evolution
2. **Semantic cache** — Cache by meaning, not exact match
3. **Speculative decoding for agents** — Predict next agent actions
4. **Cross-lingual RAG** — Retrieve in any language, answer in user's language
5. **Real-time learning agents** — Update behavior from each interaction
6. **Agent debugging tools** — Time-travel debugging for agent decisions

---

## Technology Radar

### Adopt (Use Now)
- LangGraph for agent orchestration
- OpenAI GPT-4o for complex reasoning
- ChromaDB for development vector search
- Docker Compose for deployment

### Trial (Experiment With)
- Ollama for local development
- CrewAI for multi-agent patterns
- Neo4j for knowledge graphs
- vLLM for production serving

### Assess (Watch Closely)
- DSPy for automatic prompt optimization
- Instructor for structured outputs
- LangMem for persistent agent memory
- Browser Use for web agents

### Hold (Not Yet Ready)
- Full AGI agent systems without guardrails
- Unsupervised agent-to-agent networks
- Self-modifying agent code

---

## Reading List (Priority Order)

1. ⭐ [Building LLM Applications for Production](https://huyenchip.com/2023/04/11/llm-engineering.html)
2. ⭐ [Patterns for Building LLM-based Systems](https://eugeneyan.com/writing/llm-patterns/)
3. ⭐ [RAG Survey 2024](https://arxiv.org/abs/2312.10997)
4. [Multi-Agent Systems Survey](https://arxiv.org/abs/2402.01680)
5. [LLM Agents Survey](https://arxiv.org/abs/2309.07864)
6. [AI Agent Security](https://arxiv.org/abs/2401.05459)
7. [Efficient LLM Serving](https://arxiv.org/abs/2309.06180)
