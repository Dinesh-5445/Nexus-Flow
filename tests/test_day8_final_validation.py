"""
Day 8 - Final Validation and Stabilization
Gateway -> Orchestrator -> Provider/Tool -> Event/State Pipeline

Owner: Dinesh (Gateway, Orchestration, Event flow, Execution state)

Covers:
  1. Successful end-to-end execution (with and without tool calls)
  2. Provider failure path
  3. Tool failure path (execution error, missing tool, bad arguments)
  4. Invalid / malformed request validation
  5. Canonical lifecycle event ordering
  6. State transition correctness
  7. Concurrent execution isolation
  8. Result propagation integrity
  9. Contract freeze verification (Gateway, Orchestrator, Event, State)

No teammate-owned files are modified.
Uses only MockProvider, ToolExecutor, and the EventStream already in the repo.
"""

import asyncio
import dataclasses
import unittest
import uuid

from src.events.schema import Event, EventLifecycle
from src.events.stream import EventStream
from src.gateway.models import GatewayRequest, GatewayResponse
from src.gateway.router import GatewayRouter
from src.orchestration.executor import Orchestrator
from src.providers.base import BaseLLMProvider, LLMResponse, ProviderConfig, ToolCall
from src.providers.mock_provider import MockProvider
from src.state.manager import ExecutionState, StateManager
from src.tools.builtin import CalculatorTool, EchoTool
from src.tools.executor import ToolExecutor
from src.tools.registry import ToolRegistry


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_stack(provider=None, responses=None, with_calc=True, with_echo=False):
    """Build a full Gateway/Orchestrator stack for a single test."""
    registry = ToolRegistry()
    if with_calc:
        registry.register(CalculatorTool())
    if with_echo:
        registry.register(EchoTool())

    tool_executor = ToolExecutor(registry=registry)

    if provider is None:
        mock = MockProvider()
        if responses:
            mock.predefined_responses = list(responses)
        provider = mock

    event_stream = EventStream()
    state_manager = StateManager()
    orchestrator = Orchestrator(
        provider=provider,
        tool_executor=tool_executor,
        event_stream=event_stream,
    )
    gateway = GatewayRouter(
        orchestrator=orchestrator,
        state_manager=state_manager,
        event_stream=event_stream,
    )
    return gateway, state_manager, event_stream


def _user_msg(content):
    return {"role": "user", "content": content}


# ---------------------------------------------------------------------------
# 1. SUCCESSFUL EXECUTION
# ---------------------------------------------------------------------------

