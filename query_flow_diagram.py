import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ConnectionPatch
import numpy as np

# Create figure and axis
fig, ax = plt.subplots(1, 1, figsize=(16, 12))
ax.set_xlim(0, 10)
ax.set_ylim(0, 12)
ax.axis('off')

# Define colors
frontend_color = '#4A90E2'  # Blue
backend_color = '#7ED321'   # Green
ai_color = '#F5A623'        # Orange
data_color = '#BD10E0'      # Purple
arrow_color = '#333333'     # Dark gray

# Helper function to create rounded rectangles
def create_box(ax, x, y, width, height, text, color, text_size=10):
    box = FancyBboxPatch((x, y), width, height,
                         boxstyle="round,pad=0.1",
                         facecolor=color,
                         edgecolor='black',
                         linewidth=1.5,
                         alpha=0.8)
    ax.add_patch(box)

    # Add text
    ax.text(x + width/2, y + height/2, text,
            ha='center', va='center',
            fontsize=text_size, fontweight='bold',
            wrap=True, color='white')

# Helper function to create arrows
def create_arrow(ax, start_x, start_y, end_x, end_y, text="", offset=0.1):
    arrow = patches.FancyArrowPatch((start_x, start_y), (end_x, end_y),
                                   arrowstyle='->', mutation_scale=20,
                                   color=arrow_color, linewidth=2)
    ax.add_patch(arrow)

    if text:
        mid_x = (start_x + end_x) / 2
        mid_y = (start_y + end_y) / 2 + offset
        ax.text(mid_x, mid_y, text, ha='center', va='center',
                fontsize=8, bbox=dict(boxstyle="round,pad=0.3",
                                     facecolor='white', alpha=0.8))

# Title
ax.text(5, 11.5, 'RAG System Query Processing Flow',
        ha='center', va='center', fontsize=18, fontweight='bold')

# 1. Frontend Layer
create_box(ax, 0.5, 10, 2, 1, 'Frontend\n(script.js)', frontend_color, 12)

# User interaction
ax.text(1.5, 9.3, '1. User enters query\n2. Disable UI\n3. Show loading',
        ha='center', va='top', fontsize=9,
        bbox=dict(boxstyle="round,pad=0.3", facecolor='lightblue', alpha=0.7))

# 2. FastAPI Endpoint
create_box(ax, 4, 10, 2, 1, 'FastAPI\n/api/query\n(app.py)', backend_color, 11)

# 3. RAG System
create_box(ax, 7.5, 10, 2, 1, 'RAG System\n(rag_system.py)', backend_color, 11)

# 4. Session Manager
create_box(ax, 0.5, 8, 2, 0.8, 'Session Manager\n(session_manager.py)', backend_color, 10)

# 5. AI Generator
create_box(ax, 4, 8, 2, 0.8, 'AI Generator\n(ai_generator.py)', ai_color, 11)

# 6. Tool Manager & Search Tool
create_box(ax, 7.5, 8, 2, 0.8, 'Search Tools\n(search_tools.py)', ai_color, 11)

# 7. Claude API
create_box(ax, 4, 6, 2, 0.8, 'Anthropic\nClaude API', ai_color, 11)

# 8. Vector Store
create_box(ax, 7.5, 6, 2, 0.8, 'Vector Store\n(vector_store.py)', data_color, 11)

# 9. ChromaDB
create_box(ax, 7.5, 4.5, 2, 0.8, 'ChromaDB\n(Vector Database)', data_color, 11)

# 10. Document Chunks
create_box(ax, 7.5, 3, 2, 0.8, 'Course Chunks\n+ Embeddings', data_color, 10)

# Flow arrows with labels
# Frontend to FastAPI
create_arrow(ax, 2.5, 10.5, 4, 10.5, 'POST /api/query\n{"query": "...", "session_id": "..."}')

# FastAPI to RAG System
create_arrow(ax, 6, 10.5, 7.5, 10.5, 'rag_system.query()')

# RAG to Session Manager
create_arrow(ax, 7.8, 10, 2.3, 8.8, 'Get history\nif session exists', -0.3)

