# AI Agent Swarm

## 1. Project Overview

**Objective**  
This project aims to develop a multi-agent AI-driven orchestration framework for SailPoint operations, leveraging AutoGen and the SailPoint Python SDK to process structured and unstructured identity governance data. The system will function within a localized Windows environment, integrating Azure OpenAI's ChatGPT models to enhance autonomous decision-making.

**Key Functionalities**  
- Automated user list transformations  
- Context-aware API querying for SailPoint tenant insights  
- Automated retrieval and interpretation of SailPoint API documentation  
- Efficient batch processing of identity governance data  
- Self-optimizing workflow automation through iterative agent collaboration

## 2. Technology Stack

| Component        | Technology          |
|------------------|---------------------|
| Programming Lang | Python 3.10+       |
| AI Framework     | AutoGen            |
| AI Processing    | Azure OpenAI (GPT) |
| File Handling    | Windows FS (os, shutil) |
| Data Storage     | JSON (license-free)|
| API Integration  | SailPoint Python SDK |
| Logging          | Python logging     |
| Dependencies     | pip (virtualenv)   |

## 3. System Architecture & Workflow

**Agent-Based Orchestration**  
1. User initializes execution via a command-line interface.  
2. Analyst Agent identifies input data structures, validates completeness, and flags inconsistencies.  
3. Researcher Agent queries the SailPoint API, executes contextual web searches, and synthesizes relevant API documentation.
4. Architect Agent orchestrates multi-agent decision-making and workflow validation.    
5. Engineer Agent refines, structures, and processes data, ensuring it aligns with SailPoint schema.  
6. QA Agent verifies compliance, detects anomalies, and refines transformations where needed.   


## 4. Initial Setup Instructions

1. Ensure Python 3.10+ is installed.  
2. Create a virtual environment and activate it:  
   ```bash
   python -m venv venv
   source venv/bin/activate
   # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:  
   ```bash
   pip install -r requirements.txt
   ```
4. Configure your credentials in `config/settings.json`.

## 5. Modular Code Structure

```
ai_agent_swarm/
├── agents/
│   ├── __init__.py
│   ├── analyst_agent.py
│   ├── researcher_agent.py
│   ├── engineer_agent.py
│   ├── qa_agent.py
│   └── pm_agent.py
├── data/
│   ├── input/
│   ├── output/
│   └── knowledge_base.json
├── logs/
│   └── execution.log
├── config/
│   └── settings.json
├── main.py
├── requirements.txt
├── README.md

