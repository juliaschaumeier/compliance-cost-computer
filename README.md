## Compliance-Cost Computer (CCC-App)

**The CCC-App is a specialized web application designed to compute the annual compliance costs for legislative processes in Germany.**

### User Group
The application is primarily targeted at **legislators who want to estimate compliance costs during the law drafting process**.

### Application Workflow

| Stage | Description | Key Action |
|-------|-------------|------------|
| **Law Upload** | User uploads a draft or existing law in text form | Provides legal document for analysis |
| **Regulation Identification** | App generates a list of individual regulations affected by the law | Determines potential compliance cost changes |
| **Process Compilation** | Collate individual regulations into comprehensive process lists | Creates foundational analysis framework |
| **Case Group Development** | Create case groups for each process and estimate case numbers | Provides quantitative basis for cost calculation |
| **Process Step Analysis** | Describe individual process steps for each case group | Breaks down operational complexity |
| **Effort Calculation** | Calculate and display effort for each process step | Generates granular cost insights |
| **Total Cost Computation** | Aggregate case numbers and process efforts | Produces final compliance cost estimate |

### Application Interaction

#### User Interface Features
- Workflow displayed on an interactive board with tiles connected by arrows
- Step-by-step progression guided by active buttons
- Ability to add or remove tiles using "+" and "-" buttons
- Progressive tile evolution as computation advances

#### Usage Steps
1. Upload law text (current or planned)
2. Proceed systematically through computational stages
3. Activate buttons sequentially to progress
4. Modify tiles as needed during the process

### Backend

- **Intelligent Processing**: Utilizes Large Language Models (LLM) or Machine Comprehension Platforms (MCP)
- **Data Management**: 
  - Stores law text, computational questions, answers, and resources in a database
  - Tracks user modifications
- **Resource Verification**: Double-checks accuracy of referenced resources
- **Statistical Integration**: Queries DESTATIS database for historical compliance cost data

#### FastAPI service (new)
- Backend entry point: `backend/main.py`
- Core services: `backend/core/llm_service.py`, `backend/core/config.py`, `backend/core/db.py`
- Routers: `backend/routers/tiles.py`, `backend/routers/models.py`
- Run locally:
  - `uvicorn backend.main:app --reload --port 5000`
- API keys:
  - Frontend sends `x-openai-key`, `x-deepinfra-key`, `x-gemini-key`
  - Backend falls back to `OPENAI_API_KEY`, `DEEPINFRA_API_KEY`, `GEMINI_API_KEY` if headers are missing
- Seed demo graph:
  - `POST /tiles/seed` loads `backend/legacy/mockup_data.json` into the tiles DB
  - Example:
    ```bash
    curl -X POST http://localhost:5000/tiles/seed
    ```

### Future Development Roadmap
- Implement one-time compliance cost calculation for law implementation
- Enable recalculation of steps when earlier tiles are modified
- Add functionality to edit numbers in dropdown tiles
- Develop feedback mechanism to inform user of resource accuracy
- Explicit display of LLM confidence levels
- Explainable AI components showing reasoning steps
- Create multiple draft scenarios with different modifications or allow side-by-side comparison of different law drafts' compliance costs (e.g. retrieve previously calculated options from DB)

### Alternative Entry Points
For manual usage of the backend, a python-based chatterbox is available that
bundles some of the most common usage patterns.
- Chatterbox script: `backend/scripts/main_chatterbox.py`
- Legacy modules (pre-migration): `backend/legacy/`

### Frontend (Next.js + React Flow)
- Frontend root: `frontend/`
- Run locally:
  - `npm run install:frontend`
  - `npm run dev`
- Or from inside `frontend/`:
  - `npm install`
  - `npm run dev`
- Optional: set `NEXT_PUBLIC_API_BASE_URL` if the backend isn't on `http://localhost:5000`
- UI highlights:
  - Header hosts the model selector and API key inputs.
  - Tab bar controls the workflow stage (graph stays persistent underneath).
  - React Flow canvas renders tiles from the backend `/tiles` API.
