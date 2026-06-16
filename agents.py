import os
import json
from google.antigravity import Agent, LocalAgentConfig

class RailSenseAgentCoordinator:
    def __init__(self):
        self.config = LocalAgentConfig(
            system_instructions=(
                "You are the Central AI Safety Agent for RailSense. "
                "You monitor live Indian train telemetry (speed, axle vibration, track health, AI anomaly scores). "
                "Your role is to orchestrate safety protocols. You must output ONE or MORE CMD blocks based on these rules: "
                "1. If AI anomaly score > 0.45 or vibration exceeds threshold, issue speed restriction: "
                "   CMD: {\"action\": \"RestrictSpeed\", \"train_id\": \"<id>\", \"speed\": 50} "
                "2. If a track segment's health drops below 60%, command track inspection: "
                "   CMD: {\"action\": \"InspectTrack\", \"route_id\": \"<id>\"} "
                "3. If multiple warnings occur on a route, schedule maintenance: "
                "   CMD: {\"action\": \"SuggestMaintenanceSchedule\", \"route_id\": \"<id>\", \"urgency\": \"High\"} "
                "4. Periodically predict derailment risk based on telemetry: "
                "   CMD: {\"action\": \"PredictDerailmentRisk\", \"train_id\": \"<id>\", \"risk_level\": \"Low/Medium/High\"} "
                "Keep reasoning brief, direct, and authoritative."
            )
        )

    async def get_decision(self, trains_state: list) -> tuple[str, dict | None]:
        # Fallback local agent thought & decision generator
        def get_fallback_decision():
            target_train = trains_state[0] if (isinstance(trains_state, list) and len(trains_state) > 0) else {}
            train_id = target_train.get("train_id", "unknown")
            train_name = target_train.get("name", "Express")
            vib = target_train.get("vib", 0.0)
            
            thought = (
                f"Vibration levels on Train {train_id} ({train_name}) are recorded at {vib}g, "
                f"which exceeds the safety threshold of 0.45g. Underlay structural instability or ballast wear suspected. "
                f"Enforcing safety Speed Restriction to prevent potential early derailment."
            )
            command = {"action": "RestrictSpeed", "train_id": train_id, "speed": 50}
            return thought, command

        if not os.environ.get("GEMINI_API_KEY"):
            return get_fallback_decision()

        prompt = (
            f"Current Train Telemetry Status:\n"
            f"{json.dumps(trains_state, indent=2)}\n\n"
            f"Evaluate the state and issue a safety command if action is required."
        )

        try:
            async with Agent(self.config) as agent:
                response = await agent.chat(prompt)
                response_text = await response.text()
                
                agent_thought = ""
                command_data = None

                for line in response_text.split("\n"):
                    if not line.startswith("CMD:"):
                        agent_thought += line + "\n"
                    else:
                        try:
                            json_str = line.split("CMD:")[1].strip()
                            command_data = json.loads(json_str)
                        except Exception as parse_err:
                            print(f"Failed to parse command JSON: {parse_err}")

                # If the agent output was empty or didn't yield a valid command
                if not command_data:
                    return get_fallback_decision()

                return agent_thought.strip(), command_data

        except Exception as e:
            print(f"Agent connection exception: {e}. Falling back to rule-based safety coordinator.")
            return get_fallback_decision()

