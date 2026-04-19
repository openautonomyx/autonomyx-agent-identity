import { MarketingPage } from "@/components/marketing/MarketingPage";
export default function Page() {
  return <MarketingPage title="Architecture" subtitle="Built for layered policy enforcement and composable integrations." bullets={["FastAPI service plane for identity and control APIs", "OpenFGA relationship graph for authorization", "OPA for dynamic policy and contextual deny rules", "Keycloak, APISIX, SCIM, and SIEM integration points"]} />;
}