class TestSuccessfulExecution(unittest.IsolatedAsyncioTestCase):
    """Full end-to-end success path: request_id preserved, COMPLETED state, correct events."""

    async def test_success_without_tool_call(self):
        """LLM returns a plain text response; no tool execution occurs."""
        gateway, state_manager, event_stream = _make_stack(
            responses=[LLMResponse(content="Hello from mock!", tool_calls=[])],
        )
        request = GatewayRequest(
            request_id="d8-success-notool",
            session_id="sess-notool",
            messages=[_user_msg("Say hello")],
        )
        response = await gateway.handle_request(request)

        # Gateway response contract
        self.assertEqual(response.status, "success")
        self.assertEqual(response.request_id, "d8-success-notool")
        self.assertIsNotNone(response.result)
        self.assertEqual(response.result["content"], "Hello from mock!")
        self.assertEqual(response.result["tool_results"], [])
        self.assertIsInstance(response.execution_time_ms, float)
        self.assertGreaterEqual(response.execution_time_ms, 0.0)

        # State: pending -> running -> completed
        state = state_manager.get_state("d8-success-notool")
        self.assertIsNotNone(state)
        self.assertEqual(state.status, "completed")
        self.assertIsNone(state.error)
        self.assertIsNotNone(state.end_time)

        # Canonical lifecycle event ordering (no tool call)
        types = [e.event_type for e in event_stream.published_events]
        self.assertEqual(types, [
            EventLifecycle.REQUEST_RECEIVED,
            EventLifecycle.EXECUTION_STARTED,
            EventLifecycle.LLM_EXECUTION,
            EventLifecycle.COMPLETED,
        ])

        # All events carry the correct request_id
        for evt in event_stream.published_events:
            self.assertEqual(evt.request_id, "d8-success-notool")

    async def test_success_with_tool_call(self):
        """LLM requests a calculator tool; result propagates through to final response."""
        call_id = "call_d8_tool"
        gateway, state_manager, event_stream = _make_stack(
            responses=[
                LLMResponse(
                    content="Let me compute that.",
                    tool_calls=[
                        ToolCall(id=call_id, name="calculator", arguments={"expression": "7 * 6"})
                    ],
                )
            ],
        )
        request = GatewayRequest(
            request_id="d8-success-tool",
            session_id="sess-tool",
            messages=[_user_msg("What is 7 * 6?")],
        )
        response = await gateway.handle_request(request)

        self.assertEqual(response.status, "success")
        self.assertEqual(response.request_id, "d8-success-tool")
        self.assertEqual(len(response.result["tool_results"]), 1)
        tool_res = response.result["tool_results"][0]
        self.assertEqual(tool_res["status"], "completed")
        self.assertEqual(tool_res["result"]["result"], 42)

        state = state_manager.get_state("d8-success-tool")
        self.assertEqual(state.status, "completed")

        # REQ_REC -> EXEC_STARTED -> LLM_EXEC -> TOOL_EXEC -> COMPLETED
        types = [e.event_type for e in event_stream.published_events]
        self.assertEqual(types, [
            EventLifecycle.REQUEST_RECEIVED,
            EventLifecycle.EXECUTION_STARTED,
            EventLifecycle.LLM_EXECUTION,
            EventLifecycle.TOOL_EXECUTION,
            EventLifecycle.COMPLETED,
        ])

        tool_evt = event_stream.published_events[3]
        self.assertEqual(tool_evt.request_id, "d8-success-tool")
        self.assertEqual(tool_evt.payload["tool_name"], "calculator")
        self.assertEqual(tool_evt.payload["status"], "completed")
        self.assertEqual(tool_evt.payload["request_id"], "d8-success-tool")


# ---------------------------------------------------------------------------
# 2. FAILURE EXECUTION
# ---------------------------------------------------------------------------

