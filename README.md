# OneDesk AI

### One Front Door for Everything

OneDesk AI is a multi-tenant enterprise AI support platform that provides a unified interface for organizational assistance. Instead of employees or students navigating different departments to find answers, they can ask questions in one place and receive responses from specialized AI assistants for departments such as IT, HR, Finance, and more.

It combines intelligent query routing, Retrieval-Augmented Generation (RAG), department-specific knowledge, multi-agent response synthesis, and human support escalation into a single system.

---

## Overview

Organizations often store information across multiple departments, documents, policies, and support channels. Finding the right information can be time-consuming, and general-purpose AI assistants may provide inaccurate answers when dealing with internal organizational policies.

OneDesk AI addresses this problem by routing user queries to the appropriate department assistants, retrieving relevant information from organizational knowledge bases, and generating responses grounded in available information. When AI cannot confidently resolve an issue, the conversation can be escalated to a human support agent.

---

## Key Features

- **Multi-Tenant Architecture:** Supports multiple organizations with isolated organizational data.
- **Intelligent Query Routing:** Identifies user intent and routes queries to the appropriate department.
- **Multi-Department Queries:** Splits complex queries into department-specific tasks and combines their responses.
- **RAG-Based Knowledge Retrieval:** Retrieves relevant information from organizational knowledge bases.
- **Department-Specific AI Assistants:** Specialized assistants operate within the scope of their respective departments.
- **Confidence-Based Handling:** Low-confidence or ambiguous queries can trigger clarification or human assistance.
- **Human Support Escalation:** Unresolved conversations are transferred to the relevant support team.
- **Support Ticket Claiming:** Agents can claim conversations, preventing multiple agents from handling the same ticket simultaneously.
- **AI-Assisted Agent Responses:** Human support replies can be refined into clear user-facing responses.
- **Role-Based Access Control:** Separate access and workflows for platform administrators, organization administrators, support agents, and users.
- **Runtime Model Switching:** Supports switching between cloud-based Gemini and local Ollama models.

---

## How It Works

```text
                    User Query
                        |
                        v
              Routing & Planning Agent
                        |
                        v
                Query Classification
                        |
                        v
          Identify Relevant Departments
                        |
          +-------------+-------------+
          |             |             |
          v             v             v
         IT            HR          Finance
          |             |             |
          v             v             v
    Knowledge       Knowledge      Knowledge
    Retrieval       Retrieval      Retrieval
          |             |             |
          v             v             v
    Department     Department     Department
    Assistant     Assistant      Assistant
          |             |             |
          +-------------+-------------+
                        |
                        v
              Response Synthesizer
                        |
                        v
                Confidence Evaluation
                   /           \
                  /             \
             Resolved        Unresolved
                |                |
                v                v
          Final Response    Human Support
                                 |
                                 v
                          Agent Resolution
                                 |
                                 v
                           User Response
```

### Query Processing

1. The user submits a question through the chat interface.
2. The routing and planning component identifies individual tasks and their relevant departments.
3. Queries are classified and checked for ambiguity.
4. Department assistants retrieve relevant knowledge using semantic search.
5. Each department generates a grounded response with confidence information.
6. The response synthesizer combines the department outputs.
7. If the issue cannot be reliably resolved, it is escalated to human support.
8. The assigned support agent responds, and the user receives the resolution.

---

## AI Architecture

### Intelligent Routing

OneDesk AI uses LLM-based routing to identify the topics present in a user's message and determine which departments should handle them.

Complex questions can be divided into smaller department-specific tasks, allowing multiple assistants to work independently.

### Retrieval-Augmented Generation (RAG)

Organizational knowledge is retrieved from a vector database to provide context for department assistants.

The retrieval pipeline uses:

- Dense vector embeddings
- Semantic similarity search
- Department-level filtering
- Organization-level filtering
- Context-grounded answer generation

The system uses MongoDB Atlas Vector Search to retrieve relevant knowledge while enforcing organization and department boundaries.

### Department Assistants

Each department assistant receives:

- Department identity
- Department-specific rules and skills
- Retrieved organizational knowledge
- User query
- Conversation history

Assistants are instructed to prioritize organizational knowledge, avoid fabricating policies, and request human assistance when reliable answers cannot be generated.

### Response Synthesis

When a query involves multiple departments, the synthesizer combines their answers into a unified response. It preserves the information provided by each department and clearly identifies unresolved questions.

---

## Human-in-the-Loop Support

OneDesk AI is designed to recognize when automated assistance is insufficient.

Conversations can be escalated when:

- Organizational information is unavailable.
- AI confidence is below the configured threshold.
- A query requires authoritative human judgment.
- The user needs assistance with an unresolved issue.

### Support Workflow

1. The conversation is marked as awaiting human assistance.
2. It appears in the user's Pending Support section.
3. It enters the relevant department's support queue.
4. A support agent claims the conversation.
5. The agent reviews the chat history and submits a response.
6. The response is refined where applicable.
7. The conversation is marked resolved.
8. The updated response is displayed to the user.

Ticket claiming is implemented to prevent concurrent agents from claiming the same conversation.

---

## User Roles

| Role | Responsibilities |
|---|---|
| `platform_admin` | Platform-level management |
| `org_admin` | Organization and departmental management |
| `support_agent` | Handle department-specific support escalations |
| `user` | Ask questions, interact with AI, and track support requests |

Support agents are associated with specific departments and can access escalations relevant to their assigned department.

---

## Tech Stack

### Backend

- Python
- FastAPI
- Async MongoDB integration
- JWT Authentication
- Pydantic

### Frontend