# RAG to AI Generator
create_arrow(ax, 8, 10, 5.5, 8.8, 'generate_response()\nwith tools')

# AI Generator to Claude API
create_arrow(ax, 5, 8, 5, 6.8, 'API call with\nsystem prompt\n+ tools')

# Claude decides to use search tool
create_arrow(ax, 6, 6.4, 7.5, 8.2, 'Tool call:\nsearch_course_content()', 0.2)

# Search tool to Vector Store
create_arrow(ax, 8.5, 8, 8.5, 6.8, 'Semantic search\nwith filters')

# Vector Store to ChromaDB
create_arrow(ax, 8.5, 6, 8.5, 5.3, 'Vector similarity\nsearch')

# ChromaDB to Course Chunks
create_arrow(ax, 8.5, 4.5, 8.5, 3.8, 'Retrieve relevant\nchunks')

# Return path - chunks back up
create_arrow(ax, 8.2, 3.4, 8.2, 4.1, '')
create_arrow(ax, 8.2, 4.9, 8.2, 5.6, 'Ranked results\nwith sources')
create_arrow(ax, 8.2, 6.4, 8.2, 7.6, 'Search results\ntext')

# AI generates final response
create_arrow(ax, 7.5, 8.4, 6, 6.6, 'Tool results\nintegrated', -0.2)

# Response back to RAG
create_arrow(ax, 4.5, 6.8, 4.5, 8, '')

# RAG updates session
create_arrow(ax, 7.5, 9.8, 2.3, 8.4, 'Update conversation\nhistory', 0.3)

# Response back through FastAPI
create_arrow(ax, 7.5, 10.2, 6, 10.2, '')
create_arrow(ax, 4, 10.2, 2.5, 10.2, 'JSON Response:\n{"answer": "...", "sources": [...]}')

# Update frontend UI
ax.text(1.5, 9, '4. Remove loading\n5. Display answer\n6. Show sources\n7. Re-enable UI',
        ha='center', va='top', fontsize=9,
        bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgreen', alpha=0.7))

# Add layer labels
ax.text(0.2, 10.5, 'UI Layer', rotation=90, va='center', ha='center',
        fontsize=12, fontweight='bold', color=frontend_color)
ax.text(0.2, 8.5, 'Backend\nServices', rotation=90, va='center', ha='center',
        fontsize=12, fontweight='bold', color=backend_color)
ax.text(0.2, 6.5, 'AI Layer', rotation=90, va='center', ha='center',
        fontsize=12, fontweight='bold', color=ai_color)
ax.text(0.2, 4, 'Data Layer', rotation=90, va='center', ha='center',
        fontsize=12, fontweight='bold', color=data_color)

# Add decision diamond for Claude's tool usage
diamond = patches.RegularPolygon((5, 7.2), 4, radius=0.4,
                                orientation=np.pi/4,
                                facecolor='yellow',
                                edgecolor='black',
                                alpha=0.8)
ax.add_patch(diamond)
ax.text(5, 7.2, 'Need to\nsearch?', ha='center', va='center',
        fontsize=8, fontweight='bold')

# Add "Yes" and "No" paths
ax.text(5.8, 7.4, 'Yes', fontsize=8, fontweight='bold', color='green')
ax.text(4.2, 7, 'No\n(General\nknowledge)', fontsize=8, fontweight='bold', color='red')

# Add timing/performance notes
ax.text(5, 1.5, 'Key Features:\n• Session-based conversation history\n• Smart tool usage (Claude decides when to search)\n• Vector similarity search with course/lesson filtering\n• Source attribution and transparency\n• Real-time UI updates with loading states',
        ha='center', va='center', fontsize=10,
        bbox=dict(boxstyle="round,pad=0.5", facecolor='lightyellow', alpha=0.9))

plt.tight_layout()
plt.savefig('/Users/rajpython/dev/ai-learning/claude-code-learning/starting-ragchatbot-codebase/query_flow_diagram.png',
           dpi=300, bbox_inches='tight', facecolor='white')
plt.show()