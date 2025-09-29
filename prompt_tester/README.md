# Prompt Tester

Auto-discovery and testing tool for conversational models in LM Studio.

## Features

- **Auto-Discovery**: Finds conversational models from LM Studio API
- **Performance Testing**: Measures tokens/sec, response time, resource usage
- **Quality Scoring**: Uses OpenAI API with healthcare appointment grading criteria
- **Resource Monitoring**: Tracks CPU/GPU usage and temperatures during generation
- **CSV Output**: Complete results with conversation text and grading prompts

## Quick Start

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Set OpenAI API key**:
```bash
set OPENAI_API_KEY=your_key_here
```

3. **Start LM Studio** with conversational models loaded

4. **Run tests**:
```bash
python main.py
```

## Output

Results are saved to `output/prompt_test_results_YYYYMMDD_HHMMSS.csv` with columns:
- Model performance metrics (tokens/sec, timing)
- Resource usage (CPU/GPU utilization, temperatures)
- Quality scores (realness, coherence, naturalness, overall)
- Full conversation text and grading prompts

## Configuration

Edit `config/test_prompts.yaml` to modify test prompts:
- Same-day sick appointments
- Annual checkups  
- Specialist referrals

## Requirements

- LM Studio running on localhost:1234
- OpenAI API key for quality grading
- Python 3.8+