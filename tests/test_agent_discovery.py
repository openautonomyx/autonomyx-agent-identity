"""tests/test_agent_discovery.py — Agent Auth Protocol discovery tests."""

import pytest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestDiscoveryModule:

    def test_import(self):
        from agent_discovery import router, agent_configuration
        assert router is not None

    def test_router_has_discovery_route(self):
        from agent_discovery import router
        paths = [r.path for r in router.routes]
        assert "/.well-known/agent-configuration" in paths
        assert "/.well-known/agent-configuration.json" in paths


class TestDiscoveryDocument:

    @pytest.mark.asyncio
    async def test_returns_valid_document(self):
        from agent_discovery import agent_configuration
        doc = await agent_configuration()
        assert isinstance(doc, dict)

    @pytest.mark.asyncio
    async def test_required_fields_present(self):
        from agent_discovery import agent_configuration
        doc = await agent_configuration()
        required = [
            "issuer", "provider_name", "provider_description",
            "modes", "authn_methods", "registration",
            "capabilities", "endpoints", "authorization",
        ]
        for field in required:
            assert field in doc, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_modes_correct(self):
        from agent_discovery import agent_configuration
        doc = await agent_configuration()
        assert "autonomous" in doc["modes"]
        assert "delegated" in doc["modes"]

    @pytest.mark.asyncio
    async def test_all_12_capabilities(self):
        from agent_discovery import agent_configuration
        doc = await agent_configuration()
        names = [c["name"] for c in doc["capabilities"]]
        required = [
            "llm_inference", "model_recommendation", "fraud_detection",
            "policy_creation", "policy_review", "code_review",
            "feature_gap_analysis", "saas_evaluation", "web_scraping",
            "structured_data_parsing", "translation", "feedback",
        ]
        for cap in required:
            assert cap in names, f"Missing capability: {cap}"

    @pytest.mark.asyncio
    async def test_translation_has_22_languages(self):
        from agent_discovery import agent_configuration
        doc = await agent_configuration()
        translation = next(c for c in doc["capabilities"] if c["name"] == "translation")
        assert len(translation["languages"]) == 22

    @pytest.mark.asyncio
    async def test_registration_endpoint_present(self):
        from agent_discovery import agent_configuration
        doc = await agent_configuration()
        assert "endpoint" in doc["registration"]
        assert "agents/create" in doc["registration"]["endpoint"]

    @pytest.mark.asyncio
    async def test_all_lifecycle_endpoints_present(self):
        from agent_discovery import agent_configuration
        doc = await agent_configuration()
        endpoints = doc["endpoints"]
        for ep in ["register", "execute", "models", "health", "discovery"]:
            assert ep in endpoints, f"Missing endpoint: {ep}"

    @pytest.mark.asyncio
    async def test_authorization_model_documented(self):
        from agent_discovery import agent_configuration
        doc = await agent_configuration()
        authz = doc["authorization"]
        assert "OpenFGA" in authz["rbac"]
        assert "OPA" in authz["conditions"]
        assert "DPDP Act 2023" in authz["compliance"]

    @pytest.mark.asyncio
    async def test_dpdp_compliance_listed(self):
        from agent_discovery import agent_configuration
        doc = await agent_configuration()
        compliance = doc["authorization"]["compliance"]
        assert "DPDP Act 2023" in compliance
        assert "GDPR" in compliance

    @pytest.mark.asyncio
    async def test_mcp_capability_present(self):
        from agent_discovery import agent_configuration
        doc = await agent_configuration()
        mcp = next((c for c in doc["capabilities"] if c["name"] == "mcp_tools"), None)
        assert mcp is not None
        assert mcp["protocol"] == "mcp"

    @pytest.mark.asyncio
    async def test_openai_compatible_flag(self):
        from agent_discovery import agent_configuration
        doc = await agent_configuration()
        llm = next(c for c in doc["capabilities"] if c["name"] == "llm_inference")
        assert llm["openai_compatible"] is True

    @pytest.mark.asyncio
    async def test_schema_version_present(self):
        from agent_discovery import agent_configuration
        doc = await agent_configuration()
        assert "schema_version" in doc
        assert "agent_auth_protocol_version" in doc
