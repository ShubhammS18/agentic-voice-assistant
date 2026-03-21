# Routing Benchmark Report

Generated: 2026-03-21 12:26

## Overall Results

| Metric | Value |
|--------|-------|
| Overall accuracy | 90.0% (27/30) |
| Average latency | 1282ms per query |

## Per-Domain Accuracy

| Domain | Correct | Total | Accuracy |
|--------|---------|-------|----------|
| rag | 7 | 10 | 70.0% |
| web | 10 | 10 | 100.0% |
| data | 10 | 10 | 100.0% |

## Correctly Routed (27)

| Query | Expected | Got | Latency |
|-------|----------|-----|---------|
| What are the Golden Visa eligibility requirements? | rag | rag | 1650ms |
| Explain the DIFC employment contract rules | rag | rag | 1011ms |
| What does the company policy say about remote work | rag | rag | 1007ms |
| Tell me about the product documentation for onboar | rag | rag | 1101ms |
| Summarise the internal compliance procedures | rag | rag | 1025ms |
| What are the rules according to our internal polic | rag | rag | 1027ms |
| Find information about procedures in the document  | rag | rag | 1227ms |
| What happened in AI news today? | web | web | 949ms |
| What is the current price of NVIDIA stock? | web | web | 902ms |
| What are the latest developments in large language | web | web | 2406ms |
| Who won the election results announced today? | web | web | 916ms |
| What is the weather forecast for this week? | web | web | 1448ms |
| What are the breaking news headlines right now? | web | web | 957ms |
| What did OpenAI announce recently? | web | web | 1166ms |
| What is the latest iPhone model released? | web | web | 1047ms |
| What happened at the AI conference this week? | web | web | 1234ms |
| What are the current interest rates announced toda | web | web | 1109ms |
| What is the tech stack of this system? | data | data | 1266ms |
| What is the latency budget breakdown? | data | data | 1486ms |
| What languages does this system support? | data | data | 1179ms |
| What routing method does this project use? | data | data | 1395ms |
| Which web search provider is used in this project? | data | data | 1099ms |
| What are the configuration values for this system? | data | data | 3554ms |
| What version of the model is being used? | data | data | 1110ms |
| What are the system specifications and settings? | data | data | 841ms |
| What is the supported language for this voice assi | data | data | 1186ms |
| What infrastructure components are in this project | data | data | 943ms |

## Misrouted (3)

| Query | Expected | Got | Sub-queries |
|-------|----------|-----|-------------|
| What are the technical guidelines for API integrat | rag | data | API integration best practices and technical standards 2026; REST API vs GraphQL |
| What does the knowledge base say about data retent | rag | data | data retention policy guidelines; knowledge base data retention requirements; da |
| Explain the historical background from the archive | rag | web | historical background archived documents primary sources; archival records histo |

## Design Notes

- Routing uses semantic embedding similarity (FAISS cosine) — no LLM call
- Query rewriting decomposes ambiguous queries into specific sub-queries first
- Route ms is typically under 50ms — pure local vector math
- Misrouted queries are candidates for domain description tuning