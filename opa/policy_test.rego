package autonomyx.gateway_test

import rego.v1
import data.autonomyx.gateway

# ─────────────────────────────────────────────────────────────────────────────
# Test helpers
# ─────────────────────────────────────────────────────────────────────────────

base_input := {
    "agent": {
        "name":                  "fraud-sentinel",
        "type":                  "workflow",
        "tenant_id":             "tenant-acme",
        "budget_limit":          5.0,
        "spend_this_period":     1.0,
        "tpm_limit":             10000,
        "tpm_used_last_minute":  1000,
        "expires_at":            null,
        "status":                "active",
    },
    "model": {
        "alias":    "ollama/qwen3:30b-a3b",
        "location": "local",
        "provider": "ollama",
        "healthy":  true,
        "region":   "local",
    },
    "request": {
        "prompt_length":  512,
        "contains_pii":   false,
        "language":       "en",
        "timestamp_utc":  "2026-04-16T07:30:00Z",
    },
    "system": {
        "local_models_healthy": true,
        "current_hour_utc":     7,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Rule 1: Active agent
# ─────────────────────────────────────────────────────────────────────────────

test_active_agent_allowed if {
    gateway.allow with input as base_input
}

test_suspended_agent_denied if {
    input_data := object.union(base_input, {"agent": object.union(base_input.agent, {"status": "suspended"})})
    not gateway.allow with input as input_data
    "agent_not_active" in gateway.deny_reasons with input as input_data
}

test_revoked_agent_denied if {
    input_data := object.union(base_input, {"agent": object.union(base_input.agent, {"status": "revoked"})})
    not gateway.allow with input as input_data
    "agent_not_active" in gateway.deny_reasons with input as input_data
}

# ─────────────────────────────────────────────────────────────────────────────
# Rule 3: Budget enforcement
# ─────────────────────────────────────────────────────────────────────────────

test_within_budget_allowed if {
    input_data := object.union(base_input, {"agent": object.union(base_input.agent, {
        "spend_this_period": 4.9,
        "budget_limit": 5.0,
    })})
    gateway.allow with input as input_data
}

test_budget_exactly_at_limit_denied if {
    input_data := object.union(base_input, {"agent": object.union(base_input.agent, {
        "spend_this_period": 5.0,
        "budget_limit": 5.0,
    })})
    not gateway.allow with input as input_data
    "budget_exceeded" in gateway.deny_reasons with input as input_data
}

test_budget_exceeded_denied if {
    input_data := object.union(base_input, {"agent": object.union(base_input.agent, {
        "spend_this_period": 6.0,
        "budget_limit": 5.0,
    })})
    not gateway.allow with input as input_data
    "budget_exceeded" in gateway.deny_reasons with input as input_data
}

test_budget_warning_near_limit if {
    input_data := object.union(base_input, {"agent": object.union(base_input.agent, {
        "spend_this_period": 4.6,
        "budget_limit": 5.0,
    })})
    gateway.budget_warning with input as input_data
    gateway.allow with input as input_data  # warning does not block
}

# ─────────────────────────────────────────────────────────────────────────────
# Rule 4: TPM rate limit
# ─────────────────────────────────────────────────────────────────────────────

test_within_tpm_allowed if {
    input_data := object.union(base_input, {"agent": object.union(base_input.agent, {
        "tpm_used_last_minute": 9999,
        "tpm_limit": 10000,
    })})
    gateway.allow with input as input_data
}

test_tpm_exceeded_denied if {
    input_data := object.union(base_input, {"agent": object.union(base_input.agent, {
        "tpm_used_last_minute": 10000,
        "tpm_limit": 10000,
    })})
    not gateway.allow with input as input_data
    "tpm_limit_exceeded" in gateway.deny_reasons with input as input_data
}

# ─────────────────────────────────────────────────────────────────────────────
# Rule 5: Local-first routing
# ─────────────────────────────────────────────────────────────────────────────

test_local_model_always_allowed if {
    gateway.allow with input as base_input
}

test_cloud_denied_when_local_healthy if {
    input_data := object.union(base_input, {
        "model": {
            "alias":    "groq/llama3-70b-8192",
            "location": "cloud",
            "provider": "groq",
            "healthy":  true,
            "region":   "us",
        },
        "system": {"local_models_healthy": true, "current_hour_utc": 7},
    })
    not gateway.allow with input as input_data
    "local_model_available_use_local" in gateway.deny_reasons with input as input_data
}

test_cloud_allowed_when_local_unhealthy if {
    input_data := object.union(base_input, {
        "model": {
            "alias":    "groq/llama3-70b-8192",
            "location": "cloud",
            "provider": "groq",
            "healthy":  true,
            "region":   "us",
        },
        "system": {"local_models_healthy": false, "current_hour_utc": 7},
        "request": object.union(base_input.request, {"contains_pii": false}),
    })
    gateway.allow with input as input_data
}

# ─────────────────────────────────────────────────────────────────────────────
# Rule 6: DPDP PII compliance
# ─────────────────────────────────────────────────────────────────────────────

test_pii_to_local_allowed if {
    input_data := object.union(base_input, {
        "request": object.union(base_input.request, {"contains_pii": true}),
    })
    gateway.allow with input as input_data
}

test_pii_to_groq_denied if {
    input_data := {
        "agent": object.union(base_input.agent, {}),
        "model": {
            "alias":    "groq/llama3-70b-8192",
            "location": "cloud",
            "provider": "groq",
            "healthy":  true,
            "region":   "us",
        },
        "request": object.union(base_input.request, {"contains_pii": true}),
        "system": {"local_models_healthy": false, "current_hour_utc": 7},
    }
    not gateway.allow with input as input_data
    "dpdp_pii_to_us_cloud_prohibited" in gateway.deny_reasons with input as input_data
}

test_pii_to_openai_denied if {
    input_data := {
        "agent": object.union(base_input.agent, {}),
        "model": {
            "alias":    "gpt-4o",
            "location": "cloud",
            "provider": "openai",
            "healthy":  true,
            "region":   "us",
        },
        "request": object.union(base_input.request, {"contains_pii": true}),
        "system": {"local_models_healthy": false, "current_hour_utc": 7},
    }
    not gateway.allow with input as input_data
    "dpdp_pii_to_us_cloud_prohibited" in gateway.deny_reasons with input as input_data
}

test_pii_to_vertex_us_denied if {
    input_data := {
        "agent": object.union(base_input.agent, {}),
        "model": {
            "alias":    "vertex/gemini-2.5-pro",
            "location": "cloud",
            "provider": "vertex",
            "healthy":  true,
            "region":   "us-central1",
        },
        "request": object.union(base_input.request, {"contains_pii": true}),
        "system": {"local_models_healthy": false, "current_hour_utc": 7},
    }
    not gateway.allow with input as input_data
    "dpdp_pii_to_vertex_us_prohibited" in gateway.deny_reasons with input as input_data
}

# ─────────────────────────────────────────────────────────────────────────────
# Rule 7: Prompt size
# ─────────────────────────────────────────────────────────────────────────────

test_large_prompt_denied_on_small_model if {
    input_data := object.union(base_input, {
        "request": object.union(base_input.request, {"prompt_length": 150000}),
    })
    not gateway.allow with input as input_data
    "prompt_too_large_for_model" in gateway.deny_reasons with input as input_data
}

test_large_prompt_allowed_on_gemini if {
    input_data := {
        "agent": object.union(base_input.agent, {}),
        "model": {
            "alias":    "vertex/gemini-2.5-pro",
            "location": "cloud",
            "provider": "vertex",
            "healthy":  true,
            "region":   "us-central1",
        },
        "request": object.union(base_input.request, {
            "prompt_length": 150000,
            "contains_pii":  false,
        }),
        "system": {"local_models_healthy": false, "current_hour_utc": 7},
    }
    # DPDP rule still applies but no PII so it's fine
    # large prompt IS allowed on gemini
    not "prompt_too_large_for_model" in gateway.deny_reasons with input as input_data
}

# ─────────────────────────────────────────────────────────────────────────────
# Rule 8: Ephemeral agents — local only
# ─────────────────────────────────────────────────────────────────────────────

test_ephemeral_local_allowed if {
    input_data := object.union(base_input, {
        "agent": object.union(base_input.agent, {"type": "ephemeral"}),
    })
    gateway.allow with input as input_data
}

test_ephemeral_cloud_denied if {
    input_data := {
        "agent": object.union(base_input.agent, {"type": "ephemeral"}),
        "model": {
            "alias":    "groq/llama3-70b-8192",
            "location": "cloud",
            "provider": "groq",
            "healthy":  true,
            "region":   "us",
        },
        "request": base_input.request,
        "system": {"local_models_healthy": false, "current_hour_utc": 7},
    }
    not gateway.allow with input as input_data
    "ephemeral_agent_cloud_not_allowed" in gateway.deny_reasons with input as input_data
}

# ─────────────────────────────────────────────────────────────────────────────
# Metadata
# ─────────────────────────────────────────────────────────────────────────────

test_metadata_always_present if {
    meta := gateway.decision_metadata with input as base_input
    meta.agent == "fraud-sentinel"
    meta.model == "ollama/qwen3:30b-a3b"
    meta.allow == true
}
