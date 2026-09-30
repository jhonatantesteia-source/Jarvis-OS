import pytest
import pytest_asyncio
import time
from core.approval.base import (
    ApprovalProvider,
    ApprovalRequest,
    ApprovalResult,
    ApprovalState,
    ApprovalGrant
)
from core.approval.providers.fake import FakeApprovalProvider

@pytest.mark.anyio
async def test_fake_provider_approved():
    provider = FakeApprovalProvider()
    req_id = "req1"
    provider.set_outcome(req_id, ApprovalState.APPROVED)

    request = ApprovalRequest(
        request_id=req_id,
        tool_name="test_tool",
        arguments={"a": 1},
        risk_level=None, # Mocked
        reason="test",
        timestamp=time.time()
    )

    result = await provider.request_approval(request)
    assert result.state == ApprovalState.APPROVED
    assert result.grant is not None
    assert result.grant.request_id == req_id
    assert result.grant.tool_name == "test_tool"

@pytest.mark.anyio
async def test_fake_provider_denied():
    provider = FakeApprovalProvider()
    req_id = "req2"
    provider.set_outcome(req_id, ApprovalState.DENIED)

    request = ApprovalRequest(
        request_id=req_id,
        tool_name="test_tool",
        arguments={},
        risk_level=None,
        reason="test",
        timestamp=time.time()
    )

    result = await provider.request_approval(request)
    assert result.state == ApprovalState.DENIED
    assert result.grant is None
