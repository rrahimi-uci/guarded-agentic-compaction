# Live OpenAI Agents SDK benchmark

Generated: `2026-08-02T21:27:13-0700`  
Model: `gpt-5.6-terra` with reasoning effort `low`  
Substrate: `openai_api_live` using fictional deterministic service fixtures.

These are real provider calls and native Agents SDK traces. Cost is estimated from
[published standard short-context prices](https://developers.openai.com/api/docs/pricing);
it is not an account invoice. The benchmark is small and does not certify production use.

Execution total: **52 workflows**, **244 provider responses**, **285,175 input tokens**, **9,675 output tokens**, and **$0.390910 estimated list-price cost**. Every workflow has a distinct native trace id and passed its scenario outcome contract.

| Demo | Condition | n | Requests | Input tokens | Total tokens | Latency ms | Est. cost USD | Quality | Success |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| support | baseline | 4 | 6.00 | 5787.2 | 6039.0 | 9275.3 | 0.013050 | 1.000 | 1.000 |
| support | compacted | 4 | 1.00 | 1192.8 | 1231.8 | 1072.9 | 0.003448 | 1.000 | 1.000 |
| permissioned_rag | baseline | 4 | 7.00 | 7220.0 | 7730.8 | 9926.2 | 0.016982 | 0.970 | 1.000 |
| permissioned_rag | compacted | 4 | 1.00 | 1755.0 | 1832.2 | 1298.3 | 0.005313 | 0.970 | 1.000 |
| incident_triage | baseline | 4 | 5.00 | 2782.0 | 2928.8 | 5456.8 | 0.007325 | 1.000 | 1.000 |
| incident_triage | compacted | 4 | 1.00 | 741.2 | 767.0 | 1046.4 | 0.001791 | 1.000 | 1.000 |
| mcp_ops | baseline | 2 | 3.00 | 1295.0 | 1395.5 | 4819.9 | 0.003796 | 1.000 | 1.000 |
| mcp_ops | compacted_fallback | 2 | 3.00 | 1296.0 | 1397.0 | 3076.0 | 0.003804 | 1.000 | 1.000 |
| fulfillment | baseline | 4 | 7.00 | 9787.0 | 10024.0 | 9521.3 | 0.005690 | 1.000 | 1.000 |
| fulfillment | compacted | 4 | 2.00 | 3301.0 | 3366.0 | 2180.0 | 0.006161 | 1.000 | 1.000 |
| fulfillment | compacted_loop_refused | 4 | 7.00 | 9797.8 | 10040.2 | 9272.7 | 0.008840 | 1.000 | 1.000 |
| fulfillment | compacted_ood_fallback | 4 | 7.00 | 9787.0 | 10026.2 | 8295.7 | 0.008792 | 1.000 | 1.000 |
| tgws_router | baseline | 4 | 7.00 | 9775.0 | 10008.2 | 8194.9 | 0.005120 | 1.000 | 1.000 |
| tgws_router | routed | 4 | 7.00 | 8072.2 | 8322.0 | 7753.8 | 0.011415 | 1.000 | 1.000 |

## Paired comparison

### support

* **compacted** — requests `83.3% reduction`, input tokens `79.4% reduction`, total tokens `79.6% reduction`, latency `88.4% reduction`, estimated cost `73.6% reduction`. Quality delta `+0.000`; success-rate delta `+0.000`.

### permissioned_rag

* **compacted** — requests `85.7% reduction`, input tokens `75.7% reduction`, total tokens `76.3% reduction`, latency `86.9% reduction`, estimated cost `68.7% reduction`. Quality delta `+0.000`; success-rate delta `+0.000`.

### incident_triage

* **compacted** — requests `80.0% reduction`, input tokens `73.4% reduction`, total tokens `73.8% reduction`, latency `80.8% reduction`, estimated cost `75.5% reduction`. Quality delta `+0.000`; success-rate delta `+0.000`.

### mcp_ops

* **compacted_fallback** — requests `0.0% reduction`, input tokens `0.1% increase`, total tokens `0.1% increase`, latency `36.2% reduction`, estimated cost `0.2% increase`. Quality delta `+0.000`; success-rate delta `+0.000`.

### fulfillment

* **compacted** — requests `71.4% reduction`, input tokens `66.3% reduction`, total tokens `66.4% reduction`, latency `77.1% reduction`, estimated cost `8.3% increase`. Quality delta `+0.000`; success-rate delta `+0.000`.
* **compacted_loop_refused** — requests `0.0% reduction`, input tokens `0.1% increase`, total tokens `0.2% increase`, latency `2.6% reduction`, estimated cost `55.4% increase`. Quality delta `+0.000`; success-rate delta `+0.000`.
* **compacted_ood_fallback** — requests `0.0% reduction`, input tokens `0.0% reduction`, total tokens `0.0% increase`, latency `12.9% reduction`, estimated cost `54.5% increase`. Quality delta `+0.000`; success-rate delta `+0.000`.

### tgws_router

* **routed** — requests `0.0% reduction`, input tokens `17.4% reduction`, total tokens `16.8% reduction`, latency `5.4% reduction`, estimated cost `123.0% increase`. Quality delta `+0.000`; success-rate delta `+0.000`.

## Cost is not tokens

| Demo | Condition | Input tokens | Cached share | Cache writes | Blended $/Mtok |
|---|---|---:|---:|---:|---:|
| support | baseline | 5787 | 21% | 1293 | 2.16 |
| support | compacted | 1193 | 0% | 1190 | 2.80 |
| permissioned_rag | baseline | 7220 | 35% | 1834 | 2.20 |
| permissioned_rag | compacted | 1755 | 0% | 1752 | 2.90 |
| incident_triage | baseline | 2782 | 0% | 0 | 2.50 |
| incident_triage | compacted | 741 | 0% | 0 | 2.34 |
| mcp_ops | baseline | 1295 | 0% | 0 | 2.72 |
| mcp_ops | compacted_fallback | 1296 | 0% | 0 | 2.72 |
| fulfillment | baseline | 9787 | 96% | 370 | 0.57 |
| fulfillment | compacted | 3301 | 38% | 2048 | 1.83 |
| fulfillment | compacted_loop_refused | 9798 | 82% | 1710 | 0.88 |
| fulfillment | compacted_ood_fallback | 9787 | 82% | 1707 | 0.88 |
| tgws_router | baseline | 9775 | 98% | 143 | 0.51 |
| tgws_router | routed | 8072 | 58% | 1465 | 1.37 |

Removing provider turns removes tokens; it does not reliably remove money. A
long-prompt, many-turn baseline amortizes one cache *write* across many cheap
cached reads, while a two-turn compacted run pays the write with nothing left to
amortize it over. Route specialization has the same problem one level up: each
route prompt is a distinct cache prefix, so a fleet that shared one warm prefix
now pays several writes. Both effects shrink as episodes-per-prefix grows, so a
benchmark this small understates the cost advantage of compaction and routing —
but a rarely-exercised route may genuinely never amortize its own write.

## Interpretation boundary

Support, RAG, triage and fulfillment use live OpenAI model calls plus local
read-only service fixtures. Their compacted conditions use the library's actual
`CompactingModel` to emit native function calls without provider inference at
intermediate turns. Three conditions are negative controls whose correct outcome
is *no* compaction: the MCP demo (undeclared tool effects), the fulfillment
loop-bearing artifact (the Model adapter supports straight-line programs only),
and the fulfillment schema-drift case (the hard guard pins `wms_v2`). Each returns
exactly the baseline turn count at unchanged quality, which is the result being
claimed. Fulfillment additionally demonstrates *partial* compaction: its region is
bounded by a mandatory irreversible commitment, so the evidence turns disappear
while the decision turn and the write survive.

Every fulfillment condition shares one instruction. Demos A and B specialize the
compacted prompt to assert the evidence already exists, which is only sound while
compaction is guaranteed; a wrapper that may abstain at any boundary needs an
instruction that is still complete when it does.

Synthetic traces remain only in unit and fault-injection fixtures; they are not
evidence in this report.
