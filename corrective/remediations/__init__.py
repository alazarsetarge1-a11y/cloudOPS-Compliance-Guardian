"""Per-check remediation handlers. Each is a transport-agnostic pure function
``(finding, session, *, apply) -> RemediationResult`` registered in
``corrective.registry`` against exactly one ``check_id``.
"""
