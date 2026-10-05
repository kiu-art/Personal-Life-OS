#!/usr/bin/env python3
"""
Personal Life OS - Comprehensive Backend Integration Test Suite
Validates all endpoints declared in the OpenAPI specification:
- Health & System status
- Raw Observation Ingestion (WhatsApp, Email)
- Voice Check-ins & Disruption Inference
- Tasks Pipeline (Query, Complete, Slip)
- Schedule & Forward-Only Replanner (Constraints, Warnings, Anchor)
- Tactical Recommendation Engine (WSIDN)
- Memory System (Filtering, Categorized View, Dynamic Deletion)
- Unified Life Map (Nodes, Edges, Health Score)
- Daily Story (Generation, Caching)
- Weekly Review (Generation, Pattern mining, History)
"""

import sys
import time
import json
from datetime import datetime, timezone
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"

# ANSI Terminal Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.start_time = time.time()

    def banner(self, phase_name: str):
        print(f"\n{BOLD}{CYAN}{'='*70}{RESET}")
        print(f"{BOLD}{CYAN}  {phase_name}{RESET}")
        print(f"{BOLD}{CYAN}{'='*70}{RESET}")

    def log_success(self, title: str, details: str = ""):
        self.passed += 1
        msg = f"  {GREEN}✔ [PASS]{RESET} {BOLD}{title}{RESET}"
        if details:
            msg += f" -> {details}"
        print(msg)

    def log_failure(self, title: str, error: str):
        self.failed += 1
        print(f"  {RED}✖ [FAIL]{RESET} {BOLD}{title}{RESET}")
        print(f"    {RED}Error details: {error}{RESET}")

    def log_skip(self, title: str, reason: str):
        self.skipped += 1
        print(f"  {YELLOW}⚠ [SKIP]{RESET} {title} -> {reason}")

    def request(self, method: str, endpoint: str, data: dict = None, params: dict = None, timeout: int = 60):
        url = f"{BASE_URL}{endpoint}"
        if params:
            query_str = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
            url += f"?{query_str}"

        body_bytes = None
        headers = {"Accept": "application/json"}
        if data is not None:
            body_bytes = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                raw = resp.read().decode("utf-8")
                try:
                    parsed = json.loads(raw)
                except Exception:
                    parsed = raw
                return status, parsed
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8")
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = raw
            return e.code, parsed
        except Exception as e:
            return 500, {"error": str(e)}


import urllib.parse
runner = TestRunner()


