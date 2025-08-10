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
# Create .env file and add:
GOOGLE_API_KEY=your_actual_google_gemini_api_key_here
```

Or set environment variable directly:
```bash
export GOOGLE_API_KEY="your_google_gemini_api_key_here"
```

**Note**: The agent uses Google Gemini 2.5 Flash model via the `google-generativeai` library.

### Step 3: Prepare Data Structure
Ensure your project has this structure:
```
project/
├── agent.py
├── requirements.txt
├── .env
├── data/
│   └── icici/
│       ├── icici sample.pdf
│       └── icici sample.csv
└── custom_parsers/  (will be created automatically)
```

### Step 4: Run the Agent
```bash
python agent.py --target icici
```

### Step 5: Test the Generated Parser
```bash
# Manual test of the generated parser:
python -c "
import sys; sys.path.append('custom_parsers')
import icici_parser
import pandas as pd
result = icici_parser.parse('data/icici/icici sample.pdf')
expected = pd.read_csv('data/icici/icici sample.csv')
print('✅ Parser works!' if result.equals(expected) else '❌ Parser failed')
print(f'Generated {len(result)} rows with columns: {list(result.columns)}')
"
```

## Features

- **🤖 Autonomous Operation**: No manual intervention required
- **🔄 Self-Correction**: Up to 3 attempts with error context learning
- **📊 Schema Matching**: Automatically matches expected CSV output format
- **🧪 Integrated Testing**: Built-in test suite with DataFrame comparison
- **📝 Comprehensive Logging**: Detailed step-by-step execution tracking
- **🏗️ Modular Architecture**: Clean separation of concerns with typed interfaces
- **🔍 PDF Text Extraction**: Uses `pdfplumber` for robust PDF parsing
- **🧠 Memory System**: Tracks execution history and error context

## CLI Usage

```bash
# Basic usage
python agent.py --target icici

# With custom retry limit
python agent.py --target sbi --max-attempts 5

# Help
python agent.py --help
```

## Parser Output Format

Generated parsers must return a DataFrame with these exact columns:
- **Date**: Transaction date as string in DD/MM/YYYY or DD-MM-YYYY format
- **Description**: Clean transaction description
- **Debit Amt**: Positive amounts for debits, 0.0 for credits (float)
- **Credit Amt**: Positive amounts for credits, 0.0 for debits (float)  
- **Balance**: Account balance after transaction (float)

## Parser Contract

Generated parsers must implement:
```python
def parse(pdf_path: str) -> pd.DataFrame:
    """
    Parse bank statement PDF and return structured data
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        DataFrame with columns: Date, Description, Debit Amt, Credit Amt, Balance
    """
```

## Architecture Details

### Agent States
- **PLANNING**: Input validation and path setup
- **ANALYZING**: PDF text extraction and CSV schema analysis  
- **GENERATING**: LLM-powered parser code generation
- **TESTING**: Parser execution and result comparison
- **DEBUGGING**: Error analysis and context preparation for retry
- **COMPLETED**: Successful parser generation
- **FAILED**: Maximum attempts exceeded

### Key Components
- **BankStatementAgent**: Main agent class with state management
- **ParserTask**: Task configuration and tracking
- **PDF Processing**: Text extraction using `pdfplumber`
- **LLM Integration**: Google Gemini 2.5 Flash via `google-generativeai`
- **Testing Framework**: DataFrame comparison and validation
- **Memory System**: Step-by-step execution tracking

## Dependencies

- `google-generativeai>=0.3.0`: Google Gemini API integration
- `pandas>=1.3.0`: Data manipulation and comparison  
- `PyPDF2>=3.0.0`: PDF processing support (fallback)
- `pdfplumber`: Primary PDF text extraction (imported in code)
- `python-dotenv>=0.19.0`: Environment variable management

**Note**: The agent also requires `pdfplumber` which should be added to requirements.txt.

## Error Handling

The agent handles various failure scenarios:
- Missing or invalid API key configuration
- Missing input files (PDF/CSV)
- PDF text extraction failures
- LLM generation errors  
- Parser compilation and import errors
- Test execution failures
- DataFrame schema mismatches

Each error provides detailed context for the next generation attempt, enabling iterative self-improvement.

## Environment Variables

- `GOOGLE_API_KEY`: Required. Your Google Gemini API key
- Can be set via `.env` file or system environment variables

## Output

Successful execution produces:
- Generated parser file in `custom_parsers/{target}_parser.py`
- Detailed execution logs with step-by-step progress
- Success metrics including attempt count and memory usage

## Troubleshooting

1. **API Key Issues**: Ensure `GOOGLE_API_KEY` is correctly set in `.env` or environment
2. **Missing Files**: Verify PDF and CSV files exist in `data/{target}/` directory
3. **Import Errors**: Check that all dependencies are installed via `pip install -r requirements.txt`
4. **PDF Parsing**: Some PDFs may require manual preprocessing for optimal results
