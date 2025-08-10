# AI Agent for Bank Statement Parser Generation

An autonomous AI agent that generates custom parsers for bank statement PDFs using LLM-powered code generation and self-correction loops.

## Agent Architecture

The agent follows a **Plan → Analyze → Generate → Test → Debug** cycle:

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│   PLANNING  │───▶│  ANALYZING   │───▶│ GENERATING   │
│             │    │              │    │              │
│ • Validate  │    │ • Extract    │    │ • LLM Code   │
│   inputs    │    │   PDF text   │    │   Generation │
│ • Setup     │    │ • Analyze    │    │ • Pattern    │
│   paths     │    │   CSV schema │    │   matching   │
└─────────────┘    └──────────────┘    └──────────────┘
                                                │
┌─────────────┐    ┌──────────────┐           ▼
│  DEBUGGING  │◀───│   TESTING    │    ┌──────────────┐
│             │    │              │    │   WRITING    │
│ • Error     │    │ • Import     │    │              │
│   analysis  │    │   parser     │    │ • Save code  │
│ • Context   │    │ • Run tests  │    │   to file    │
│   for retry │    │ • Compare    │    │ • Validate   │
└─────────────┘    │   results    │    │   syntax     │
       ▲           └──────────────┘    └──────────────┘
       │                    │                  │
       └────────────────────┼──────────────────┘
                           ▼
                    ┌──────────────┐
                    │  COMPLETED   │
                    │              │
                    │ • Success    │
                    │ • Parser     │
                    │   ready      │
                    └──────────────┘
```

The agent maintains short-term memory of previous attempts and uses error context to improve subsequent generations. It can self-correct up to 3 times before failing.

## 5-Step Setup & Run Instructions

### Step 1: Setup Environment
```bash
git clone https://github.com/apurv-korefi/ai-agent-challenge
cd ai-agent-challenge
pip install -r requirements.txt
```

### Step 2: Configure API Key
Create a `.env` file in your project root:
```bash
cp .env.template .env
# Edit .env and add:
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

Or set environment variable directly:
```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
```

### Step 3: Prepare Data Structure
Ensure your project has this structure:
```
project/
├── agent.py
├── data/
│   └── icici/
│       ├── icici sample.pdf
│       └── icici sample.csv
└── custom_parsers/  (will be created)
```

### Step 4: Run the Agent
```bash
python agent.py --target icici
```

### Step 5: Test the Generated Parser
```bash
python -m pytest test_agent.py -v
# Or test the specific parser:
python -c "
import sys; sys.path.append('custom_parsers')
import icici_parser
import pandas as pd
result = icici_parser.parse('data/icici/icici sample.pdf')
expected = pd.read_csv('data/icici/icici sample.csv')
print('✅ Parser works!' if result.equals(expected) else '❌ Parser failed')
"
```

## Features

- **🤖 Autonomous Operation**: No manual intervention required
- **🔄 Self-Correction**: Up to 3 attempts with error context learning
- **📊 Schema Matching**: Automatically matches expected CSV output format
- **🧪 Integrated Testing**: Built-in test suite with DataFrame comparison
- **📝 Comprehensive Logging**: Detailed step-by-step execution tracking
- **🏗️ Modular Architecture**: Clean separation of concerns with typed interfaces

## CLI Usage

```bash
# Basic usage
python agent.py --target icici

# With custom retry limit
python agent.py --target sbi --max-attempts 5

# Help
python agent.py --help
```

## Parser Contract

Generated parsers must implement:
```python
def parse(pdf_path: str) -> pd.DataFrame:
    """
    Parse bank statement PDF and return structured data
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        DataFrame with columns matching the expected CSV schema
    """
```

## Architecture Details

- **Agent State Management**: Enum-based state tracking (PLANNING → ANALYZING → GENERATING → TESTING → DEBUGGING → COMPLETED/FAILED)
- **Memory System**: Conversation history and intermediate results storage
- **Error Context Propagation**: Failed attempts inform subsequent generations
- **LLM Integration**: Google Gemini API with structured prompting
- **File I/O Management**: Robust PDF text extraction and CSV analysis
- **Testing Framework**: Automated DataFrame comparison and validation

## Dependencies

- `google-generativeai`: LLM integration
- `pandas`: Data manipulation and comparison  
- `pdfplumber`: PDF text extraction
- `pytest`: Testing framework

## Error Handling

The agent handles various failure scenarios:
- Missing input files
- PDF extraction failures
- LLM generation errors
- Parser compilation errors
- Test execution failures
- DataFrame schema mismatches

Each error provides context for the next generation attempt, enabling self-improvement.