class TestFailureExecution(unittest.IsolatedAsyncioTestCase):

    async def test_provider_failure_emits_failed_state_and_event(self):
        """Provider exception -> FAILED state, FAILED event, not stuck at PENDING."""

        class FailingProvider(BaseLLMProvider):
            async def generate(self, messages, tools=None, **kwargs):
                raise RuntimeError("provider down")

        gateway, state_manager, event_stream = _make_stack(
            provider=FailingProvider(config=ProviderConfig(model_name="failing-model"))
        )
        request = GatewayRequest(request_id="d8-prov-fail", messages=[_user_msg("Hello")])
        response = await gateway.handle_request(request)

        self.assertEqual(response.status, "failed")
        self.assertEqual(response.request_id, "d8-prov-fail")
        self.assertIn("provider down", response.error)

        state = state_manager.get_state("d8-prov-fail")
        self.assertIsNotNone(state)
        self.assertEqual(state.status, "failed")
        self.assertNotEqual(state.status, "pending")

        types = [e.event_type for e in event_stream.published_events]
        self.assertEqual(types, [
            EventLifecycle.REQUEST_RECEIVED,
            EventLifecycle.EXECUTION_STARTED,
            EventLifecycle.FAILED,
        ])
        failed_evt = event_stream.published_events[2]
        self.assertEqual(failed_evt.request_id, "d8-prov-fail")
        self.assertIn("provider down", failed_evt.payload["error"])

    async def test_tool_execution_error_does_not_fail_whole_request(self):
        """Tool execution error is contained; overall request still succeeds."""
        gateway, state_manager, event_stream = _make_stack(
            responses=[
                LLMResponse(
                    content="Calculating",
                    tool_calls=[
                        ToolCall(id="call_bad_expr", name="calculator", arguments={"expression": "invalid!"})
                    ],
                )
            ],
        )
        request = GatewayRequest(request_id="d8-tool-error", messages=[_user_msg("Bad expression")])
        response = await gateway.handle_request(request)

        # Overall request succeeds despite tool failure
        self.assertEqual(response.status, "success")
        tool_res = response.result["tool_results"][0]
        self.assertEqual(tool_res["status"], "failed")
        self.assertIsNotNone(tool_res["error"])

        state = state_manager.get_state("d8-tool-error")
        self.assertEqual(state.status, "completed")

        tool_evt = next(
            e for e in event_stream.published_events
            if e.event_type == EventLifecycle.TOOL_EXECUTION
        )
        self.assertEqual(tool_evt.payload["status"], "failed")

    async def test_missing_tool_error_contained(self):
        """Provider requests an unregistered tool; ToolExecutor returns failed, no crash."""
        gateway, state_manager, event_stream = _make_stack(
            responses=[
                LLMResponse(
                    content="Let me call weather",
                    tool_calls=[
                        ToolCall(id="call_w", name="weather_tool", arguments={"city": "NYC"})
                    ],
                )
            ],
            with_calc=False,
        )
        request = GatewayRequest(request_id="d8-missing-tool", messages=[_user_msg("Weather?")])
        response = await gateway.handle_request(request)

        self.assertEqual(response.status, "success")
        tool_res = response.result["tool_results"][0]
        self.assertEqual(tool_res["status"], "failed")
        self.assertIn("not registered", tool_res["error"])

    async def test_orchestration_failure_sets_failed_state_not_pending(self):
        """Any orchestration-level exception transitions state to FAILED, not left as PENDING."""

        class CrashProvider(BaseLLMProvider):
            async def generate(self, messages, tools=None, **kwargs):
                raise ConnectionError("network error")

        gateway, state_manager, event_stream = _make_stack(
            provider=CrashProvider(config=ProviderConfig()),
        )
        response = await gateway.handle_request(
            GatewayRequest(request_id="d8-orch-fail", messages=[_user_msg("Hello")])
        )
        state = state_manager.get_state("d8-orch-fail")
        self.assertNotEqual(state.status, "pending")
        self.assertEqual(state.status, "failed")
        self.assertEqual(response.status, "failed")


# ---------------------------------------------------------------------------
# 3. EVENT VALIDATION
# ---------------------------------------------------------------------------

