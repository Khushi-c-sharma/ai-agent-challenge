#!/usr/bin/env python3
"""
AI Agent for Bank Statement Parser Generation
Description: An autonomous agent that generates custom parsers for bank statement PDFs
"""

import argparse
import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import re
import pdfplumber
from dataclasses import dataclass
from enum import Enum
import subprocess
import tempfile

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()  # This loads the .env file
except ImportError:
    print("Note: python-dotenv not installed. Make sure to set GOOGLE_API_KEY environment variable manually.")
    print("Install with: pip install python-dotenv")

# LLM Integration (using Google Gemini as suggested)
try:
    import google.generativeai as genai
except ImportError:
    print("Please install google-generativeai: pip install google-generativeai")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AgentState(Enum):
    PLANNING = "planning"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    TESTING = "testing"
    DEBUGGING = "debugging"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ParserTask:
    target_bank: str
    pdf_path: str
    csv_path: str
    output_parser_path: str
    max_attempts: int = 3
    current_attempt: int = 0

class BankStatementAgent:
    """
    Autonomous agent that generates custom parsers for bank statement PDFs
    
    Architecture:
    Plan → Analyze PDF → Generate Code → Test → Debug (loop) → Complete
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the agent with LLM configuration"""
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError(
                "GOOGLE_API_KEY not found. Please:\n"
                "1. Create a .env file with: GOOGLE_API_KEY=your_api_key_here\n"
                "2. Or set the environment variable: export GOOGLE_API_KEY=your_key\n"
                "3. Or pass api_key parameter to BankStatementAgent()"
            )
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.state = AgentState.PLANNING
        self.memory: List[str] = []
        
    def log_step(self, message: str) -> None:
        """Log step and add to memory"""
        logger.info(f"[{self.state.value.upper()}] {message}")
        self.memory.append(f"{self.state.value}: {message}")
    
    def extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text content from PDF using pdfplumber"""
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        except Exception as e:
            logger.error(f"Failed to extract PDF text: {e}")
            return ""
    
    def analyze_csv_schema(self, csv_path: str) -> Dict:
        """Analyze the expected CSV output schema"""
        try:
            df = pd.read_csv(csv_path)
            schema = {
                'columns': list(df.columns),
                'dtypes': {col: str(df[col].dtype) for col in df.columns},
                'sample_data': df.head(3).to_dict('records'),
                'row_count': len(df)
            }
            return schema
        except Exception as e:
            logger.error(f"Failed to analyze CSV: {e}")
            return {}
    
    def generate_parser_code(self, task: ParserTask, pdf_text: str, csv_schema: Dict, error_context: str = "") -> str:
        """Generate parser code using LLM"""
        prompt = f"""
You are a Python expert creating a bank statement PDF parser for {task.target_bank} bank.

PDF SAMPLE TEXT (first 2000 chars):
{pdf_text[:2000]}

EXPECTED CSV SCHEMA:
Columns: {csv_schema.get('columns', [])}
Data types: {csv_schema.get('dtypes', {})}
Sample data: {csv_schema.get('sample_data', [])}

CRITICAL REQUIREMENTS:
1. Function signature: def parse(pdf_path: str) -> pd.DataFrame
2. Return DataFrame with EXACTLY these columns: Date, Description, Debit Amt, Credit Amt, Balance
3. Date column: Parse dates in DD/MM/YYYY or DD-MM-YYYY format and keep as string (do not convert to YYYY-MM-DD)
4. Description: Clean transaction descriptions, remove extra whitespace
5. Debit Amt: Positive amounts for debits, 0.0 for credits, float type
6. Credit Amt: Positive amounts for credits, 0.0 for debits, float type  
7. Balance: Account balance after transaction, float type
8. Handle various PDF layouts - transactions might be in tables or text blocks
9. Use regex patterns to extract transaction data
10. Include proper error handling and return empty DataFrame if parsing fails
11. Ignore header/footer lines such as "Date Description Debit Amt Credit Amt Balance" or page footers.
12. For every line that is not matched by the transaction regex, log or print the line for debugging.

PARSING STRATEGY:
- Look for date patterns (DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY)
- Extract transaction descriptions (usually after date)
- Identify debit/credit indicators (Dr/Cr, +/-, or separate columns)
- Parse amounts (handle commas, currency symbols)
- Extract running balance
- Clean and validate all data

PREVIOUS ERRORS (if any):
{error_context}

