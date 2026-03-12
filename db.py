import json
import logging
import sqlite3

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_file: str):
        self.connection = sqlite3.connect(db_file, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        with self.connection:
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS homework (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    description TEXT NOT NULL,
                    files_json TEXT,
                    deadline TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cur = self.connection.execute("PRAGMA table_info(homework)")
            columns = [col[1] for col in cur.fetchall()]

            if "file_id" in columns and "files_json" not in columns:
                logger.info("🔄 Миграция старых данных...")
                self.connection.execute("ALTER TABLE homework ADD COLUMN files_json TEXT")
                cur2 = self.connection.execute(
                    "SELECT id, file_id, file_type FROM homework WHERE file_id IS NOT NULL"
                )
                for hw_id, file_id, file_type in cur2.fetchall():
                    if file_id:
                        files_list = [
                            {"file_id": file_id, "file_type": file_type or "document"}
                        ]
                        self.connection.execute(
                            "UPDATE homework SET files_json = ? WHERE id = ?",
                            (json.dumps(files_list, ensure_ascii=False), hw_id),
                        )

    def add_homework(self, subject: str, description: str, files_list: list, deadline: str) -> int:
        files_json = json.dumps(files_list, ensure_ascii=False)
        with self.connection:
            cur = self.connection.execute(
                "INSERT INTO homework (subject, description, files_json, deadline) "
                "VALUES (?, ?, ?, ?)",
                (subject, description, files_json, deadline),
            )
            return cur.lastrowid

    def get_all_homework(self):
        cur = self.connection.execute("SELECT * FROM homework ORDER BY deadline ASC")
        return cur.fetchall()

    def get_homework_by_date(self, target_date: str):
        cur = self.connection.execute(
            "SELECT * FROM homework WHERE deadline = ?", (target_date,)
        )
        return cur.fetchall()

    def get_homework_by_id(self, hw_id: int):
        cur = self.connection.execute(
            "SELECT * FROM homework WHERE id = ?", (hw_id,)
        )
        return cur.fetchone()

    def delete_homework(self, hw_id: int) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM homework WHERE id = ?", (hw_id,))

    def update_homework(
        self,
        hw_id: int,
        subject: str | None = None,
        description: str | None = None,
        deadline: str | None = None,
        files_list: list | None = None,
    ) -> bool:
        updates = []
        values: list = []

        if subject is not None:
            updates.append("subject = ?")
            values.append(subject)
        if description is not None:
            updates.append("description = ?")
            values.append(description)
        if deadline is not None:
            updates.append("deadline = ?")
            values.append(deadline)
        if files_list is not None:
            updates.append("files_json = ?")
            values.append(json.dumps(files_list, ensure_ascii=False))

        if not updates:
            return False

        values.append(hw_id)
        with self.connection:
            self.connection.execute(
                f"UPDATE homework SET {', '.join(updates)} WHERE id = ?", values
            )
        return True


db = Database("school_bot.db")