class TestEventValidation(unittest.IsolatedAsyncioTestCase):
    """Validate canonical lifecycle events: names, ordering, payloads, no duplicates."""

    async def test_no_duplicate_lifecycle_events_in_success_path(self):
        """Each lifecycle event appears exactly once in the no-tool success path."""
        gateway, _, event_stream = _make_stack(
            responses=[LLMResponse(content="ok", tool_calls=[])],
        )
        await gateway.handle_request(GatewayRequest(
            request_id="d8-evt-dup", messages=[_user_msg("test")]
        ))
        types = [e.event_type for e in event_stream.published_events]
        self.assertEqual(types.count(EventLifecycle.REQUEST_RECEIVED), 1)
        self.assertEqual(types.count(EventLifecycle.EXECUTION_STARTED), 1)
        self.assertEqual(types.count(EventLifecycle.LLM_EXECUTION), 1)
        self.assertEqual(types.count(EventLifecycle.COMPLETED), 1)
        self.assertEqual(types.count(EventLifecycle.FAILED), 0)

    async def test_request_received_payload_contains_session_and_message_count(self):
        gateway, _, event_stream = _make_stack(
            responses=[LLMResponse(content="ok", tool_calls=[])],
        )
        await gateway.handle_request(GatewayRequest(
            request_id="d8-evt-rr",
            session_id="sess-rr",
            messages=[_user_msg("msg1"), _user_msg("msg2")],
        ))
        rr_evt = next(e for e in event_stream.published_events
                      if e.event_type == EventLifecycle.REQUEST_RECEIVED)
        self.assertEqual(rr_evt.payload["session_id"], "sess-rr")
        self.assertEqual(rr_evt.payload["messages_count"], 2)

    async def test_execution_started_payload_contains_provider_model(self):
        prov = MockProvider(config=ProviderConfig(model_name="mock-v2"))
        prov.predefined_responses = [LLMResponse(content="ok", tool_calls=[])]
        gateway, _, event_stream = _make_stack(provider=prov)
        await gateway.handle_request(GatewayRequest(
            request_id="d8-evt-es", messages=[_user_msg("hello")]
        ))
        es_evt = next(e for e in event_stream.published_events
                      if e.event_type == EventLifecycle.EXECUTION_STARTED)
        self.assertEqual(es_evt.payload["provider_model"], "mock-v2")

    async def test_llm_execution_payload_contains_model_and_usage(self):
        gateway, _, event_stream = _make_stack(
            responses=[LLMResponse(
                content="done",
                tool_calls=[],
                model="mock-v2",
                usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
            )],
        )
        await gateway.handle_request(GatewayRequest(
            request_id="d8-evt-llm", messages=[_user_msg("hi")]
        ))
        llm_evt = next(e for e in event_stream.published_events
                       if e.event_type == EventLifecycle.LLM_EXECUTION)
        self.assertIn("usage", llm_evt.payload)
        self.assertIn("model", llm_evt.payload)

    async def test_failed_event_contains_error_string(self):
        class ErrProvider(BaseLLMProvider):
            async def generate(self, messages, tools=None, **kwargs):
                raise ValueError("validation error detail")

        gateway, _, event_stream = _make_stack(provider=ErrProvider(config=ProviderConfig()))
        await gateway.handle_request(GatewayRequest(
            request_id="d8-evt-fail", messages=[_user_msg("hi")]
        ))
        failed_evt = next(
            (e for e in event_stream.published_events if e.event_type == EventLifecycle.FAILED), None
        )
        self.assertIsNotNone(failed_evt)
        self.assertIn("validation error detail", failed_evt.payload["error"])

    async def test_event_schema_to_dict_contract(self):
        """Event.to_dict() produces the canonical key set."""
        evt = Event(
            event_type=EventLifecycle.REQUEST_RECEIVED,
            request_id="d8-contract-evt",
            payload={"key": "val"},
        )
        d = evt.to_dict()
        self.assertEqual(set(d.keys()), {"event_type", "request_id", "timestamp", "payload"})
        self.assertEqual(d["event_type"], "request_received")
        self.assertIsInstance(d["timestamp"], float)


# ---------------------------------------------------------------------------
# 4. STATE VALIDATION
# ---------------------------------------------------------------------------

class TestStateValidation(unittest.IsolatedAsyncioTestCase):
    """Validate StateManager lifecycle transitions for every execution path."""

    def test_initial_state_is_pending(self):
        sm = StateManager()
        state = sm.create_state("d8-state-init")
        self.assertEqual(state.status, "pending")
        self.assertIsNone(state.end_time)
        self.assertIsNone(state.error)
        self.assertEqual(state.request_id, "d8-state-init")

    async def test_success_path_state_lifecycle(self):
        gateway, state_manager, _ = _make_stack(
            responses=[LLMResponse(content="ok", tool_calls=[])],
        )
        await gateway.handle_request(GatewayRequest(
            request_id="d8-state-success", messages=[_user_msg("hi")]
        ))
        state = state_manager.get_state("d8-state-success")
        self.assertEqual(state.status, "completed")
        self.assertIsNotNone(state.end_time)
        self.assertIsNone(state.error)

    async def test_failure_path_state_lifecycle(self):
        class Fail(BaseLLMProvider):
            async def generate(self, messages, tools=None, **kwargs):
                raise RuntimeError("deliberate failure")

        gateway, state_manager, _ = _make_stack(provider=Fail(config=ProviderConfig()))
        await gateway.handle_request(GatewayRequest(
            request_id="d8-state-fail", messages=[_user_msg("hi")]
        ))
        state = state_manager.get_state("d8-state-fail")
        self.assertEqual(state.status, "failed")
        self.assertIsNotNone(state.end_time)
        self.assertIsNotNone(state.error)
        self.assertIn("deliberate failure", state.error)

    def test_state_manager_update_returns_none_for_unknown_request(self):
        sm = StateManager()
        result = sm.update_state("nonexistent-id", "completed")
        self.assertIsNone(result)

    def test_state_manager_get_returns_none_for_unknown_request(self):
        sm = StateManager()
        self.assertIsNone(sm.get_state("ghost-id"))

    async def test_error_propagation_in_state(self):
        """State.error is set to the exact exception message on failure."""
        class Fail(BaseLLMProvider):
            async def generate(self, messages, tools=None, **kwargs):
                raise ValueError("exact error message 42")

        gateway, state_manager, _ = _make_stack(provider=Fail(config=ProviderConfig()))
        await gateway.handle_request(GatewayRequest(
            request_id="d8-state-errmsg", messages=[_user_msg("hi")]
        ))
        state = state_manager.get_state("d8-state-errmsg")
        self.assertEqual(state.error, "exact error message 42")


