import { PlaceholderPage } from "@/components/console/PlaceholderPage";
export default function Page() {
  return <PlaceholderPage title="Integrations" subtitle="Connection status and setup guidance for enforcement and identity dependencies." items={["OpenFGA tuple model and store status", "OPA bundle and decision endpoint status", "Keycloak realm and client provisioning", "APISIX, SCIM, SIEM, and webhook consumers"]} />;
}
