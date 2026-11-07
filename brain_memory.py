import os
import json
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_PATH = os.path.join(BASE_DIR, "memory_vault.json")

def load_vault():
    if not os.path.exists(VAULT_PATH):
        return {"knowledge_base": [], "custom_memories": []}
    try:
        with open(VAULT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[MEMORY] Error loading vault: {e}", flush=True)
        return {"knowledge_base": [], "custom_memories": []}

def save_vault(data):
    try:
        with open(VAULT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[MEMORY] Error saving vault: {e}", flush=True)
        return False

def get_context_for_query(query: str) -> str:
    """
    Autonomous Intent & Bhav Extractor:
    Scans the query against all knowledge base topics and custom memories.
    Returns targeted, relevant facts without dumping raw history.
    """
    vault = load_vault()
    query_lower = query.lower()
    tokens = set(re.findall(r'\b\w+\b', query_lower))

    # Aliases to map shorthand to core concepts
    alias_map = {
        "rea": ["rea", "reverse", "engineer", "decode", "decompile"],
        "tcp": ["tcp", "tally", "quick entry", "tdl"],
        "render": ["render", "cloud", "server", "worker"],
        "iris": ["iris", "telegram", "bot"],
        "fees": ["fees", "fee", "school", "cirs", "skv"],
        "school": ["school", "cirs", "skv", "aarav", "avni"],
        "tally": ["tally", "tallyprime", "1800", "tcp", "tdl"],
        "whatsapp": ["whatsapp", "mirror"]
    }

    expanded_tokens = set(tokens)
    for t in tokens:
        if t in alias_map:
            expanded_tokens.update(alias_map[t])

    matched_facts = []

    # Check curated knowledge base
    for item in vault.get("knowledge_base", []):
        score = 0
        keywords = item.get("keywords", [])
        for kw in keywords:
            if kw in expanded_tokens or kw in query_lower:
                score += 2
        if score > 0:
            matched_facts.append((score, item.get("topic"), item.get("fact")))

    # Check custom memories
    for mem in vault.get("custom_memories", []):
        mem_text = mem.get("fact", "").lower()
        if any(tok in mem_text for tok in expanded_tokens):
            matched_facts.append((1, "Custom Memory", mem.get("fact")))

    # Sort by relevance score descending
    matched_facts.sort(key=lambda x: x[0], reverse=True)

    if not matched_facts:
        return ""

    # Return top 3 most relevant facts
    context_lines = [f"• [{topic}]: {fact}" for _, topic, fact in matched_facts[:3]]
    return "\n".join(context_lines)

def remember_new_fact(fact: str) -> bool:
    vault = load_vault()
    if "custom_memories" not in vault:
        vault["custom_memories"] = []
    vault["custom_memories"].append({"fact": fact.strip()})
    return save_vault(vault)

def get_memory_summary() -> str:
    vault = load_vault()
    lines = ["🧠 *IRIS CLOUD MEMORY SUMMARY:*\n━━━━━━━━━━━━━━━━━━━"]
    for item in vault.get("knowledge_base", []):
        lines.append(f"• *{item.get('topic')}:* {item.get('fact')[:80]}...")
    custom = vault.get("custom_memories", [])
    if custom:
        lines.append("\n📌 *Recent Custom Memories:*")
        for c in custom[-3:]:
            lines.append(f"• {c.get('fact')}")
    lines.append("━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)