# ---------------------------------------------------------------------------
# 5. EXECUTION ISOLATION (CONCURRENT)
# ---------------------------------------------------------------------------

class TestExecutionIsolation(unittest.IsolatedAsyncioTestCase):

    async def test_concurrent_success_executions_are_independent(self):
        """Two concurrent requests share nothing: IDs, states, and results are isolated."""
        gateway, state_manager, event_stream = _make_stack(
            responses=[
                LLMResponse(content="Result A", tool_calls=[]),
                LLMResponse(content="Result B", tool_calls=[]),
            ],
        )
        req_a = GatewayRequest(request_id="d8-iso-A", messages=[_user_msg("Req A")])
        req_b = GatewayRequest(request_id="d8-iso-B", messages=[_user_msg("Req B")])

        resp_a, resp_b = await asyncio.gather(
            gateway.handle_request(req_a),
            gateway.handle_request(req_b),
        )

        self.assertEqual(resp_a.request_id, "d8-iso-A")
        self.assertEqual(resp_b.request_id, "d8-iso-B")
        self.assertEqual(resp_a.result["content"], "Result A")
        self.assertEqual(resp_b.result["content"], "Result B")

        state_a = state_manager.get_state("d8-iso-A")
        state_b = state_manager.get_state("d8-iso-B")
        self.assertEqual(state_a.status, "completed")
        self.assertEqual(state_b.status, "completed")

        evts_a = [e for e in event_stream.published_events if e.request_id == "d8-iso-A"]
        evts_b = [e for e in event_stream.published_events if e.request_id == "d8-iso-B"]
        # REQ_REC, EXEC_START, LLM_EXEC, COMPLETED = 4 events each
        self.assertEqual(len(evts_a), 4)
        self.assertEqual(len(evts_b), 4)

    async def test_failure_in_one_does_not_corrupt_sibling(self):
        """A failure in request A does not affect a concurrent successful request B."""

        class OnceFail(BaseLLMProvider):
            _called = False

            async def generate(self, messages, tools=None, **kwargs):
                if not OnceFail._called:
                    OnceFail._called = True
                    raise RuntimeError("first call fails")
                return LLMResponse(content="B is fine", tool_calls=[])

        gateway, state_manager, event_stream = _make_stack(
            provider=OnceFail(config=ProviderConfig()),
        )
        req_a = GatewayRequest(request_id="d8-fail-iso-A", messages=[_user_msg("A")])
        req_b = GatewayRequest(request_id="d8-fail-iso-B", messages=[_user_msg("B")])

        resp_a, resp_b = await asyncio.gather(
            gateway.handle_request(req_a),
            gateway.handle_request(req_b),
        )

        results = {resp_a.status, resp_b.status}
        self.assertIn("failed", results)
        self.assertIn("success", results)

        # Each response's state must match its own outcome
        for resp in [resp_a, resp_b]:
            state = state_manager.get_state(resp.request_id)
            self.assertIsNotNone(state)
            expected_status = "completed" if resp.status == "success" else "failed"
            self.assertEqual(state.status, expected_status)

    async def test_concurrent_tool_executions_produce_correct_results(self):
        """Concurrent requests with tool calls each return the correct tool result."""
        gateway, state_manager, event_stream = _make_stack(
            responses=[
                LLMResponse(
                    content="Calc",
                    tool_calls=[ToolCall(id="c1", name="calculator", arguments={"expression": "3 + 3"})],
                ),
                LLMResponse(
                    content="Calc",
                    tool_calls=[ToolCall(id="c2", name="calculator", arguments={"expression": "10 * 10"})],
                ),
            ],
        )
        req_x = GatewayRequest(request_id="d8-conc-X", messages=[_user_msg("3+3")])
        req_y = GatewayRequest(request_id="d8-conc-Y", messages=[_user_msg("10*10")])

        resp_x, resp_y = await asyncio.gather(
            gateway.handle_request(req_x),
            gateway.handle_request(req_y),
        )

        all_results = {
            resp_x.result["tool_results"][0]["result"]["result"],
            resp_y.result["tool_results"][0]["result"]["result"],
        }
        self.assertEqual(all_results, {6, 100})


