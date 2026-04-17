package autonomyx.gateway

import rego.v1

default allow := false

allow if {
    count(deny_reasons) == 0
}

deny_reasons contains "agent_not_active" if {
    input.agent.status != "active"
}

deny_reasons contains "ephemeral_agent_expired" if {
    input.agent.type == "ephemeral"
    input.agent.expires_at != null
    time.parse_rfc3339_ns(input.agent.expires_at) < time.now_ns()
}

deny_reasons contains "mcp_tool_agent_expired" if {
    input.agent.type == "mcp_tool"
    input.agent.expires_at != null
    time.parse_rfc3339_ns(input.agent.expires_at) < time.now_ns()
}

deny_reasons contains "budget_exceeded" if {
    input.agent.spend_this_period >= input.agent.budget_limit
}

default budget_warning := false

budget_warning if {
    input.agent.spend_this_period >= (input.agent.budget_limit * 0.9)
    input.agent.spend_this_period < input.agent.budget_limit
}

deny_reasons contains "tpm_limit_exceeded" if {
    input.agent.tpm_used_last_minute >= input.agent.tpm_limit
}

deny_reasons contains "local_model_available_use_local" if {
    input.model.location == "cloud"
    input.system.local_models_healthy == true
    not cloud_exception_applies
}

cloud_exception_applies if {
    input.model.alias == "vertex/gemini-2.5-pro"
    input.agent.name in ["policy-creator"]
}

cloud_exception_applies if {
    input.model.location == "cloud"
    input.system.local_models_healthy == false
}

deny_reasons contains "dpdp_pii_to_us_cloud_prohibited" if {
    input.request.contains_pii == true
    input.model.location == "cloud"
    input.model.provider in ["groq", "openai", "anthropic"]
}

deny_reasons contains "dpdp_pii_to_vertex_us_prohibited" if {
    input.request.contains_pii == true
    input.model.provider == "vertex"
    input.model.region == "us-central1"
}

deny_reasons contains "prompt_too_large_for_model" if {
    input.request.prompt_length > 100000
    not input.model.alias in [
        "ollama/gemma3:9b",
        "vertex/gemini-2.5-pro",
        "vertex/gemini-2.5-flash"
    ]
}

deny_reasons contains "ephemeral_agent_cloud_not_allowed" if {
    input.agent.type == "ephemeral"
    input.model.location == "cloud"
}

decision_metadata := {
    "agent":          input.agent.name,
    "model":          input.model.alias,
    "allow":          allow,
    "deny_reasons":   deny_reasons,
    "budget_warning": budget_warning,
    "evaluated_at":   time.now_ns(),
}