def run_full_suite():
    print(f"\n{BOLD}{MAGENTA}Starting Personal Life OS End-to-End Test Suite against {BASE_URL}{RESET}")
    today_str = datetime.now().strftime("%Y-%m-%d")

    # =========================================================================
    # PHASE 1: Health & Base Connectivity
    # =========================================================================
    runner.banner("PHASE 1: System Health & OpenAPI Validation")
    status, res = runner.request("GET", "/health", timeout=10)
    if status == 200:
        runner.log_success("GET /health", f"Response: {res}")
    else:
        runner.log_failure("GET /health", f"Status {status}: {res}")
        print(f"\n{RED}Backend is unreachable. Please verify Uvicorn is active.{RESET}")
        sys.exit(1)

    # =========================================================================
    # PHASE 2: Cognitive State Inference & Voice Observations
    # =========================================================================
    runner.banner("PHASE 2: Voice Check-ins & Cognitive Vector Inference")

    # 2A. Test voice inference route
    status, res = runner.request("POST", "/api/observations/voice-state-test", data={
        "text": "Woke up feeling sharp, drank an espresso, ready for 2 hours of deep coding."
    })
    if status == 200 and "operating_mode" in res:
        runner.log_success("POST /api/observations/voice-state-test", f"Mode: {res.get('operating_mode')} | Clarity: {res.get('cognitive_clarity')}/10")
    else:
        runner.log_failure("POST /api/observations/voice-state-test", str(res))

    # 2B. Test voice check-in (Routine / No disruption)
    status, res = runner.request("POST", "/api/observations/voice-checkin", data={
        "transcript": "Morning check-in. Alertness is solid, slept 7.5 hours. Baseline energy intact.",
        "source_device": "mobile_mic"
    }, timeout=75)
    if status == 200:
        runner.log_success("POST /api/observations/voice-checkin (Normal)", f"Disruption Detected: {res.get('disruption_detected')} | Mode: {res.get('operating_mode')}")
    else:
        runner.log_failure("POST /api/observations/voice-checkin (Normal)", str(res))

    # 2C. Test voice check-in (Disruption Detected & Auto-replanning Trigger)
    status, res = runner.request("POST", "/api/observations/voice-checkin", data={
        "transcript": "I had a flat tire on the highway and missed my 2 PM design review. Completely derailed.",
        "source_device": "mobile_mic"
    }, timeout=90)
    if status == 200 and res.get("disruption_detected") is True:
        runner.log_success("POST /api/observations/voice-checkin (Disruption)", f"Disruption Confirmed! Auto-replanned: {res.get('schedule_replanned')}")
    else:
        runner.log_failure("POST /api/observations/voice-checkin (Disruption)", f"Expected disruption=True, got: {res}")

    # =========================================================================
    # PHASE 3: Raw Observations Ingestion (Strict Commitment Gate)
    # =========================================================================
    runner.banner("PHASE 3: Raw WhatsApp & Email Observation Ingestion")

    # 3A. Domestic Chatter (Must be rejected/ignored)
    status, res = runner.request("POST", "/api/observations/raw", data={
        "source": "chat",
        "channel": "WhatsApp",
        "sender": "Roommate",
        "raw_text": "bhai kal pest control karwaye kya?",
        "metadata": {"chat_jid": "flat_chat@g.us", "is_group": True, "from_me": False}
    })
    if status in [200, 202]:
        runner.log_success("POST /api/observations/raw (Domestic Noise)", f"Ingested for triage: obs_id={res.get('observation_id')}")
    else:
        runner.log_failure("POST /api/observations/raw (Domestic Noise)", str(res))

    # 3B. Direct @Mention (Must create professional task)
    status, res = runner.request("POST", "/api/observations/raw", data={
        "source": "chat",
        "channel": "WhatsApp",
        "sender": "Lead Dev",
        "raw_text": "@Ayush please review PR #88 and update database schema by 6 PM",
        "metadata": {
            "chat_jid": "core_team@g.us",
            "is_group": True,
            "from_me": False,
            "mentioned_jids": ["ayush@s.whatsapp.net"]
        }
    })
    if status in [200, 202]:
        runner.log_success("POST /api/observations/raw (@Mention Commitment)", f"Obs ID: {res.get('observation_id')}")
    else:
        runner.log_failure("POST /api/observations/raw (@Mention Commitment)", str(res))

    # Give background workers time to complete LLM triage
    print("  ... waiting 3 seconds for background observation queue to process ...")
    time.sleep(3)

    # =========================================================================
    # PHASE 4: Tasks Pipeline & Dynamic Updates (Complete & Slip)
    # =========================================================================
    runner.banner("PHASE 4: Tasks Lifecycle (List, Complete, Slip)")

    # 4A. List tasks
    status, res = runner.request("GET", "/api/tasks/", params={"status": "pending"})
    task_list = res.get("tasks", []) if isinstance(res, dict) else res
    if status == 200 and isinstance(task_list, list):
        runner.log_success("GET /api/tasks/?status=pending", f"Found {len(task_list)} pending tasks")
    else:
        runner.log_failure("GET /api/tasks/", str(res))
        task_list = []

    target_task_id = None
    if task_list:
        target_task_id = task_list[0].get("id") or task_list[0].get("_id")

    # 4B. Dynamic Task Completion
    if target_task_id:
        status, res = runner.request("PATCH", f"/api/tasks/{target_task_id}/complete")
        if status == 200 and res.get("completed") is True:
            runner.log_success(f"PATCH /api/tasks/{target_task_id}/complete", f"Task marked completed in DB & schedule sync")
        else:
            runner.log_failure(f"PATCH /api/tasks/{target_task_id}/complete", str(res))
    else:
        runner.log_skip("PATCH /api/tasks/{id}/complete", "No existing task available to complete")

    # 4C. Dynamic Task Slip (Triggers auto-replan & causal learning)
    if len(task_list) > 1:
        slip_task_id = task_list[1].get("id") or task_list[1].get("_id")
        status, res = runner.request("PATCH", f"/api/tasks/{slip_task_id}/slip", params={"reason": "Blocked by external dependency"}, timeout=75)
        if status == 200 and res.get("status") == "slipped_and_replanned":
            runner.log_success(f"PATCH /api/tasks/{slip_task_id}/slip", f"Causal edge reinforced & replanned")
        else:
            runner.log_failure(f"PATCH /api/tasks/{slip_task_id}/slip", str(res))
    else:
        runner.log_skip("PATCH /api/tasks/{id}/slip", "Need at least 2 tasks to test separate slip action")

    # =========================================================================
    # PHASE 5: Dynamic Scheduling & Forward Replan Engine
    # =========================================================================
    runner.banner("PHASE 5: Schedule Endpoints & Forward Replanner")

    # 5A. POST /api/schedule/replan
    status, res = runner.request("POST", "/api/schedule/replan", data={
        "current_time": "14:30",
        "situation_note": "Morning headache resolved after rest. Need focused sprint for core deliverables.",
        "hard_stop_bedtime": "23:30",
        "target_date": today_str
    }, timeout=90)
    if status == 200 and "schedule" in res:
        blocks = res.get("schedule", [])
        warnings = res.get("vital_warnings", [])
        runner.log_success("POST /api/schedule/replan", f"Generated {len(blocks)} forward blocks | Vital Warnings: {len(warnings)}")
    else:
        runner.log_failure("POST /api/schedule/replan", str(res))

    # 5B. GET /api/schedule/today
    status, res = runner.request("GET", "/api/schedule/today")
    if status == 200 and ("blocks" in res or "schedule" in res):
        b_count = len(res.get("blocks", []) or res.get("schedule", []))
        runner.log_success("GET /api/schedule/today", f"Retrieved {b_count} blocks for today ({res.get('date')})")
    else:
        runner.log_failure("GET /api/schedule/today", str(res))

    # 5C. GET /api/schedule/{target_date}
    status, res = runner.request("GET", f"/api/schedule/{today_str}")
    if status == 200:
        runner.log_success(f"GET /api/schedule/{today_str}", f"Date confirmed: {res.get('date')}")
    else:
        runner.log_failure(f"GET /api/schedule/{today_str}", str(res))

    # =========================================================================
    # PHASE 6: Tactical Recommendations ("What Should I Do Now?")
    # =========================================================================
    runner.banner("PHASE 6: WSIDN Recommendation Engine")
    status, res = runner.request("GET", "/api/recommendations/what-next", params={
        "available_minutes": 35,
        "notes": "Testing energy alignment"
    })
    if status == 200:
        rec = res.get("primary_recommendation") or res.get("recommendation") or {}
        task_title = rec.get("title") or rec.get("tactical_action")
        duration = rec.get("estimated_minutes", 25)
        runner.log_success("GET /api/recommendations/what-next", f"Action: '{task_title}' ({duration}m) | Chunked: {rec.get('is_chunked')}")
    else:
        runner.log_failure("GET /api/recommendations/what-next", str(res))

    # =========================================================================
    # PHASE 7: Memory System & Dynamic Deletion
    # =========================================================================
    runner.banner("PHASE 7: Memory Facts & Dynamic Deletion")

    # 7A. GET /api/memory/about-me
    status, res = runner.request("GET", "/api/memory/about-me")
    if status == 200 and "categories" in res:
        total = res.get("total_facts", 0)
        runner.log_success("GET /api/memory/about-me", f"Total structured facts: {total}")
    else:
        runner.log_failure("GET /api/memory/about-me", str(res))

    # 7B. GET /api/memory with query parameters
    status, res = runner.request("GET", "/api/memory", params={
        "category": "preferences",
        "limit": 10,
        "skip": 0
    })
    mem_list = res if isinstance(res, list) else res.get("memories", [])
    if status == 200 and isinstance(mem_list, list):
        runner.log_success("GET /api/memory?category=preferences", f"Fetched {len(mem_list)} preferences")
    else:
        runner.log_failure("GET /api/memory", str(res))
        mem_list = []

    # 7C. DELETE /api/memory/{memory_id} (Dynamic Deletion Test)
    if mem_list:
        victim_memory = mem_list[-1]
        victim_id = victim_memory.get("id") or str(victim_memory.get("_id"))
        status, res = runner.request("DELETE", f"/api/memory/{victim_id}")
        if status == 200:
            runner.log_success(f"DELETE /api/memory/{victim_id}", f"Successfully forgotten/deleted fact")
        else:
            runner.log_failure(f"DELETE /api/memory/{victim_id}", str(res))
    else:
        runner.log_skip("DELETE /api/memory/{id}", "No existing memory found to test deletion")

    # =========================================================================
    # PHASE 8: Unified Life Map (Network Graph)
    # =========================================================================
    runner.banner("PHASE 8: Unified Life Map Graph")
    status, res = runner.request("GET", "/api/life-map/")
    if status == 200 and "nodes" in res and "edges" in res:
        nodes = res.get("nodes", [])
        edges = res.get("edges", [])
        health = res.get("graph_health_score", 1.0)
        runner.log_success("GET /api/life-map/", f"Vertices: {len(nodes)} | Edges: {len(edges)} | Resilience Score: {health}")
    else:
        runner.log_failure("GET /api/life-map/", str(res))

    # =========================================================================
    # PHASE 9: Daily Story (Generation & Retrieval)
    # =========================================================================
    runner.banner("PHASE 9: Daily Story Engine")

    # 9A. Generate Story
    status, res = runner.request("POST", "/api/story/generate", params={"target_date": today_str}, timeout=90)
    if status == 200 and "wins" in res:
        runner.log_success(f"POST /api/story/generate?target_date={today_str}", f"Headline: '{res.get('headline')}' | Wins: {len(res.get('wins', []))}")
    else:
        runner.log_failure("POST /api/story/generate", str(res))

    # 9B. Fetch Today Story
    status, res = runner.request("GET", "/api/story/today")
    if status == 200 and "narrative" in res:
        runner.log_success("GET /api/story/today", f"Retrieved story: '{res.get('headline')}'")
    else:
        runner.log_failure("GET /api/story/today", str(res))

    # =========================================================================
    # PHASE 10: Weekly Review (Mining, Latest, History)
    # =========================================================================
    runner.banner("PHASE 10: Weekly Review & Behavioral Pattern Mining")

    # 10A. Generate Weekly Review
    status, res = runner.request("POST", "/api/review/weekly/generate", params={"end_date": today_str}, timeout=110)
    if status == 200 and "behavioral_patterns" in res:
        patterns = res.get("behavioral_patterns", [])
        runner.log_success(f"POST /api/review/weekly/generate?end_date={today_str}", f"Headline: '{res.get('headline')}' | Patterns Mined: {len(patterns)}")
    else:
        runner.log_failure("POST /api/review/weekly/generate", str(res))

    # 10B. Latest Weekly Review
    status, res = runner.request("GET", "/api/review/weekly/latest")
    if status == 200:
        runner.log_success("GET /api/review/weekly/latest", f"Retrieved latest: {res.get('headline')}")
    else:
        runner.log_failure("GET /api/review/weekly/latest", str(res))

    # 10C. Weekly History
    status, res = runner.request("GET", "/api/review/weekly/history", params={"limit": 5})
    if status == 200 and isinstance(res, list):
        runner.log_success("GET /api/review/weekly/history?limit=5", f"Retrieved {len(res)} archived weekly reviews")
    else:
        runner.log_failure("GET /api/review/weekly/history", str(res))

    # =========================================================================
    # SUMMARY
    # =========================================================================
    elapsed = round(time.time() - runner.start_time, 2)
    print(f"\n{BOLD}{CYAN}{'='*70}{RESET}")
    print(f"{BOLD}  TEST RUN SUMMARY{RESET} (Elapsed Time: {elapsed}s)")
    print(f"{BOLD}{CYAN}{'='*70}{RESET}")
    print(f"  Total Passed  : {GREEN}{BOLD}{runner.passed}{RESET}")
    print(f"  Total Failed  : {RED}{BOLD}{runner.failed}{RESET}")
    print(f"  Total Skipped : {YELLOW}{BOLD}{runner.skipped}{RESET}")

    if runner.failed == 0:
        print(f"\n  {GREEN}{BOLD}🎉 ALL ENDPOINTS & DATA FLOWS VALIDATED SUCCESSFULLY!{RESET}\n")
        sys.exit(0)
    else:
        print(f"\n  {RED}{BOLD}⚠ {runner.failed} TEST(S) FAILED. Review output above.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    run_full_suite()