# ---------------------------------------------------------------------------
# 6. REQUEST VALIDATION
# ---------------------------------------------------------------------------

class TestRequestValidation(unittest.IsolatedAsyncioTestCase):

    async def test_empty_request_id_returns_failed_with_unknown_id(self):
        """Empty string request_id -> status 'failed', request_id 'unknown'."""
        gateway, _, _ = _make_stack()
        response = await gateway.handle_request(
            GatewayRequest(request_id="", messages=[_user_msg("hi")])
        )
        self.assertEqual(response.status, "failed")
        self.assertEqual(response.request_id, "unknown")
        self.assertIn("missing request_id", response.error.lower())

    async def test_none_request_id_returns_failed(self):
        """request_id=None should be rejected cleanly."""
        gateway, _, _ = _make_stack()
        req = GatewayRequest(request_id="placeholder", messages=[_user_msg("hi")])
        req.request_id = None
        response = await gateway.handle_request(req)
        self.assertEqual(response.status, "failed")
        self.assertEqual(response.request_id, "unknown")

    async def test_malformed_message_structure_causes_failure(self):
        """Message dicts missing required keys cause a clean failure, not a crash."""
        gateway, state_manager, _ = _make_stack()
        response = await gateway.handle_request(
            GatewayRequest(
                request_id="d8-bad-msg",
                messages=[{"no_role": "x", "no_content": "y"}],
            )
        )
        self.assertEqual(response.status, "failed")
        self.assertIsNotNone(response.error)
        state = state_manager.get_state("d8-bad-msg")
        self.assertIsNotNone(state)
        self.assertEqual(state.status, "failed")

    async def test_valid_minimal_request_succeeds(self):
        """Minimal valid GatewayRequest (no session_id, no params) succeeds."""
        gateway, state_manager, _ = _make_stack(
            responses=[LLMResponse(content="minimal ok", tool_calls=[])],
        )
        response = await gateway.handle_request(
            GatewayRequest(request_id="d8-minimal", messages=[_user_msg("hi")])
        )
        self.assertEqual(response.status, "success")
        self.assertEqual(response.request_id, "d8-minimal")

    async def test_to_dict_on_success_response_has_required_fields(self):
        """GatewayResponse.to_dict() contract includes all fields needed by REST layer."""
        gateway, _, _ = _make_stack(
            responses=[LLMResponse(content="ok", tool_calls=[])],
        )
        response = await gateway.handle_request(
            GatewayRequest(request_id="d8-dict-contract", messages=[_user_msg("hi")])
        )
        d = response.to_dict()
        self.assertIn("request_id", d)
        self.assertIn("status", d)
        self.assertIn("execution_time_ms", d)
        self.assertEqual(d["request_id"], "d8-dict-contract")
        self.assertEqual(d["status"], "success")

    async def test_failed_response_to_dict_includes_error_not_result(self):
        """Failed GatewayResponse.to_dict() includes error, omits result."""
        class Fail(BaseLLMProvider):
            async def generate(self, messages, tools=None, **kwargs):
                raise RuntimeError("deliberate")

        gateway, _, _ = _make_stack(provider=Fail(config=ProviderConfig()))
        response = await gateway.handle_request(
            GatewayRequest(request_id="d8-fail-dict", messages=[_user_msg("hi")])
        )
        d = response.to_dict()
        self.assertIn("error", d)
        self.assertIn("deliberate", d["error"])
        self.assertNotIn("result", d)


