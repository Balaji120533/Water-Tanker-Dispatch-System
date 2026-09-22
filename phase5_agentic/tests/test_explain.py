import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from explain import explain_decision


def test_explain_decision_without_proof_trace_uses_fixed_message_no_llm_call():
    # empty proof_trace path never calls the LLM -- must not require an API
    # key or network access.
    result = explain_decision("manali", entitled=False, high_priority=False, proof_trace="")
    assert "manali" in result
    assert "does not currently meet" in result
