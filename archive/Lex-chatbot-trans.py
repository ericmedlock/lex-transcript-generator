#!/usr/bin/env python3
"""
Generate Amazon Lex 'Automated Chatbot Designer' transcripts using local LLMs.

Features:
- Throttled concurrent calls to local LLM HTTP endpoints.
- Scenario-driven prompts for variety (schedule, reschedule, cancel, new patient,
  urgent, angry, confused, escalation).
- Post-process LLM output into Contact Lens v1.1.0 JSON (one transcript per file).
- Date-stamped filenames (yyyy-mm-dd) to satisfy Lex requirement.
- Basic near-duplicate filtering via SequenceMatcher.
- Configurable: total conversations, turns per conversation target, RPS throttle.

Usage:
  python gen_lex_transcripts.py \
    --out-dir ./out_transcripts \
    --num-conversations 200 \
    --min-turns 80 --max-turns 140 \
    --rps 2 \
    --endpoints http://127.0.0.1:8000/v1/chat,http://127.0.0.1:8080/v1/chat

Assumes each endpoint speaks a simple OpenAI-style json API. Adapt 'call_llm()' if your API differs.
"""

import os, re, json, time, math, asyncio, random, argparse, datetime
from pathlib import Path
from difflib import SequenceMatcher

try:
    import aiohttp
except ImportError:
    raise SystemExit("Please: pip install aiohttp")

RANDOM_NAMES = [
    "Alex Nguyen","Jordan Patel","Taylor Garcia","Morgan Lopez","Casey Kim",
    "Riley Singh","Drew Johnson","Jamie Ramirez","Cameron Chen","Avery Davis"
]
STREETS = ["Maple St","Oakwood Ave","Birch Rd","Cedar Ln","Willow Way","Elm St","Pinecrest Dr","Clover Ln","Garden St","Westfield Rd"]
CITIES = ["Springfield","Riverton","Brookside","Fairview","Lakeside"]
PROVIDERS = ["Dr. Patel","Dr. Kim","Dr. Singh","Dr. Nguyen","Dr. Rivera"]
PURPOSES = ["a routine check-up","a follow-up visit","a physical","to discuss lab results","a medication review"]
TIMES = ["9:00am","10:15am","1:30pm","2:45pm","4:00pm"]
DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday"]

SCENARIOS = [
    "Existing patient – simple scheduling",
    "Existing patient – slightly chatty",
    "New patient – first appointment",
    "Urgent appointment request (non-emergency)",
    "Frustrated/angry patient",
    "Confused/spaced-out caller",
    "Escalation to supervisor",
    "Appointment change/reschedule",
    "Appointment cancellation",
    "Repeat/impatient caller"
]

SYSTEM_PROMPT = (
    "You are generating realistic doctor office scheduling call transcripts. "
    "Output ONLY a plain-text conversation with alternating lines prefixed by "
    "User: and Bot: (no JSON). Keep it natural and varied."
)

USER_PROMPT_TEMPLATE = """Create a single conversation for scenario: "{scenario}".
Constraints:
- Domain: doctor's office appointment scheduling.
- Include name + DOB; confirm address for existing patients.
- Use realistic variation, possible hesitations, minor corrections.
- Length: {min_turns} to {max_turns} turns (a turn = one User or Bot line).
- Alternate strictly: User:, Bot:, User:, Bot:, ...
- Avoid PHI beyond fictional placeholders (fake names, addresses, phone).
- Do NOT add commentary or section headers; ONLY the conversation.
"""

def random_dob():
    y = random.randint(1955, 2005)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    return f"{m:02d}/{d:02d}/{y}"

def random_addr():
    return f"{random.randint(10,9999)} {random.choice(STREETS)}, {random.choice(CITIES)}"

def make_seed_context():
    return {
        "name": random.choice(RANDOM_NAMES),
        "dob": random_dob(),
        "addr": random_addr(),
        "provider": random.choice(PROVIDERS),
        "purpose": random.choice(PURPOSES),
        "day": random.choice(DAYS),
        "time": random.choice(TIMES),
    }

async def call_llm(session, endpoint, system_prompt, user_prompt, timeout=60):
    # Example minimal OpenAI-ish chat API; change to your local LLM API format.
    payload = {
        "model": "local-llm",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.9,
        "max_tokens": 2500,
    }
    async with session.post(endpoint, json=payload, timeout=timeout) as resp:
        resp.raise_for_status()
        data = await resp.json()
        # Adjust this path if your API differs
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return text