# ---------------------------------------------------------------------------
# 7. RESULT PROPAGATION
# ---------------------------------------------------------------------------

class TestResultPropagation(unittest.IsolatedAsyncioTestCase):

    async def test_provider_content_flows_to_gateway_response(self):
        """Provider 'content' field is not lost or overwritten on the way to GatewayResponse."""
        sentinel = "sentinel result content 7890"
        gateway, _, _ = _make_stack(responses=[LLMResponse(content=sentinel, tool_calls=[])])
        response = await gateway.handle_request(
            GatewayRequest(request_id="d8-prop-content", messages=[_user_msg("hi")])
        )
        self.assertEqual(response.result["content"], sentinel)

    async def test_tool_result_flows_intact_to_gateway_response(self):
        """Tool execution result is not lost, not nested incorrectly, matches computation."""
        call_id = "call_99plus1"
        gateway, _, _ = _make_stack(
            responses=[
                LLMResponse(
                    content=None,
                    tool_calls=[ToolCall(id=call_id, name="calculator", arguments={"expression": "99 + 1"})],
                )
            ],
        )
        response = await gateway.handle_request(
            GatewayRequest(request_id="d8-prop-tool", messages=[_user_msg("99+1")])
        )
        self.assertEqual(response.status, "success")
        tr = response.result["tool_results"][0]
        self.assertEqual(tr["tool_call_id"], call_id)
        self.assertEqual(tr["result"]["result"], 100)
        self.assertEqual(tr["tool_name"], "calculator")

    async def test_multiple_tool_results_ordered_correctly(self):
        """Multiple tool calls return results in the correct insertion order."""
        gateway, _, _ = _make_stack(
            responses=[
                LLMResponse(
                    content=None,
                    tool_calls=[
                        ToolCall(id="c-first", name="calculator", arguments={"expression": "1 + 1"}),
                        ToolCall(id="c-second", name="calculator", arguments={"expression": "2 + 2"}),
                    ],
                )
            ],
        )
        response = await gateway.handle_request(
            GatewayRequest(request_id="d8-prop-multi", messages=[_user_msg("compute")])
        )
        self.assertEqual(response.status, "success")
        self.assertEqual(len(response.result["tool_results"]), 2)
        self.assertEqual(response.result["tool_results"][0]["tool_call_id"], "c-first")
        self.assertEqual(response.result["tool_results"][0]["result"]["result"], 2)
        self.assertEqual(response.result["tool_results"][1]["tool_call_id"], "c-second")
        self.assertEqual(response.result["tool_results"][1]["result"]["result"], 4)

    async def test_result_is_associated_with_correct_request_id(self):
        """Results are correctly bound to their originating request_id."""
        gateway, _, _ = _make_stack(
            responses=[
                LLMResponse(content="for-A", tool_calls=[]),
                LLMResponse(content="for-B", tool_calls=[]),
            ],
        )
        resp_a = await gateway.handle_request(
            GatewayRequest(request_id="d8-assoc-A", messages=[_user_msg("A")])
        )
        resp_b = await gateway.handle_request(
            GatewayRequest(request_id="d8-assoc-B", messages=[_user_msg("B")])
        )
        self.assertEqual(resp_a.result["content"], "for-A")
        self.assertEqual(resp_b.result["content"], "for-B")


