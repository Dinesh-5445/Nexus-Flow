import sys
import json
import asyncio

from src.gateway.models import GatewayRequest
from src.gateway.router import GatewayRouter
from src.orchestration.executor import Orchestrator
from src.state.manager import StateManager
from src.events.stream import EventStream
from src.providers.mock_provider import MockProvider, ProviderConfig
from src.tools.executor import ToolExecutor
from src.tools.registry import ToolRegistry
from src.tools.builtin import CalculatorTool, EchoTool
from src.watchdog.detector import Watchdog

async def run_gateway(req_data):
    # 1. Setup Tools & Registry
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(EchoTool())
    tool_executor = ToolExecutor(registry=registry)
    
    # 2. Setup Provider
    provider = MockProvider(config=ProviderConfig(model_name="mock-model"))
    
    # 3. Setup Events, State, Orchestrator
    event_stream = EventStream()
    state_manager = StateManager()
    
    # 4. Setup Watchdog (Subscriber seam)
    watchdog = Watchdog(repeated_call_threshold=5)
    def on_event_payload(payload):
        watchdog.process_event(payload)
    event_stream.subscribe(on_event_payload)
    
    # (No API-specific interceptors or monkey patches here. The API or other consumers
    # will consume events through the agreed boundary when integrated).

    # 5. Initialize Orchestrator and GatewayRouter
    orchestrator = Orchestrator(
        provider=provider,
        tool_executor=tool_executor,
        event_stream=event_stream
    )
    
    gateway = GatewayRouter(
        orchestrator=orchestrator,
        state_manager=state_manager,
        event_stream=event_stream
    )
    
    # 7. Execute Request
    request = GatewayRequest(**req_data)
    response = await gateway.handle_request(request)
    
    # Finally, print the GatewayResponse to stdout
    print(json.dumps({"__type__": "GatewayResponse", **response.__dict__}), flush=True)


if __name__ == "__main__":
    input_data = sys.stdin.read()
    if input_data.strip():
        req_data = json.loads(input_data)
        asyncio.run(run_gateway(req_data))
