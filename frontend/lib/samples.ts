// Suggested questions for the three files in backend/samples/ (Git notes as a PDF, slides, and a Word guide).
// Shown only while every document is a sample (APP_FLOW J2). All three are in backend/eval/qa.json
// (q01, q02, q15). The last needs two documents: only the PDF (or the slides) says a .gitignore applies
// to subfolders, and only the Word guide covers keeping .env out of the repository.
export const SUGGESTED_QUESTIONS = [
  "What is the difference between git revert and git reset --hard?",
  "How do Git-Flow and GitHub Flow branching strategies differ?",
  "Does a .gitignore also apply inside subfolders, and how do I keep secret config files like .env out of the repository?",
] as const;
