# Finance Governor Design Partner Program

Institutions adopting Finance Governor before general availability receive structured support and co-certification under **FG-ECP**.

## What you get

| Benefit | Detail |
|---------|--------|
| **L5 co-certification** | Joint attestation report (`make fg-certification-external-full`) |
| **Reference architecture** | Spine + 1–2 platforms in your VPC (Helm + optional RDS) |
| **Examiner pack** | Regulatory export samples + chain verify runbook |
| **Roadmap input** | Priority on rail adapters, mesh rules, platform #6 |

## Technical prerequisites

- Kubernetes 1.28+ or Docker Compose pilot
- Postgres 16 (managed RDS or in-cluster)
- OIDC IdP (Keycloak, Auth0, Entra ID)
- Optional: Istio 1.20+, ArgoCD 2.9+

## Pilot timeline (typical)

1. **Week 1** — Standalone platform demo (AlgoFreeze or WireMatch)
2. **Week 2** — Spine-connected staging (`make fg-demo-gold`)
3. **Week 3–4** — Production overlay (RDS, OIDC, FG-ECP attestation)
4. **Ongoing** — SLO review + invariant counter audit

## Deliverables from partner

- Signed FG-ECP attestation JSON per environment
- Completed [partner-checklist.md](../../finance-governor/certification/partner-checklist.md)
- Model risk / compliance sign-off on facet schemas

## Contact

Open a design-partner issue in-repo or use your account team channel. Include target platform (AlgoFreeze, WireMatch, CreditGovern, etc.) and regulatory jurisdiction.

## Related

- [external-certification.md](../../finance-governor/docs/external-certification.md)
- [desirability.md](desirability.md)
