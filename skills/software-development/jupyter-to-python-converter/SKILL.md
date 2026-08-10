---
name: jupyter-to-python-converter
description: Convert Jupyter notebooks into production-ready Python applications. Use when migrating research/notebooks to maintainable codebases with proper structure and testing.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [notebook, jupyter, python, conversion, deployment]
    related_skills: [python-dev-companion]
---

# Jupyter to Python Converter

Convert Jupyter notebooks into production-ready Python applications that are maintainable, testable, and deployable.

## When to Use

- Converting Jupyter notebooks to production-ready code for VS Code/terminal environments
- Moving from conda environments (ai_env) to clean Python packages without environment complications
- Addressing user frustration with poor-quality PDF converters and markdown-to-PDF tools
- Setting up hardware-accelerated Python applications on systems like RTX 5070 GPU
- Navigating conda vs standard Python environment conflicts
- Implementing user-pinned workflows for notebook-to-python conversion with explicit dependencies

## Conversion Process

### 1. Analysis Phase
- Identify core logic patterns in the notebook
- Extract dependencies (libraries, external calls)
- Separate concerns (data processing, UI, business logic)
- Map notebook outputs to function returns

### 2. Structure Design
```python
# Recommended package structure
src/
├── __init__.py
├── core/              # Main application logic
│   ├── __init__.py
│   ├── processor.py  # Data processing
│   └── models.py     # Data models
├── utils/             # Helper functions
│   ├── __init__.py
│   └── file_manager.py
├── config/            # Configuration
│   └── settings.py
└── tests/             # Test suite
    ├── __init__.py
    ├── test_processor.py
    └── test_integration.py
```

### 3. Code Refactoring
- Replace `print()` statements with logging
- Extract magic numbers into constants/config
- Add proper error handling and validation
- Include comprehensive docstrings
- Set up type hints for better IDE support

### 4. Testing Strategy
```python
# Add pytest fixtures and test patterns
test_project/
├── conftest.py
├── unit/
│   ├── test_processor.py
│   └── test_utils.py
└── integration/
    └── test_notebook_conversion.py
```

## Common Conversion Pitfalls

### 1. Cell Dependencies
- **Problem**: Notebooks execute cells in order
- **Solution**: Explicit function calls and dependencies

### 2. Interactive Elements
- **Problem**: Widgets, display functions, and markdown in notebooks
- **Solution**: Separate UI from core logic, create separate modules

### 3. Hidden State
- **Problem**: Variables persist across cells
- **Solution**: Use proper state management patterns

### 4. Testing Gaps
- **Problem**: Notebooks rarely have tests
- **Solution**: Write unit and integration tests before conversion

### 5. External Dependencies
- **Problem**: Network calls, file I/O, and database connections mixed with logic
- **Solution**: Extract into separate modules with proper abstractions

## Quick Reference Commands

```bash
# There is NO pip package called "jupyter-to-python-converter".
# This skill is a method, not an installable tool. Convert by reading the
# notebook and writing plain .py files (see Conversion Process below).

# Verify the converted file actually runs (DO NOT just assert success):
python -c "import ast; ast.parse(open('main.py').read()); print('syntax OK')"
python -c "import sys; sys.path.insert(0,'.'); import main; print('IMPORT OK')"

# For notebook reading only (optional, not required):
pip install nbformat    # to parse .ipynb JSON if you script the extraction
```

## Example Conversion

**Before (Jupyter cell):**
```python
def process_data():
    df = pd.read_csv('data.csv')
    result = []
    for index, row in df.iterrows():
        if row['value'] > 100:
            result.append(row['name'] * 2)
    print(f"Processed {len(result)} items")
    return result

# Execute with example
data = process_data()
print(data[:5])
```

**After (Python module):**
```python
# src/core/processor.py
import logging
from typing import List
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def process_data(self, file_path: Path) -> List[str]:
        """Process CSV data and return filtered results.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            List of processed result strings
        """
        try:
            df = pd.read_csv(file_path)
            result = []
            
            for _, row in df.iterrows():
                if row['value'] > self.config.threshold:
                    result.append(row['name'] * self.config.multiplier)
            
            self.logger.info(f"Processed {len(result)} items")
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing data: {e}")
            raise
```

## Verification

```python
# Test the converter
def test_jupyter_conversion_notebook_to_python():
    # Test that conversion preserves functionality
    processor = DataProcessor(Config(threshold=100, multiplier=2))
    
    # Mock data
    test_df = pd.DataFrame({
        'value': [50, 150, 200],
        'name': ['A', 'B', 'C']
    })
    
    test_file = Path("test_data.csv")
    test_df.to_csv(test_file, index=False)
    
    result = processor.process_data(test_file)
    assert len(result) == 2
    assert 'B' in result[0]  # 'BB' (value 150 > 100)
    
    test_file.unlink()  # Clean up
    
    logger.info("✓ Jupyter conversion test passed")
```

## Common Issues and Solutions

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Loss of cell order logic | Runtime errors after conversion | Trace execution flow, extract function dependencies |
| Interactive widgets | Import errors (`ipywidgets`) | Separate UI from core logic into `ui/` module |
| Hidden state | Inconsistent results | Use proper state management with classes |
| Lack of tests | No test coverage | Add pytest fixtures and comprehensive tests |
| External calls | Hardcoded paths and credentials | Use config files and environment variables |

## Best Practices for Reseach to Production

1. **Separate Research Code from Production**
```python
# research.py - For exploration
# production/ - For deployment
```

2. **Use Configuration Files**
```yaml
# config/production.yaml
processing:
  threshold: 100
  batch_size: 1000
  timeout: 30
```

3. **Implement Logging**
```python
import logging
logging.basicConfig(level=logging.INFO)
```

4. **Add Error Handling**
```python
try:
    result = processor.process_data(file_path)
except DataProcessingError as e:
    logger.error(f"Failed to process data: {e}")
    raise
```

5. **Create Modular Structure**
- Core logic in `src/core/`
- Utilities in `src/utils/`
- Configuration in `src/config/`
- Tests in `tests/`

This skill ensures that Jupyter notebooks are transformed into robust, maintainable Python applications that can be shared, tested, and deployed in production environments.