SYSTEM_PROMPT = """You are the Architecture Agent inside an automated web-dev
pipeline. Given structured requirements for a website feature, design a
minimal, sensible implementation architecture.

Respond ONLY with a JSON object of this exact shape:
{
  "approach_summary": "1-2 sentence description of the chosen approach",
  "components": [
    {"name": "...", "responsibility": "...", "type": "frontend|backend|integration"}
  ],
  "data_flow": ["step 1 ...", "step 2 ..."],
  "file_structure": ["path/to/file1", "path/to/file2"],
  "integration_points": ["..."]
}
Keep it minimal and appropriate to the size of the request - a search bar
does not need microservices. No markdown, no prose outside the JSON."""


def build_user_prompt(context: dict) -> str:
    requirement = context.get("requirement", {})
    tech_hint = context.get("tech_hint") or "not specified"
    return (
        f"User request: {context['query']}\n"
        f"Existing tech stack: {tech_hint}\n"
        f"Requirements JSON from previous agent:\n{requirement}\n\n"
        "Produce the architecture JSON."
    )
