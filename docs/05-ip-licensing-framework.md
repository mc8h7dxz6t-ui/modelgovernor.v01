# IP Licensing Framework — Governor Portfolio

Canonical licensing map for ModelGovernor, Finance Governor, and Cybersecurity Governor.

## Unique IP (licensable primitives)

| IP asset | Governor | Description | Competes with |
|----------|----------|-------------|---------------|
| **Reserve-before-dispatch** | ModelGovernor | Ledger-backed LLM spend control | LiteLLM, Portkey, cloud alerts |
| **Crystal Commit Protocol (CCP)** | Finance Governor | Governance crystal + commit horizon + mesh | GRC suites, payment hubs (post-hoc) |
| **Threat Crystal Protocol (TCP)** | Cybersecurity Governor | Threat crystal + session horizon + mesh | SIEM correlation, IdP alone |
| **Hash-chained audit spine** | All three | `security_events` / `ledger_events` + S3 anchor | Log stores without tamper proof |
| **STRANDED semantics** | All three | Ambiguity → hold, never guess | Retry-heavy systems |
| **Institutional++ test pyramid** | All three | Unit → Postgres → load → Toxiproxy | Point tools without chaos proof |

## Product codes and license bundles

| Code | Product | License tier |
|------|---------|--------------|
| `MG-SPINE` | ModelGovernor control plane | Enterprise AI governance |
| `FG-SPINE` | Finance Governor control plane | Regulated finance ops |
| `CG-SPINE` | Cybersecurity Governor control plane | Security operations governance |
| `MG-PLATFORM-DEMO` through `MG-ADDON-ENTERPRISE-SECURITY` | ModelGovernor deployment SKUs | Per deployment mode |
| `FG-ALGOFREEZE` … `FG-CREDITGOVERN` | Finance wedges | Per use-case |
| `CG-IDENTITYGATE` … `CG-LINEAGEINGEST` | Cyber wedges | Per use-case |
| `CG-POSTURERECONCILE`, `CG-CONTENTGUARD` | Cyber wedges (posture + content) | Per use-case |

## Cybersecurity Governor — licensable differentiators

These are **real shipped mechanisms** on `main`, not roadmap names:

1. **TCP** — crystallize-before-authorize on identity, egress, witness, lineage, posture, content
2. **Threat Mesh** — cross-platform invariants (STRANDED session blocks egress commit)
3. **Witness quorum** — S3 Object Lock anchor + `security_chain_anchors`
4. **Lineage DAG** — structural parent/child edges (Falco/Tetragon/generic)
5. **Shadow Gap closure** — time-skew (hash chain), erasure (witness), mutation (anchor)

## Cybersecurity Governor — licensable wedges (6)

| Code | Platform | Status |
|------|----------|--------|
| `CG-IDENTITYGATE` | Session arm + device binding | ✅ Shipped |
| `CG-EGRESSLOCK` | Egress evaluate gate | ✅ Shipped |
| `CG-WITNESSBRIDGE` | Witness ingest + erasure detect | ✅ Shipped |
| `CG-LINEAGEINGEST` | Lineage DAG ingest | ✅ Shipped |
| `CG-POSTURERECONCILE` | Posture vs baseline at authorize | ✅ Shipped |
| `CG-CONTENTGUARD` | Pre-publish content gate | ✅ Shipped |

## Open-source vs commercial boundary

| Component | License posture |
|-----------|-----------------|
| Core spine patterns | Proprietary — sibling to ModelGovernor |
| Dependencies | See `docs/dependency-licenses.md` |
| PyJWT, FastAPI, SQLAlchemy | Permissive OSS — customer deploys in VPC |

## Submodule grant (typical enterprise deal)

- Non-exclusive, non-transferable right to deploy in customer VPC
- Includes: spine + purchased wedges + K8s manifests + updates for contract term
- Excludes: resale, managed multi-tenant SaaS without separate agreement
- Audit rights: hash chain verify API + invariant report artifacts

## Competitive moat (licensing narrative)

> Incumbents sell **detection volume** or **identity seats**. Cybersecurity Governor licenses **authorization proof** — a tamper-evident chain that answers *under which governed conditions was this action authorized?*

Related: [GOVERNOR-PORTFOLIO.md](sales-sheets/GOVERNOR-PORTFOLIO.md) · [cyber-governor/PLUG-AND-PLAY.md](../cyber-governor/PLUG-AND-PLAY.md)
