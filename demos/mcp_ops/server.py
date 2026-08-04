"""Local stdio MCP server used by the provider-backed negative-control demo.

The records are fictional and read-only.  The point of this server is to exercise
the actual MCP transport and Agents SDK integration, not to imitate a production
CRM endpoint inside the model prompt.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "agent-compaction-multi-tenant-ops",
    instructions="Read-only fictional tenant operations used for a benchmark.",
    log_level="ERROR",
)

ACCOUNTS = {
    ("northwind", "alex@northwind.example"): {
        "customer_id": "cus_nw_1042",
        "tenant": "northwind",
        "email": "alex@northwind.example",
        "status": "active",
    },
    ("contoso", "sam@contoso.example"): {
        "customer_id": "cus_ct_8831",
        "tenant": "contoso",
        "email": "sam@contoso.example",
        "status": "active",
    },
}

SUBSCRIPTIONS = {
    "cus_nw_1042": {"customer_id": "cus_nw_1042", "tier": "enterprise", "seats": 240},
    "cus_ct_8831": {"customer_id": "cus_ct_8831", "tier": "business", "seats": 60},
}


@mcp.tool()
def lookup_customer(tenant: str, email: str) -> dict:
    """Look up one customer within an exact tenant boundary."""

    record = ACCOUNTS.get((tenant, email.lower()))
    if record is None:
        return {"found": False, "tenant": tenant}
    return {"found": True, **record}


@mcp.tool()
def get_subscription(tenant: str, customer_id: str) -> dict:
    """Read a subscription only when the customer belongs to the supplied tenant."""

    account = next(
        (row for row in ACCOUNTS.values() if row["customer_id"] == customer_id),
        None,
    )
    if account is None or account["tenant"] != tenant:
        return {"authorized": False, "tenant": tenant}
    return {"authorized": True, **SUBSCRIPTIONS[customer_id]}


if __name__ == "__main__":
    mcp.run(transport="stdio")
