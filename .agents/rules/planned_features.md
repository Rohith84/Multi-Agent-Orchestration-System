# Planned Feature: Code Export & Prompt-Grouped Workspace Studio

When returning to work on this repository, remember to implement the following user-requested improvements:

## 1. Direct Project Export (.zip Download)
- Add a **"📥 Download .zip"** button on completed **Build Mode** chat messages and Workflow detail pages (`/app/workflows/[id]`).
- Create a backend endpoint `GET /api/workspace/download/{session_id}` that zips only the files generated for that specific session/prompt and serves it as a `.zip` file download.

## 2. Prompt-Grouped Session Folders in Workspace Studio
- Update `/app/workspace` to group files by **User Prompt / Session ID & Timestamp** instead of a single flat list:
  ```text
  📁 "Check if string is palindrome" (Aug 19, 10:42 PM)
     ├── palindrome.py
     └── test_palindrome.py
  📁 "FastAPI User Authentication API" (Aug 19, 9:15 PM)
     ├── main.py
     └── auth.py
  ```

## 3. Workflow History Tracker
- Ensure every historical build retains its prompt title, generated file manifest, test reports, and quality scores accessible via `/app/workflows`.