- React
- Vite
- JavaScript
- Axios

### AI & Machine Learning

- Google Gemini
- Ollama
- Hugging Face Sentence Transformers
- `BAAI/bge-small-en-v1.5`
- Retrieval-Augmented Generation (RAG)

### Database & Retrieval

- MongoDB Atlas
- MongoDB Atlas Vector Search

### Authentication & Security

- JWT-based authentication
- Role-Based Access Control (RBAC)
- Organization-level data isolation
- Department-level access restrictions

---

## Security & Isolation

OneDesk AI follows a multi-tenant design to ensure organizational data is isolated.

- Every organization has its own organizational scope.
- Database retrieval is filtered using `organisation_id`.
- Department knowledge retrieval is filtered using `department_id`.
- Support agents are restricted to their assigned department.
- APIs enforce authentication and role-based authorization.

These restrictions help prevent users and support agents from accessing data belonging to other organizations or departments.

---

## Project Structure

```text
OneDeskAI/
│
├── backend/
│   ├── routers/
│   │   ├── auth.py
│   │   ├── support.py
│   │   └── ...
│   │
│   ├── services/
│   │   ├── gemini.py
│   │   ├── rag.py
│   │   ├── embeddings.py
│   │   └── ...
│   │
│   ├── department_skills.py
│   ├── main.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── dashboards/
│   │   └── ...
│   └── package.json
│
├── prompts/
│   ├── README.md
│   ├── 01_routing_planner.md
│   ├── 02_query_classifier.md
│   ├── 03_department_assistant.md
│   └── 04_response_synthesizer.md
│
└── README.md
```

*Note: The structure above is illustrative; adjust it to match the actual repository.*

---

## Model Support

OneDesk AI supports different inference backends.

| Model Provider | Model | Usage |
|---|---|---|
| Google Gemini | `gemini-3.8-flash` | Cloud-based AI processing |
| Ollama | `qwen3:8b` | Local model inference |

The model provider can be switched at runtime, allowing the application to use cloud inference or a locally running model.

---

## Installation & Setup

### Prerequisites

- Python 3.10+
- Node.js and npm
- MongoDB Atlas account
- Gemini API key (if using Gemini)
- Ollama (optional, for local inference)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd OneDeskAI
```

### 2. Backend Setup

Navigate to the backend directory:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it:

**macOS / Linux**

```bash
source venv/bin/activate
```

**Windows**

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure the environment variables required by the backend.

### 3. Frontend Setup

Open a new terminal:

```bash
cd frontend
npm install
```

Create the frontend environment file and configure the backend API URL as required by the project.

### 4. Run the Backend

From the backend directory:

```bash
uvicorn main:app --reload
```

### 5. Run the Frontend

From the frontend directory:

```bash
npm run dev
```

Open the local URL provided by Vite to access OneDesk AI.

---

## Environment Variables

Configure your environment variables according to the backend configuration.

Example:

```env
MONGO_URI=your_mongodb_connection_string
DATABASE_NAME=onedesk

GEMINI_API_KEY=your_gemini_api_key
JWT_SECRET=your_jwt_secret

# Additional configuration may be required
# depending on the selected model provider.
```

Never commit actual API keys, database credentials, or secrets to version control.

---

## Example Use Cases

### IT Support

> My laptop is not connecting to the university Wi-Fi. What should I do?

Routes to IT and retrieves relevant troubleshooting information.

### Finance

> What is the process for reimbursement of travel expenses?

Retrieves relevant finance policies and provides a knowledge-grounded response.

### Multi-Department Query

> I need a new laptop and want to know if I can claim reimbursement for my home internet.

The query is divided into IT and Finance tasks, answered independently, and synthesized into one response.

### Human Escalation

> I want an exception to the university policy for my situation.

If the available organizational knowledge cannot establish the appropriate answer, the conversation can be escalated to human support.

---

## Current Status

OneDesk AI's core backend, AI pipeline, authentication, retrieval, dashboards, and support escalation workflow have been implemented.

| Component | Status |
||---|
| FastAPI backend | Implemented |
| JWT authentication | Implemented |
| Multi-tenant architecture | Implemented |
| Role-based access control | Implemented |
| Department-based routing | Implemented |
| Multi-department query handling | Implemented |
| Embedding generation | Implemented |
| MongoDB Vector Search | Implemented |
| Department-specific AI responses | Implemented |
| Response synthesis | Implemented |
| Human support escalation | Implemented |
| Atomic ticket claiming | Implemented |
| User dashboard | Implemented |
| Support agent dashboard | Implemented |
| Gemini / Ollama switching | Implemented |
| Final end-to-end verification | Pending |
| Public deployment | Pending |

---

## Limitations

- AI responses depend on the quality and completeness of organizational documents.
- Queries may require human intervention when information is missing or ambiguous.
- LLM-generated responses can still be imperfect and should not replace authoritative decisions.
- Local model performance depends on available hardware.
- The current prototype is not yet publicly deployed.
- Full production readiness requires additional testing, monitoring, and security validation.

---

## Future Improvements

- Production deployment with scalable infrastructure
- Improved retrieval quality and document chunking
- Knowledge base ingestion and management interface
- Analytics for query volume, routing, and resolution rates
- Feedback and response quality evaluation
- Improved agent availability and notification system
- Automated testing and monitoring
- More department integrations and enterprise connectors

---

## Vision

OneDesk AI aims to make organizational support simpler by creating one intelligent entry point for every department.

Instead of searching through documents, navigating departments, or figuring out where to ask a question, users can simply ask.

**One question. One front door. Every department.**

---

## License

Add your preferred license here.