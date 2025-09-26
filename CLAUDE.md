# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Start the application:**
```bash
./run.sh
```

**Manual startup:**
```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

**Install dependencies:**
```bash
uv sync
```

**Environment setup:**
- Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`
- Server restart required after changing environment variables

## Architecture Overview

This is a **Retrieval-Augmented Generation (RAG) system** for course materials with a tool-based AI architecture.

### Core Query Processing Flow
```
Frontend → FastAPI → RAG System → AI Generator (Claude API)
                                     ↓ (intelligent tool usage)
                                 Search Tools → Vector Store → ChromaDB
```

### Key Architectural Patterns

**Tool-Based AI Integration:**
- Claude API decides whether to search course materials or use general knowledge
- Search functionality exposed as tools to Claude rather than forced retrieval
- Single search per query maximum to avoid over-fetching

**Hierarchical Document Structure:**
- Documents parsed as: Course → Lessons → Chunks
- Each chunk maintains full context (course title, lesson number)
- Sentence-based chunking with configurable overlap (800 chars, 100 overlap)

**Session-Based Conversations:**
- Frontend manages session IDs for conversation continuity
- Backend tracks conversation history (configurable: 2 messages)
- Session created automatically on first query if not provided

### Critical Components Integration

**RAG System (`rag_system.py`)** - Central orchestrator:
- Coordinates document processing, vector storage, AI generation, and sessions
- Handles the complete query pipeline from input to response with sources

**AI Generator (`ai_generator.py`)** - Claude API interface:
- Implements tool-based architecture with sophisticated system prompt
- Temperature: 0, Max tokens: 800 for consistent responses
- Model: `claude-sonnet-4-20250514`

**Document Processor (`document_processor.py`)** - Course document parser:
- Expected format: `Course Title:`, `Course Link:`, `Course Instructor:`, then `Lesson N:` sections
- Smart sentence splitting that handles abbreviations
- Chunk prefixing with lesson context for better search results

**Vector Store (`vector_store.py`)** - ChromaDB integration:
- Uses `all-MiniLM-L6-v2` for embeddings
- Semantic search with course/lesson filtering capabilities
- Stores both metadata and content chunks

**Search Tools (`search_tools.py`)** - Tool definitions for Claude:
- `search_course_content` tool with optional course_name and lesson_number filters
- Tracks sources from searches for response attribution

### Configuration (`config.py`)
- `CHUNK_SIZE: 800` / `CHUNK_OVERLAP: 100` - Document processing
- `MAX_RESULTS: 5` / `MAX_HISTORY: 2` - Search and session limits
- `CHROMA_PATH: "./chroma_db"` - Vector database location

### Application Startup
- Auto-loads documents from `docs/` folder
- Processes `.txt`, `.pdf`, `.docx` files
- Skips already-processed courses to avoid duplicates
- Web UI: http://localhost:8000, API docs: http://localhost:8000/docs

### Development Notes
- No test suite currently implemented
- Uses `uv` for Python package management (Python 3.13+)
- Frontend serves from root `/`, API at `/api/*`
- Invalid API keys cause 500 errors - restart server after fixing `.env`
- always use pip to manger the server do not use pip directly
- don't run the server using ./run.sh I will do it myself