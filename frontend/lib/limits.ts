// Mirrors backend/app/config.py limits (BACKEND_SCHEMA §9). Change both together.
export const MAX_FILE_MB = 25;
export const MAX_FILES_PER_BATCH = 10;
export const MAX_DOCS_PER_WORKSPACE = 30;
export const QUESTION_MIN_CHARS = 3;
export const QUESTION_MAX_CHARS = 500;
export const QUESTION_COUNTER_FROM = 450;
// The sample set is 3 files, so it needs room for 3 (APP_FLOW J2: disabled from 28 documents).
export const SAMPLES_NEED_ROOM = 3;
