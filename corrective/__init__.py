"""Corrective layer — gated, dry-run-first remediation of detective findings.

Each detective ``check_id`` maps 1:1 to a remediation whose allowed ``Action``
is fixed here at design time. Remediations are transport-agnostic pure functions
(see ``corrective.base``); the FastAPI backend and the MCP ``trigger_remediation``
tool both wrap the same ``remediate`` dispatcher and inherit its ``apply`` gate.
"""
