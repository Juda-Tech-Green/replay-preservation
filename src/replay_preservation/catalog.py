"""Traceable catalog; does not invent disc or software records."""
from contextlib import closing
import sqlite3

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS discs (
 disc_id TEXT PRIMARY KEY, label TEXT, source_description TEXT NOT NULL,
 filesystem TEXT, acquisition_date TEXT, image_hash TEXT,
 acquisition_status TEXT NOT NULL DEFAULT 'pending',
 image_path TEXT, mapfile_path TEXT, acquisition_log TEXT
);
CREATE TABLE IF NOT EXISTS files (
 file_id INTEGER PRIMARY KEY, disc_id TEXT NOT NULL REFERENCES discs(disc_id),
 original_path TEXT NOT NULL, file_size INTEGER NOT NULL CHECK(file_size>=0),
 sha256 TEXT, detected_format TEXT, recovery_status TEXT NOT NULL,
 damage_information TEXT, mtime_ns INTEGER, mode INTEGER,
 provenance TEXT NOT NULL, UNIQUE(disc_id, original_path)
);
CREATE INDEX IF NOT EXISTS files_sha256 ON files(sha256);
CREATE TABLE IF NOT EXISTS software (
 software_id INTEGER PRIMARY KEY, disc_id TEXT NOT NULL REFERENCES discs(disc_id),
 title TEXT NOT NULL, platform TEXT, probable_year INTEGER, description TEXT,
 executable_path TEXT, license_status TEXT NOT NULL DEFAULT 'unknown',
 license_evidence TEXT, recovery_confidence TEXT, compatibility_status TEXT NOT NULL DEFAULT 'untested'
);
CREATE TABLE IF NOT EXISTS recovery_events (
 event_id INTEGER PRIMARY KEY, disc_id TEXT REFERENCES discs(disc_id),
 timestamp TEXT NOT NULL, operation TEXT NOT NULL, source TEXT, output TEXT,
 result TEXT NOT NULL, supporting_log TEXT, command_json TEXT, tool_version TEXT
);
CREATE TABLE IF NOT EXISTS compatibility_tests (
 test_id INTEGER PRIMARY KEY, software_id INTEGER NOT NULL REFERENCES software(software_id),
 emulator TEXT NOT NULL, environment TEXT NOT NULL, test_date TEXT NOT NULL,
 outcome TEXT NOT NULL, observations TEXT, supporting_log TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reconstructions (
 reconstruction_id INTEGER PRIMARY KEY, disc_id TEXT NOT NULL REFERENCES discs(disc_id),
 output_path TEXT NOT NULL, output_sha256 TEXT, source_files_json TEXT NOT NULL,
 method TEXT NOT NULL, changes TEXT NOT NULL, evidence TEXT NOT NULL,
 verification TEXT NOT NULL, limitations TEXT, confidence TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS file_extents (
 file_id INTEGER NOT NULL REFERENCES files(file_id), image_offset INTEGER NOT NULL,
 length INTEGER NOT NULL CHECK(length>0), evidence TEXT NOT NULL,
 PRIMARY KEY(file_id,image_offset)
);
CREATE TABLE IF NOT EXISTS schema_info (version INTEGER PRIMARY KEY);
INSERT OR IGNORE INTO schema_info VALUES(1);
"""


def initialize(path):
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript(SCHEMA)