# ---------------------------------------------------------------------------
# 8. CONTRACT FREEZE VERIFICATION
# ---------------------------------------------------------------------------

class TestContractFreeze(unittest.IsolatedAsyncioTestCase):
    """
    Verify the interfaces exposed to the REST/WebSocket integration are stable.
    No REST/WebSocket implementation is written here.
    """

    def test_gateway_request_required_fields(self):
        fields = {f.name for f in dataclasses.fields(GatewayRequest)}
        self.assertIn("request_id", fields)
        self.assertIn("messages", fields)
        self.assertIn("session_id", fields)
        self.assertIn("parameters", fields)

    def test_gateway_response_required_fields(self):
        fields = {f.name for f in dataclasses.fields(GatewayResponse)}
        self.assertIn("request_id", fields)
        self.assertIn("status", fields)
        self.assertIn("result", fields)
        self.assertIn("error", fields)
        self.assertIn("execution_time_ms", fields)

    def test_execution_state_required_fields(self):
        fields = {f.name for f in dataclasses.fields(ExecutionState)}
        self.assertIn("request_id", fields)
        self.assertIn("status", fields)
        self.assertIn("start_time", fields)
        self.assertIn("end_time", fields)
        self.assertIn("error", fields)

    def test_event_lifecycle_enum_has_all_six_values(self):
        """All six canonical event lifecycle values are present and correctly named."""
        expected = {
            "request_received",
            "execution_started",
            "llm_execution",
            "tool_execution",
            "completed",
            "failed",
        }
        actual = {e.value for e in EventLifecycle}
        self.assertEqual(actual, expected)

    def test_event_schema_fields(self):
        fields = {f.name for f in dataclasses.fields(Event)}
        self.assertIn("event_type", fields)
        self.assertIn("request_id", fields)
        self.assertIn("timestamp", fields)
        self.assertIn("payload", fields)

    def test_state_manager_interface(self):
        sm = StateManager()
        self.assertTrue(callable(getattr(sm, "create_state", None)))
        self.assertTrue(callable(getattr(sm, "update_state", None)))
        self.assertTrue(callable(getattr(sm, "get_state", None)))

    def test_event_stream_interface(self):
        es = EventStream()
        self.assertTrue(callable(getattr(es, "publish", None)))
        self.assertTrue(callable(getattr(es, "subscribe", None)))
        self.assertIsInstance(es.published_events, list)

    def test_gateway_response_to_dict_omits_none_result(self):
        """to_dict() omits 'result' key when result is None (on failure)."""
        resp = GatewayResponse(
            request_id="r1", status="failed", error="oops", execution_time_ms=1.0
        )
        d = resp.to_dict()
        self.assertNotIn("result", d)
        self.assertIn("error", d)

    def test_gateway_response_to_dict_omits_none_error(self):
        """to_dict() omits 'error' key when error is None (on success)."""
        resp = GatewayResponse(
            request_id="r2", status="success", result={"content": "hi"}, execution_time_ms=2.0
        )
        d = resp.to_dict()
        self.assertNotIn("error", d)
        self.assertIn("result", d)

    async def test_orchestrator_accepts_gateway_request_directly(self):
        """Orchestrator.execute_flow() accepts the GatewayRequest object without conversion."""
        registry = ToolRegistry()
        tool_executor = ToolExecutor(registry=registry)
        mock = MockProvider()
        mock.predefined_responses = [LLMResponse(content="direct ok", tool_calls=[])]
        es = EventStream()
        orchestrator = Orchestrator(provider=mock, tool_executor=tool_executor, event_stream=es)
        request = GatewayRequest(
            request_id="d8-orch-direct",
            session_id="sess-x",
            messages=[{"role": "user", "content": "hi"}],
        )
        result = await orchestrator.execute_flow(request)
        self.assertEqual(result["content"], "direct ok")
        self.assertEqual(result["tool_results"], [])


if __name__ == "__main__":
    unittest.main()