Generate ONLY the Python code for the parser, starting with imports.
Use pandas, re, pdfplumber, and datetime modules:
"""

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return ""
    
    def write_parser_file(self, code: str, output_path: str) -> bool:
        """Write generated parser code to file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Clean up code (remove markdown formatting if present)
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0]
            elif "```" in code:
                code = code.split("```")[1].split("```")[0]
            
            with open(output_path, 'w') as f:
                f.write(code.strip())
            
            self.log_step(f"Parser written to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to write parser: {e}")
            return False
    
    def test_parser(self, task: ParserTask) -> Tuple[bool, str]:
        """Test the generated parser against expected CSV"""
        try:
            # Import the generated parser
            sys.path.insert(0, os.path.dirname(task.output_parser_path))
            parser_module_name = os.path.basename(task.output_parser_path).replace('.py', '')
            
            # Remove from cache if exists
            if parser_module_name in sys.modules:
                del sys.modules[parser_module_name]
            
            parser_module = __import__(parser_module_name)
            
            # Run parser
            result_df = parser_module.parse(task.pdf_path)
            expected_df = pd.read_csv(task.csv_path)
            
            # Compare results
            if result_df.equals(expected_df):
                return True, "Parser output matches expected CSV exactly"
            else:
                error_msg = f"""
Parser test failed:
- Expected shape: {expected_df.shape}
- Actual shape: {result_df.shape}
- Expected columns: {list(expected_df.columns)}
- Actual columns: {list(result_df.columns)}
- Sample differences: {self._compare_dataframes(expected_df, result_df)}
                """
                return False, error_msg
                
        except Exception as e:
            return False, f"Parser execution failed: {str(e)}"
    
    def _compare_dataframes(self, expected: pd.DataFrame, actual: pd.DataFrame) -> str:
        """Compare two dataframes and return differences"""
        try:
            if expected.shape != actual.shape:
                return f"Shape mismatch: expected {expected.shape}, got {actual.shape}"
            
            differences = []
            for col in expected.columns:
                if col not in actual.columns:
                    differences.append(f"Missing column: {col}")
                elif not expected[col].equals(actual[col]):
                    differences.append(f"Column '{col}' differs")
            
            return "; ".join(differences[:3])  # Limit to first 3 differences
        except:
            return "Comparison failed"
    
    def plan_task(self, task: ParserTask) -> bool:
        """Plan the parsing task"""
        self.state = AgentState.PLANNING
        self.log_step(f"Planning parser generation for {task.target_bank}")
        
        # Validate inputs
        if not os.path.exists(task.pdf_path):
            logger.error(f"PDF file not found: {task.pdf_path}")
            return False
        
        if not os.path.exists(task.csv_path):
            logger.error(f"CSV file not found: {task.csv_path}")
            return False
        
        self.log_step("Task validation completed")
        return True
    
    def execute_task(self, task: ParserTask) -> bool:
        """Main execution loop with self-correction"""
        
        if not self.plan_task(task):
            self.state = AgentState.FAILED
            return False
        
        # Analyze inputs
        self.state = AgentState.ANALYZING
        self.log_step("Analyzing PDF and CSV structure")
        
        pdf_text = self.extract_pdf_text(task.pdf_path)
        if not pdf_text:
            logger.error("Failed to extract PDF text")
            self.state = AgentState.FAILED
            return False
        
        csv_schema = self.analyze_csv_schema(task.csv_path)
        if not csv_schema:
            logger.error("Failed to analyze CSV schema")
            self.state = AgentState.FAILED
            return False
        
        error_context = ""
        
        # Generation and testing loop
        while task.current_attempt < task.max_attempts:
            task.current_attempt += 1
            self.log_step(f"Attempt {task.current_attempt}/{task.max_attempts}")
            
            # Generate parser code
            self.state = AgentState.GENERATING
            self.log_step("Generating parser code")
            
            parser_code = self.generate_parser_code(task, pdf_text, csv_schema, error_context)
            if not parser_code:
                logger.error("Failed to generate parser code")
                continue
            
            # Write parser to file
            if not self.write_parser_file(parser_code, task.output_parser_path):
                logger.error("Failed to write parser file")
                continue
            
            # Test parser
            self.state = AgentState.TESTING
            self.log_step("Testing generated parser")
            
            success, test_result = self.test_parser(task)
            
            if success:
                self.state = AgentState.COMPLETED
                self.log_step("Parser generation completed successfully!")
                return True
            else:
                self.state = AgentState.DEBUGGING
                self.log_step(f"Test failed, preparing for retry: {test_result}")
                error_context = test_result
        
        self.state = AgentState.FAILED
        self.log_step(f"Failed to generate working parser after {task.max_attempts} attempts")
        return False

def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="AI Agent for Bank Statement Parser Generation")
    parser.add_argument("--target", required=True, help="Target bank name (e.g., icici)")
    parser.add_argument("--max-attempts", type=int, default=3, help="Maximum attempts for self-correction")
    
    args = parser.parse_args()
    
    # Setup paths
    base_dir = Path.cwd()
    data_dir = base_dir / "data" / args.target
    pdf_path = data_dir / f"{args.target} sample.pdf"
    csv_path = data_dir / f"{args.target} sample.csv"
    
    custom_parsers_dir = base_dir / "custom_parsers"
    output_parser_path = custom_parsers_dir / f"{args.target}_parser.py"
    
    # Validate file existence
    if not pdf_path.exists():
        print(f"Error: PDF file not found at {pdf_path}")
        sys.exit(1)
    
    if not csv_path.exists():
        print(f"Error: CSV file not found at {csv_path}")
        sys.exit(1)
    
    # Create task
    task = ParserTask(
        target_bank=args.target,
        pdf_path=str(pdf_path),
        csv_path=str(csv_path),
        output_parser_path=str(output_parser_path),
        max_attempts=args.max_attempts
    )
    
    # Initialize and run agent
    try:
        agent = BankStatementAgent()
        success = agent.execute_task(task)
        
        if success:
            print(f"\n✅ Success! Parser generated at {output_parser_path}")
            print(f"🔄 Agent completed in {task.current_attempt} attempts")
            print(f"🧠 Memory: {len(agent.memory)} steps recorded")
        else:
            print(f"\n❌ Failed to generate parser after {task.max_attempts} attempts")
            print("Check logs for details")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Agent execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":

    main()