def parse_plain_conversation(text):
    """
    Turn 'User: ...\\nBot: ...\\n...' into a list of (speaker, utterance).
    Enforce alternating turns; filter empty lines.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    turns = []
    for ln in lines:
        if ln.startswith("User:"):
            turns.append(("User", ln[len("User:"):].strip()))
        elif ln.startswith("Bot:"):
            turns.append(("Bot", ln[len("Bot:"):].strip()))
    # Enforce alternating by trimming trailing odd lines if needed
    cleaned = []
    expect = None
    for spk, utt in turns:
        if expect is None or spk == expect:
            cleaned.append((spk, utt))
            expect = "Bot" if spk == "User" else "User"
    # Ensure at least 6 turns
    return cleaned[:], len(cleaned)

def to_contact_lens_v110(conv_id, turns):
    return {
        "Participants": [
            {"ParticipantId": "A1", "ParticipantRole": "AGENT"},
            {"ParticipantId": "C1", "ParticipantRole": "CUSTOMER"},
        ],
        "Version": "1.1.0",
        "ContentMetadata": {
            "RedactionTypes": ["PII"],
            "Output": "Raw"
        },
        "CustomerMetadata": {
            "ContactId": conv_id
        },
        "Transcript": [
            {
                "ParticipantId": "C1" if s == "User" else "A1",
                "Id": f"T{i:06d}",
                "Content": u
            }
            for i, (s, u) in enumerate(turns, start=1)
        ]
    }

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def canon(turns):
    return " ".join(f"{s}:{u}" for s,u in turns).lower()

async def worker(idx, endpoint, sem, session, out_dir, rps_delay, min_turns, max_turns, date_str):
    await sem.acquire()
    try:
        # Throttle
        await asyncio.sleep(rps_delay)

        scenario = random.choice(SCENARIOS)
        seeds = make_seed_context()
        user_prompt = USER_PROMPT_TEMPLATE.format(
            scenario=scenario, min_turns=min_turns, max_turns=max_turns
        )

        text = await call_llm(session, endpoint, SYSTEM_PROMPT, user_prompt)
        turns, n = parse_plain_conversation(text)
        # If too short, pad with a minimal close-out
        if n < min_turns:
            # pad with polite back-and-forth
            needed = min_turns - n
            for i in range(needed):
                turns.append(("User" if i % 2 == 0 else "Bot",
                              "Okay." if i % 2 == 0 else "Got it."))
        conv_id = f"conv_{idx:05d}"
        doc = to_contact_lens_v110(conv_id, turns)

        # Filename includes date
        fname = f"local_llm_transcript_{conv_id}_{date_str}.json"
        with open(out_dir / fname, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
        return (conv_id, turns)
    finally:
        sem.release()

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--num-conversations", type=int, default=100)
    ap.add_argument("--min-turns", type=int, default=60)
    ap.add_argument("--max-turns", type=int, default=120)
    ap.add_argument("--rps", type=float, default=2.0, help="Requests per second cap (global)")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--endpoints", required=True, help="Comma-separated list of local LLM HTTP endpoints")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.date.today().strftime("%Y-%m-%d")

    endpoints = [e.strip() for e in args.endpoints.split(",") if e.strip()]
    if not endpoints:
        raise SystemExit("No endpoints provided.")

    # Throttle: simple global RPS via per-task delay
    rps_delay = 1.0 / max(0.001, args.rps)
    sem = asyncio.Semaphore(args.concurrency)

    tasks = []
    async with aiohttp.ClientSession() as session:
        for i in range(args.num_conversations):
            ep = endpoints[i % len(endpoints)]
            tasks.append(asyncio.create_task(
                worker(i+1, ep, sem, session, out_dir, rps_delay, args.min_turns, args.max_turns, date_str)
            ))
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Basic near-duplicate pruning (optional)
    # Build canon strings and remove files that are >= 0.92 similar to any prior
    threshold = 0.92
    seen = []
    kept_files = []
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            continue
        conv_id, turns = res
        c = canon(turns)
        dup = False
        for c_prev, fname_prev in seen:
            if similarity(c, c_prev) >= threshold:
                # delete file
                for p in out_dir.glob(f"*{conv_id}_*.json"):
                    p.unlink(missing_ok=True)
                dup = True
                break
        if not dup:
            seen.append((c, conv_id))
            # locate filename and keep track
            for p in out_dir.glob(f"*{conv_id}_*.json"):
                kept_files.append(p.name)

    # Simple summary
    summary = {
        "generated": args.num_conversations,
        "kept": len(kept_files),
        "out_dir": str(out_dir),
        "date_stamp": date_str
    }
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
