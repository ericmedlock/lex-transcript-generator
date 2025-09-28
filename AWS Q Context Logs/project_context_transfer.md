# LLM Transcript Platform - Ultra Context

**System**: `C:\Users\ericm\PycharmProjects\lex-transcript-generator\` | PostgreSQL EPM_DELL:5432/calllab | 1000 convs (10/job) | Hash dedupe → OpenAI grade → CSV

**Core**: orchestrator.py (jobs, health, /5min perf monitor), generation_node.py (LLM worker, activity throttle), dedupe_manager.py (hash-only), health_check.py, dump_performance_data.py (analysis export)

**Config**: config.json (EPM_DELL master, debug_mode, models_filter), per-hostname interactive setup, OpenAI GPT-4o-mini grading (R/C/N/O scores)

**Pipeline**: LM Studio models → generation (178.7 tok/s) → hash dedupe (run 18) → OpenAI grade → conversation_grades table → performance CSV export

**Features**: Auto-discovery, gaming/thermal throttling, graceful shutdown, multi-node, debug single-model testing, Unicode fix (emojis→ASCII)

**Commands**: health_check.py | status.py | Trial: T1 orchestrator T2 "node.py 1" | Prod: T1 orchestrator T2+ node.py | Export: dump_performance_data.py

**Status**: Working system, trial validated (R=8 O=8), syntax errors fixed, performance monitoring /5min, data export ready for analysis LLMs

**Issues Fixed**: Misleading failure logs, semantic dedupe false positives, indentation syntax errors, Unicode encoding, undefined variables, redundant GAN fields