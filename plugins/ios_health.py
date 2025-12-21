"""
iOS Health Data Extractor Plugin

Extracts comprehensive health and fitness data from iOS Health databases including:
- Workouts and activity data
- Heart rate and vital signs
- Sleep tracking
- Steps and movement
- Device information
- And more...

Ported from iLEAPP health artifacts.
"""

from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil
from typing import Any

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class iOShealthPlugin(PluginBase):
    """Extract comprehensive health and fitness data from iOS Health databases."""

    def __init__(self, core_api: CoreAPI):
        super().__init__(core_api)
        self.extraction_type = "unknown"
        self.zip_prefix = ""

        # Data storage for each artifact
        self.workouts_data: list[dict[str, Any]] = []
        self.steps_data: list[dict[str, Any]] = []
        self.heart_rate_data: list[dict[str, Any]] = []
        self.sleep_data: list[dict[str, Any]] = []
        self.source_devices_data: list[dict[str, Any]] = []
        self.provenances_data: list[dict[str, Any]] = []
        self.headphone_audio_data: list[dict[str, Any]] = []
        self.resting_heart_rate_data: list[dict[str, Any]] = []
        self.achievements_data: list[dict[str, Any]] = []
        self.height_data: list[dict[str, Any]] = []
        self.weight_data: list[dict[str, Any]] = []
        self.watch_worn_data: list[dict[str, Any]] = []
        self.sleep_period_data: list[dict[str, Any]] = []
        self.wrist_temperature_data: list[dict[str, Any]] = []

        self.errors: list[str] = []
        self.temp_dir: Path | None = None

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="iOShealthPlugin",
            version="1.0.0",
            description="Extract comprehensive health and fitness data from iOS Health databases",
            author="YaFT (ported from iLEAPP - @KevinPagano3, @Johann-PLW, @SQLMcGee, @stark4n6)",
            target_os=["ios"],
        )

    def initialize(self) -> None:
        """Initialize plugin resources."""
        self.core_api.log_info(f"Initializing {self.metadata.name}")

    def execute(self, *args, **kwargs) -> dict[str, Any]:
        """
        Extract health and fitness data from Health databases.

        Returns:
            Dictionary with execution results
        """
        # Check ZIP file is loaded
        if not self.core_api.get_current_zip():
            self.core_api.print_error("No ZIP file loaded")
            return {"success": False, "error": "No ZIP file loaded"}

        # Detect ZIP format
        self.extraction_type, self.zip_prefix = self.core_api.detect_zip_format()
        self.core_api.print_info(f"Detected extraction format: {self.extraction_type}")

        # Find Health databases
        self.core_api.print_info("Searching for Health databases...")
        healthdb_secure_files = self.core_api.find_files_in_zip("healthdb_secure.sqlite")
        healthdb_files = self.core_api.find_files_in_zip("healthdb.sqlite")

        if not healthdb_secure_files and not healthdb_files:
            self.core_api.print_warning("No Health databases found in ZIP archive")
            return {
                "success": True,
                "message": "No Health databases found",
            }

        healthdb_secure_path = healthdb_secure_files[0] if healthdb_secure_files else None
        healthdb_path = healthdb_files[0] if healthdb_files else None

        if healthdb_secure_path:
            self.core_api.print_info(f"Found healthdb_secure.sqlite: {healthdb_secure_path}")
        if healthdb_path:
            self.core_api.print_info(f"Found healthdb.sqlite: {healthdb_path}")

        # Create temporary directory for database extraction
        self.temp_dir = Path(tempfile.mkdtemp(prefix="yaft_health_"))

        try:
            # Extract databases to temp directory for complex queries
            temp_secure_db = None
            temp_healthdb = None

            if healthdb_secure_path:
                temp_secure_db = self.temp_dir / "healthdb_secure.sqlite"
                self.core_api.extract_zip_file(healthdb_secure_path, self.temp_dir)
                # Find the extracted file
                for file in self.temp_dir.rglob("healthdb_secure.sqlite"):
                    temp_secure_db = file
                    break

            if healthdb_path:
                temp_healthdb = self.temp_dir / "healthdb.sqlite"
                self.core_api.extract_zip_file(healthdb_path, self.temp_dir)
                # Find the extracted file
                for file in self.temp_dir.rglob("healthdb.sqlite"):
                    temp_healthdb = file
                    break

            # Extract artifacts
            if temp_secure_db and temp_secure_db.exists():
                self._extract_workouts(str(temp_secure_db), str(temp_healthdb) if temp_healthdb else None)
                self._extract_steps(str(temp_secure_db))
                self._extract_heart_rate(str(temp_secure_db), str(temp_healthdb) if temp_healthdb else None)
                self._extract_sleep_data(str(temp_secure_db))
                self._extract_resting_heart_rate(str(temp_secure_db), str(temp_healthdb) if temp_healthdb else None)
                self._extract_achievements(str(temp_secure_db))
                self._extract_height(str(temp_secure_db))
                self._extract_weight(str(temp_secure_db))
                self._extract_watch_worn_data(str(temp_secure_db))
                self._extract_sleep_period(str(temp_secure_db))
                self._extract_wrist_temperature(str(temp_secure_db), str(temp_healthdb) if temp_healthdb else None)

            if temp_healthdb and temp_healthdb.exists():
                self._extract_source_devices(str(temp_healthdb))
                if temp_secure_db and temp_secure_db.exists():
                    self._extract_provenances(str(temp_secure_db), str(temp_healthdb))
                    self._extract_headphone_audio(str(temp_secure_db), str(temp_healthdb))

        finally:
            # Clean up temporary directory
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Generate report
        report_path = self._generate_report()

        # Export to JSON
        json_path = self._export_to_json()

        # Export to CSV
        csv_paths = self._export_to_csv()

        return {
            "success": True,
            "report_path": str(report_path),
            "json_path": str(json_path),
            "csv_paths": csv_paths,
            "workouts": len(self.workouts_data),
            "steps": len(self.steps_data),
            "heart_rate": len(self.heart_rate_data),
            "sleep": len(self.sleep_data),
            "devices": len(self.source_devices_data),
            "provenances": len(self.provenances_data),
            "headphone_audio": len(self.headphone_audio_data),
            "resting_heart_rate": len(self.resting_heart_rate_data),
            "achievements": len(self.achievements_data),
            "height": len(self.height_data),
            "weight": len(self.weight_data),
            "watch_worn": len(self.watch_worn_data),
            "sleep_periods": len(self.sleep_period_data),
            "wrist_temperature": len(self.wrist_temperature_data),
            "errors": self.errors,
        }

    def _convert_cocoa_timestamp(self, timestamp: float) -> str:
        """
        Convert Cocoa/Core Data timestamp to ISO format string.
        Cocoa timestamps are seconds since 2001-01-01 00:00:00 UTC.
        """
        if timestamp is None:
            return ""
        try:
            # Cocoa reference date: January 1, 2001, 00:00:00 UTC
            reference_date = datetime(2001, 1, 1)
            dt = reference_date + timedelta(seconds=timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OverflowError, OSError):
            return str(timestamp)

    def _format_duration_hms(self, seconds: float) -> str:
        """Format duration in seconds to HH:MM:SS format."""
        if seconds is None:
            return ""
        try:
            total_seconds = int(seconds)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            secs = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        except (ValueError, TypeError):
            return ""

    def _extract_workouts(self, healthdb_secure_path: str, healthdb_path: str | None) -> None:
        """Extract workout data."""
        try:
            import sqlite3

            conn = sqlite3.connect(healthdb_secure_path)

            # Attach healthdb.sqlite if available
            if healthdb_path:
                conn.execute(f"ATTACH DATABASE '{healthdb_path}' AS healthdb")

            cursor = conn.cursor()

            # Simplified query focusing on core workout data
            query = """
            SELECT
                samples.start_date,
                samples.end_date,
                workouts.activity_type,
                workouts.duration,
                workouts.total_distance,
                workouts.total_energy_burned,
                workouts.goal_type,
                workouts.goal
            FROM workouts
            LEFT OUTER JOIN samples ON samples.data_id = workouts.data_id
            ORDER BY samples.start_date
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            # Activity type mapping (simplified)
            activity_types = {
                37: "RUNNING", 52: "WALKING", 13: "CYCLING", 46: "SWIMMING",
                63: "HIGH INTENSITY INTERVAL TRAINING (HIIT)", 57: "YOGA",
                50: "TRADITIONAL STRENGTH TRAINING", 77: "DANCE", 3000: "OTHER"
            }

            goal_types = {
                0: "Open", 1: "Distance in meters", 2: "Time in seconds", 3: "Kilocalories"
            }

            for row in rows:
                start_time = self._convert_cocoa_timestamp(row[0])
                end_time = self._convert_cocoa_timestamp(row[1])
                activity = activity_types.get(row[2], f"Unknown-{row[2]}")
                duration = self._format_duration_hms(row[3])
                distance_km = round(row[4], 2) if row[4] else 0
                distance_miles = round(distance_km * 0.621371, 2) if row[4] else 0
                energy = round(row[5], 2) if row[5] else 0
                goal_type = goal_types.get(row[6], f"Unknown-{row[6]}")
                goal = int(row[7]) if row[7] else 0

                self.workouts_data.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "activity_type": activity,
                    "duration": duration,
                    "distance_km": distance_km,
                    "distance_miles": distance_miles,
                    "energy_kcal": energy,
                    "goal_type": goal_type,
                    "goal": goal,
                })

            conn.close()
            self.core_api.print_success(f"Extracted {len(self.workouts_data)} workout records")

        except Exception as e:
            self.core_api.log_error(f"Error extracting workouts: {e}")
            self.errors.append(f"Workouts extraction error: {str(e)}")

    def _extract_steps(self, healthdb_secure_path: str) -> None:
        """Extract step count data."""
        try:
            import sqlite3

            conn = sqlite3.connect(healthdb_secure_path)
            cursor = conn.cursor()

            query = """
            SELECT
                samples.start_date,
                samples.end_date,
                quantity_samples.quantity,
                (samples.end_date - samples.start_date) AS duration
            FROM samples
            JOIN quantity_samples ON samples.data_id = quantity_samples.data_id
            WHERE samples.data_type = 7
            ORDER BY samples.start_date
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            for row in rows:
                start_time = self._convert_cocoa_timestamp(row[0])
                end_time = self._convert_cocoa_timestamp(row[1])
                steps = int(row[2]) if row[2] else 0
                duration = int(row[3]) if row[3] else 0

                self.steps_data.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "steps": steps,
                    "duration_seconds": duration,
                })

            conn.close()
            self.core_api.print_success(f"Extracted {len(self.steps_data)} step records")

        except Exception as e:
            self.core_api.log_error(f"Error extracting steps: {e}")
            self.errors.append(f"Steps extraction error: {str(e)}")

    def _extract_heart_rate(self, healthdb_secure_path: str, healthdb_path: str | None) -> None:
        """Extract heart rate data."""
        try:
            import sqlite3

            conn = sqlite3.connect(healthdb_secure_path)

            if healthdb_path:
                conn.execute(f"ATTACH DATABASE '{healthdb_path}' AS healthdb")

            cursor = conn.cursor()

            query = """
            SELECT
                samples.start_date,
                samples.end_date,
                quantity_samples.quantity,
                metadata_values.numerical_value
            FROM samples
            LEFT JOIN quantity_samples ON samples.data_id = quantity_samples.data_id
            LEFT JOIN metadata_values ON samples.data_id = metadata_values.object_id
            WHERE samples.data_type = 5
            ORDER BY samples.start_date DESC
            LIMIT 10000
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            # Heart rate context mapping
            context_map = {
                1.0: "Background", 2.0: "Streaming", 3.0: "Sedentary",
                4.0: "Walking", 5.0: "Breathe", 6.0: "Workout",
                8.0: "Background", 9.0: "ECG", 10.0: "Blood Oxygen Saturation"
            }

            for row in rows:
                start_time = self._convert_cocoa_timestamp(row[0])
                end_time = self._convert_cocoa_timestamp(row[1])
                # Convert to BPM (beats per minute)
                heart_rate = int(round(row[2] * 60)) if row[2] else 0
                context = context_map.get(row[3], f"Unknown-{row[3]}") if row[3] else "Unknown"

                self.heart_rate_data.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "heart_rate_bpm": heart_rate,
                    "context": context,
                })

            conn.close()
            self.core_api.print_success(f"Extracted {len(self.heart_rate_data)} heart rate records")

        except Exception as e:
            self.core_api.log_error(f"Error extracting heart rate: {e}")
            self.errors.append(f"Heart rate extraction error: {str(e)}")

    def _extract_sleep_data(self, healthdb_secure_path: str) -> None:
        """Extract sleep tracking data."""
        try:
            import sqlite3

            conn = sqlite3.connect(healthdb_secure_path)
            cursor = conn.cursor()

            query = """
            SELECT
                samples.start_date,
                samples.end_date,
                category_samples.value,
                (samples.end_date - samples.start_date) AS duration
            FROM samples
            LEFT JOIN category_samples ON samples.data_id = category_samples.data_id
            WHERE samples.data_type = 63
                AND category_samples.value IN (2, 3, 4, 5)
            ORDER BY samples.start_date
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            # Sleep state mapping
            sleep_states = {
                2: "AWAKE", 3: "CORE", 4: "DEEP", 5: "REM"
            }

            for row in rows:
                start_time = self._convert_cocoa_timestamp(row[0])
                end_time = self._convert_cocoa_timestamp(row[1])
                sleep_state = sleep_states.get(row[2], f"Unknown-{row[2]}")
                duration = self._format_duration_hms(row[3])

                self.sleep_data.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "sleep_state": sleep_state,
                    "duration": duration,
                })

            conn.close()
            self.core_api.print_success(f"Extracted {len(self.sleep_data)} sleep records")

        except Exception as e:
            self.core_api.log_error(f"Error extracting sleep data: {e}")
            self.errors.append(f"Sleep extraction error: {str(e)}")

    def _extract_source_devices(self, healthdb_path: str) -> None:
        """Extract source device information."""
        try:
            import sqlite3

            conn = sqlite3.connect(healthdb_path)
            cursor = conn.cursor()

            query = """
            SELECT
                creation_date,
                name,
                manufacturer,
                model,
                hardware,
                firmware,
                software,
                localIdentifier
            FROM source_devices
            WHERE name NOT LIKE '__NONE__' AND localIdentifier NOT LIKE '__NONE__'
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            for row in rows:
                creation_date = self._convert_cocoa_timestamp(row[0])

                self.source_devices_data.append({
                    "creation_date": creation_date,
                    "device_name": row[1] or "",
                    "manufacturer": row[2] or "",
                    "model": row[3] or "",
                    "hardware": row[4] or "",
                    "firmware": row[5] or "",
                    "software": row[6] or "",
                    "local_identifier": row[7] or "",
                })

            conn.close()
            self.core_api.print_success(f"Extracted {len(self.source_devices_data)} source devices")

        except Exception as e:
            self.core_api.log_error(f"Error extracting source devices: {e}")
            self.errors.append(f"Source devices extraction error: {str(e)}")

    def _extract_provenances(self, healthdb_secure_path: str, healthdb_path: str) -> None:
        """Extract data provenances (devices and apps collecting health data)."""
        try:
            import sqlite3

            conn = sqlite3.connect(healthdb_secure_path)
            conn.execute(f"ATTACH DATABASE '{healthdb_path}' AS healthdb")
            cursor = conn.cursor()

            query = """
            SELECT
                data_provenances.ROWID,
                data_provenances.origin_product_type,
                data_provenances.origin_build,
                data_provenances.local_product_type,
                data_provenances.local_build,
                data_provenances.source_id,
                healthdb.sources.name,
                data_provenances.source_version,
                data_provenances.device_id,
                CASE
                    WHEN healthdb.source_devices.name = '__NONE__' THEN ''
                    ELSE healthdb.source_devices.name
                END,
                data_provenances.tz_name
            FROM data_provenances
            LEFT OUTER JOIN healthdb.sources ON healthdb.sources.ROWID = data_provenances.source_id
            LEFT OUTER JOIN healthdb.source_devices ON healthdb.source_devices.ROWID = data_provenances.device_id
            ORDER BY data_provenances.ROWID
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            for row in rows:
                self.provenances_data.append({
                    "row_id": row[0],
                    "origin_product_type": row[1] or "",
                    "origin_build": row[2] or "",
                    "local_product_type": row[3] or "",
                    "local_build": row[4] or "",
                    "source_id": row[5] or "",
                    "source_name": row[6] or "",
                    "source_version": row[7] or "",
                    "device_id": row[8] or "",
                    "device_name": row[9] or "",
                    "timezone": row[10] or "",
                })

            conn.close()
            self.core_api.print_success(f"Extracted {len(self.provenances_data)} provenance records")

        except Exception as e:
            self.core_api.log_error(f"Error extracting provenances: {e}")
            self.errors.append(f"Provenances extraction error: {str(e)}")

    def _extract_headphone_audio(self, healthdb_secure_path: str, healthdb_path: str) -> None:
        """Extract headphone audio levels."""
        try:
            import sqlite3

            conn = sqlite3.connect(healthdb_secure_path)
            conn.execute(f"ATTACH DATABASE '{healthdb_path}' AS healthdb")
            cursor = conn.cursor()

            query = """
            SELECT
                samples.start_date,
                samples.end_date,
                quantity_samples.quantity,
                metadata_values.string_value,
                healthdb.source_devices.name,
                healthdb.source_devices.manufacturer,
                healthdb.source_devices.model,
                healthdb.source_devices.localIdentifier
            FROM samples
            LEFT OUTER JOIN quantity_samples ON samples.data_id = quantity_samples.data_id
            LEFT OUTER JOIN metadata_values ON metadata_values.object_id = samples.data_id
            LEFT OUTER JOIN metadata_keys ON metadata_keys.ROWID = metadata_values.key_id
            LEFT OUTER JOIN objects ON samples.data_id = objects.data_id
            LEFT OUTER JOIN data_provenances ON objects.provenance = data_provenances.ROWID
            LEFT OUTER JOIN healthdb.source_devices ON healthdb.source_devices.ROWID = data_provenances.device_id
            WHERE samples.data_type = 173 AND metadata_keys.key != "_HKPrivateMetadataKeyHeadphoneAudioDataIsTransient"
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            for row in rows:
                start_time = self._convert_cocoa_timestamp(row[0])
                end_time = self._convert_cocoa_timestamp(row[1])

                self.headphone_audio_data.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "decibels": round(row[2], 2) if row[2] else 0,
                    "bundle_name": row[3] or "",
                    "device_name": row[4] or "",
                    "manufacturer": row[5] or "",
                    "model": row[6] or "",
                    "local_identifier": row[7] or "",
                })

            conn.close()
            self.core_api.print_success(f"Extracted {len(self.headphone_audio_data)} headphone audio records")

        except Exception as e:
            self.core_api.log_error(f"Error extracting headphone audio levels: {e}")
            self.errors.append(f"Headphone audio extraction error: {str(e)}")

    def _extract_resting_heart_rate(self, healthdb_secure_path: str, healthdb_path: str | None) -> None:
        """Extract resting heart rate data."""
        try:
            import sqlite3

            conn = sqlite3.connect(healthdb_secure_path)

            if healthdb_path:
                conn.execute(f"ATTACH DATABASE '{healthdb_path}' AS healthdb")

            cursor = conn.cursor()

            query = """
            SELECT
                samples.start_date,
                samples.end_date,
                quantity_samples.quantity,
                objects.creation_date,
                healthdb.sources.product_type,
                healthdb.sources.name
            FROM samples
            LEFT JOIN quantity_samples ON samples.data_id = quantity_samples.data_id
            LEFT JOIN objects ON samples.data_id = objects.data_id
            LEFT JOIN data_provenances ON objects.provenance = data_provenances.ROWID
            LEFT JOIN healthdb.sources ON data_provenances.source_id = healthdb.sources.ROWID
            WHERE samples.data_type = 118 AND quantity_samples.quantity NOT NULL
            ORDER BY samples.start_date DESC
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            for row in rows:
                start_time = self._convert_cocoa_timestamp(row[0])
                end_time = self._convert_cocoa_timestamp(row[1])
                added_time = self._convert_cocoa_timestamp(row[3])
                resting_hr = int(row[2]) if row[2] else 0

                self.resting_heart_rate_data.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "resting_heart_rate_bpm": resting_hr,
                    "date_added": added_time,
                    "hardware_id": row[4] or "",
                    "source": row[5] or "",
                })

            conn.close()
            self.core_api.print_success(f"Extracted {len(self.resting_heart_rate_data)} resting heart rate records")

        except Exception as e:
            self.core_api.log_error(f"Error extracting resting heart rate: {e}")
            self.errors.append(f"Resting heart rate extraction error: {str(e)}")

    def _extract_achievements(self, healthdb_secure_path: str) -> None:
        """Extract health achievements."""
        try:
            import sqlite3

            conn = sqlite3.connect(healthdb_secure_path)
            cursor = conn.cursor()

            query = """
            SELECT
                created_date,
                earned_date,
                template_unique_name,
                value_in_canonical_unit,
                value_canonical_unit,
                creator_device
            FROM ACHAchievementsPlugin_earned_instances
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            for row in rows:
                created_date = self._convert_cocoa_timestamp(row[0])

                self.achievements_data.append({
                    "created_date": created_date,
                    "earned_date": row[1] or "",
                    "achievement": row[2] or "",
                    "value": row[3] or 0,
                    "unit": row[4] or "",
                    "creator_device": row[5] or "",
                })

            conn.close()
            self.core_api.print_success(f"Extracted {len(self.achievements_data)} achievement records")

        except Exception as e:
            self.core_api.log_error(f"Error extracting achievements: {e}")
            self.errors.append(f"Achievements extraction error: {str(e)}")

    def _extract_height(self, healthdb_secure_path: str) -> None:
        """Extract user-entered height data."""
        try:
            import sqlite3

            conn = sqlite3.connect(healthdb_secure_path)
            cursor = conn.cursor()

            query = """
            SELECT
                samples.start_date,
                quantity_samples.quantity
            FROM samples
            LEFT OUTER JOIN quantity_samples ON samples.data_id = quantity_samples.data_id
            WHERE samples.data_type = 2
            ORDER BY samples.start_date DESC
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            for row in rows:
                timestamp = self._convert_cocoa_timestamp(row[0])
                height_m = round(row[1], 2) if row[1] else 0
                height_cm = int(height_m * 100) if row[1] else 0
                # Convert to feet and inches
                height_ft = height_m * 3.281
                feet = int(height_ft)
                inches = int((height_ft - feet) * 12)
                height_ft_in = f"{feet}'{inches}\""

                self.height_data.append({
                    "timestamp": timestamp,
                    "height_meters": height_m,
                    "height_cm": height_cm,
                    "height_feet_inches": height_ft_in,
                })

            conn.close()
            self.core_api.print_success(f"Extracted {len(self.height_data)} height records")

        except Exception as e:
            self.core_api.log_error(f"Error extracting height: {e}")
            self.errors.append(f"Height extraction error: {str(e)}")

    def _extract_weight(self, healthdb_secure_path: str) -> None:
        """Extract user-entered weight data."""
        try:
            import sqlite3

            conn = sqlite3.connect(healthdb_secure_path)
            cursor = conn.cursor()

            query = """
            SELECT
                samples.start_date,
                quantity_samples.quantity
            FROM samples
            LEFT OUTER JOIN quantity_samples ON samples.data_id = quantity_samples.data_id
            WHERE samples.data_type = 3
            ORDER BY samples.start_date DESC
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            for row in rows:
                timestamp = self._convert_cocoa_timestamp(row[0])
                weight_kg = round(row[1], 2) if row[1] else 0
                # Convert to pounds
                weight_lbs = round(weight_kg * 2.20462, 2) if row[1] else 0
                # Convert to stones and pounds
                stones = int(weight_kg / 6.35029)
                stone_pounds = int(((weight_kg / 6.35029) - stones) * 14)
                weight_stone = f"{stones} st {stone_pounds} lbs"

                self.weight_data.append({
                    "timestamp": timestamp,
                    "weight_kg": weight_kg,
                    "weight_pounds": weight_lbs,
                    "weight_stone": weight_stone,
                })

            conn.close()
            self.core_api.print_success(f"Extracted {len(self.weight_data)} weight records")

        except Exception as e:
            self.core_api.log_error(f"Error extracting weight: {e}")
            self.errors.append(f"Weight extraction error: {str(e)}")

    def _extract_watch_worn_data(self, healthdb_secure_path: str) -> None:
        """Extract Apple Watch worn data (periods when watch was worn)."""
        try:
            import sqlite3

            conn = sqlite3.connect(healthdb_secure_path)
            cursor = conn.cursor()

            # Complex CTE query to identify watch worn periods
            query = """
            WITH TimeData AS (
                SELECT
                    start_date,
                    end_date,
                    LAG(start_date) OVER (ORDER BY start_date) AS prev_start_time,
                    LAG(end_date) OVER (ORDER BY start_date) AS prev_end_time
                FROM samples
                WHERE data_type = 70
            ),
            PeriodData AS (
                SELECT
                    *,
                    start_date - prev_end_time AS gap_seconds,
                    CASE
                        WHEN start_date - prev_end_time > 3600 THEN 1
                        ELSE 0
                    END AS new_period
                FROM TimeData
            ),
            PeriodGroup AS (
                SELECT
                    *,
                    SUM(new_period) OVER
                        (ORDER BY start_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS period_id
                FROM PeriodData
            ),
            Summary AS (
                SELECT
                    period_id,
                    MIN(start_date) AS watch_worn_start,
                    MAX(end_date) AS last_worn_hour,
                    (MAX(end_date) - MIN(start_date)) / 3600.0 AS hours_worn
                FROM PeriodGroup
                GROUP BY period_id
            )
            SELECT
                s1.watch_worn_start,
                CAST(s1.hours_worn AS INT),
                s1.last_worn_hour,
                CAST((s2.watch_worn_start - s1.last_worn_hour) / 3600 AS INT)
            FROM Summary s1
            LEFT JOIN Summary s2 ON s1.period_id + 1 = s2.period_id
            ORDER BY s1.period_id
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            for row in rows:
                worn_start = self._convert_cocoa_timestamp(row[0])
                last_hour = self._convert_cocoa_timestamp(row[2])

                self.watch_worn_data.append({
                    "worn_start_time": worn_start,
                    "hours_worn": row[1] or 0,
                    "last_worn_hour_time": last_hour,
                    "hours_off_before_next": row[3] or 0,
                })

            conn.close()
            self.core_api.print_success(f"Extracted {len(self.watch_worn_data)} watch worn period records")

        except Exception as e:
            self.core_api.log_error(f"Error extracting watch worn data: {e}")
            self.errors.append(f"Watch worn data extraction error: {str(e)}")

    def _extract_sleep_period(self, healthdb_secure_path: str) -> None:
        """Extract Apple Watch sleep data aggregated by sleep period."""
        try:
            import sqlite3

            conn = sqlite3.connect(healthdb_secure_path)
            cursor = conn.cursor()

            # Complex CTE query for sleep period analysis
            query = """
            WITH lagged_samples AS (
                SELECT
                    samples.start_date,
                    samples.end_date,
                    samples.data_id,
                    (samples.end_date - samples.start_date) / 60 AS duration_minutes,
                    category_samples.value,
                    LAG(samples.data_id) OVER (ORDER BY samples.data_id) AS prev_data_id,
                    CASE
                        WHEN category_samples.value = 2 THEN "AWAKE"
                        WHEN category_samples.value = 3 THEN "CORE"
                        WHEN category_samples.value = 4 THEN "DEEP"
                        WHEN category_samples.value = 5 THEN "REM"
                    END AS sleep_value
                FROM samples
                LEFT OUTER JOIN category_samples ON samples.data_id = category_samples.data_id
                LEFT OUTER JOIN objects ON samples.data_id = objects.data_id
                LEFT OUTER JOIN data_provenances ON objects.provenance = data_provenances.ROWID
                WHERE samples.data_type = 63 AND category_samples.value != 0
                    AND category_samples.value != 1
                    AND data_provenances.origin_product_type LIKE "%Watch%"
            ),
            grouped_samples AS (
                SELECT
                    start_date,
                    end_date,
                    duration_minutes,
                    sleep_value,
                    CASE
                        WHEN data_id - prev_data_id > 1 OR prev_data_id IS NULL THEN 1
                        ELSE 0
                    END AS is_new_group,
                    SUM(CASE
                            WHEN data_id - prev_data_id > 1 OR prev_data_id IS NULL THEN 1
                            ELSE 0
                        END) OVER (ORDER BY data_id) AS group_number
                FROM lagged_samples
            )
            SELECT
                MIN(start_date),
                MAX(end_date),
                SUM(CASE WHEN sleep_value IN ('AWAKE', 'REM', 'CORE', 'DEEP')
                    THEN duration_minutes * 60 ELSE 0 END),
                SUM(CASE WHEN sleep_value IN ('REM', 'CORE', 'DEEP')
                    THEN duration_minutes * 60 ELSE 0 END),
                SUM(CASE WHEN sleep_value = 'AWAKE' THEN duration_minutes * 60 ELSE 0 END),
                SUM(CASE WHEN sleep_value = 'REM' THEN duration_minutes * 60 ELSE 0 END),
                SUM(CASE WHEN sleep_value = 'CORE' THEN duration_minutes * 60 ELSE 0 END),
                SUM(CASE WHEN sleep_value = 'DEEP' THEN duration_minutes * 60 ELSE 0 END),
                ROUND(SUM(CASE WHEN sleep_value = 'AWAKE'
                    THEN duration_minutes ELSE 0 END) * 100.0 / SUM(duration_minutes), 2),
                ROUND(SUM(CASE WHEN sleep_value = 'REM'
                    THEN duration_minutes ELSE 0 END) * 100.0 / SUM(duration_minutes), 2),
                ROUND(SUM(CASE WHEN sleep_value = 'CORE'
                    THEN duration_minutes ELSE 0 END) * 100.0 / SUM(duration_minutes), 2),
                ROUND(SUM(CASE WHEN sleep_value = 'DEEP'
                    THEN duration_minutes ELSE 0 END) * 100.0 / SUM(duration_minutes), 2)
            FROM grouped_samples
            GROUP BY group_number
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            for row in rows:
                sleep_start = self._convert_cocoa_timestamp(row[0])
                sleep_end = self._convert_cocoa_timestamp(row[1])

                self.sleep_period_data.append({
                    "sleep_start_time": sleep_start,
                    "sleep_end_time": sleep_end,
                    "time_in_bed": self._format_duration_hms(row[2]),
                    "time_asleep": self._format_duration_hms(row[3]),
                    "awake_duration": self._format_duration_hms(row[4]),
                    "rem_duration": self._format_duration_hms(row[5]),
                    "core_duration": self._format_duration_hms(row[6]),
                    "deep_duration": self._format_duration_hms(row[7]),
                    "awake_percent": row[8] or 0,
                    "rem_percent": row[9] or 0,
                    "core_percent": row[10] or 0,
                    "deep_percent": row[11] or 0,
                })

            conn.close()
            self.core_api.print_success(f"Extracted {len(self.sleep_period_data)} sleep period records")

        except Exception as e:
            self.core_api.log_error(f"Error extracting sleep period data: {e}")
            self.errors.append(f"Sleep period extraction error: {str(e)}")

    def _extract_wrist_temperature(self, healthdb_secure_path: str, healthdb_path: str | None) -> None:
        """Extract wrist temperature data."""
        try:
            import sqlite3

            conn = sqlite3.connect(healthdb_secure_path)

            if healthdb_path:
                conn.execute(f"ATTACH DATABASE '{healthdb_path}' AS healthdb")

            cursor = conn.cursor()

            query = """
            WITH surface_temp AS (
                SELECT
                    metadata_values.object_id,
                    metadata_values.numerical_value
                FROM metadata_values
                JOIN metadata_keys ON metadata_values.key_id = metadata_keys.ROWID
                WHERE metadata_keys.key = '_HKPrivateMetadataKeySkinSurfaceTemperature'
            ),
            algorithm_version AS (
                SELECT
                    metadata_values.object_id,
                    metadata_values.numerical_value
                FROM metadata_values
                JOIN metadata_keys ON metadata_values.key_id = metadata_keys.ROWID
                WHERE metadata_keys.key = 'HKAlgorithmVersion'
            )
            SELECT
                samples.start_date,
                samples.end_date,
                objects.creation_date,
                quantity_samples.quantity,
                healthdb.sources.name,
                algorithm_version.numerical_value,
                surface_temp.numerical_value,
                healthdb.source_devices.name,
                healthdb.source_devices.manufacturer,
                healthdb.source_devices.model,
                healthdb.source_devices.hardware,
                healthdb.source_devices.software
            FROM samples
            LEFT OUTER JOIN quantity_samples ON quantity_samples.data_id = samples.data_id
            LEFT OUTER JOIN objects ON samples.data_id = objects.data_id
            LEFT OUTER JOIN data_provenances ON objects.provenance = data_provenances.ROWID
            LEFT OUTER JOIN surface_temp ON surface_temp.object_id = samples.data_id
            LEFT OUTER JOIN algorithm_version ON algorithm_version.object_id = samples.data_id
            LEFT OUTER JOIN healthdb.sources ON healthdb.sources.ROWID = data_provenances.source_id
            LEFT OUTER JOIN healthdb.source_devices ON healthdb.source_devices.ROWID = data_provenances.device_id
            WHERE samples.data_type = 256
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            for row in rows:
                start_time = self._convert_cocoa_timestamp(row[0])
                end_time = self._convert_cocoa_timestamp(row[1])
                added_time = self._convert_cocoa_timestamp(row[2])
                temp_c = round(row[3], 2) if row[3] else 0
                temp_f = round((temp_c * 1.8) + 32, 2) if row[3] else 0
                surface_c = round(row[6], 2) if row[6] else 0
                surface_f = round((surface_c * 1.8) + 32, 2) if row[6] else 0

                self.wrist_temperature_data.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "date_added": added_time,
                    "wrist_temp_celsius": temp_c,
                    "wrist_temp_fahrenheit": temp_f,
                    "source": row[4] or "",
                    "algorithm_version": row[5] or 0,
                    "surface_temp_celsius": surface_c,
                    "surface_temp_fahrenheit": surface_f,
                    "device_name": row[7] or "",
                    "manufacturer": row[8] or "",
                    "model": row[9] or "",
                    "hardware": row[10] or "",
                    "software": row[11] or "",
                })

            conn.close()
            self.core_api.print_success(f"Extracted {len(self.wrist_temperature_data)} wrist temperature records")

        except Exception as e:
            self.core_api.log_error(f"Error extracting wrist temperature: {e}")
            self.errors.append(f"Wrist temperature extraction error: {str(e)}")

    def _generate_report(self) -> Path:
        """Generate markdown report."""
        sections = []

        # Summary
        total_records = (
            len(self.workouts_data) +
            len(self.steps_data) +
            len(self.heart_rate_data) +
            len(self.sleep_data) +
            len(self.source_devices_data) +
            len(self.provenances_data) +
            len(self.headphone_audio_data) +
            len(self.resting_heart_rate_data) +
            len(self.achievements_data) +
            len(self.height_data) +
            len(self.weight_data) +
            len(self.watch_worn_data) +
            len(self.sleep_period_data) +
            len(self.wrist_temperature_data)
        )

        summary_content = f"""
Extracted comprehensive health and fitness data from iOS Health databases.

**Total Records:** {total_records:,}

The Health app stores rich health and fitness information including workout activities,
step counts, heart rate measurements, sleep tracking, device information, provenances,
headphone audio levels, achievements, user-entered height/weight, watch worn data,
sleep analysis, and wrist temperature. This data provides valuable insights into user
health patterns, device usage, and activity patterns.

**Note:** Full data exported to CSV and JSON files for detailed analysis.
"""

        sections.append({
            "heading": "Summary",
            "content": summary_content.strip(),
            "style": "text",
        })

        # Statistics table
        stats = {
            "Workout Records": f"{len(self.workouts_data):,}",
            "Step Records": f"{len(self.steps_data):,}",
            "Heart Rate Records": f"{len(self.heart_rate_data):,}",
            "Resting Heart Rate Records": f"{len(self.resting_heart_rate_data):,}",
            "Sleep Records": f"{len(self.sleep_data):,}",
            "Sleep Period Records": f"{len(self.sleep_period_data):,}",
            "Source Devices": f"{len(self.source_devices_data):,}",
            "Provenance Records": f"{len(self.provenances_data):,}",
            "Headphone Audio Records": f"{len(self.headphone_audio_data):,}",
            "Achievement Records": f"{len(self.achievements_data):,}",
            "Height Records": f"{len(self.height_data):,}",
            "Weight Records": f"{len(self.weight_data):,}",
            "Watch Worn Records": f"{len(self.watch_worn_data):,}",
            "Wrist Temperature Records": f"{len(self.wrist_temperature_data):,}",
        }

        sections.append({
            "heading": "Data Statistics",
            "content": stats,
            "style": "table",
        })

        # Add sample data for each artifact (first 10 records for large datasets)
        if self.workouts_data:
            self._add_section_with_sample(sections, "Workouts (Sample)", self.workouts_data[:10])

        if self.steps_data:
            self._add_section_with_sample(sections, "Steps (Sample)", self.steps_data[:10])

        if self.heart_rate_data:
            self._add_section_with_sample(sections, "Heart Rate (Sample)", self.heart_rate_data[:10])

        if self.resting_heart_rate_data:
            self._add_section_with_sample(sections, "Resting Heart Rate (Sample)", self.resting_heart_rate_data[:10])

        if self.sleep_data:
            self._add_section_with_sample(sections, "Sleep Data (Sample)", self.sleep_data[:10])

        if self.sleep_period_data:
            self._add_section_with_sample(sections, "Sleep Periods (Sample)", self.sleep_period_data[:10])

        if self.watch_worn_data:
            self._add_section_with_sample(sections, "Watch Worn Periods (Sample)", self.watch_worn_data[:10])

        if self.achievements_data:
            self._add_section_with_sample(sections, "Achievements (Sample)", self.achievements_data[:10])

        if self.height_data:
            self._add_section_with_sample(sections, "Height Records (Sample)", self.height_data[:5])

        if self.weight_data:
            self._add_section_with_sample(sections, "Weight Records (Sample)", self.weight_data[:5])

        if self.headphone_audio_data:
            self._add_section_with_sample(sections, "Headphone Audio Levels (Sample)", self.headphone_audio_data[:10])

        if self.wrist_temperature_data:
            self._add_section_with_sample(sections, "Wrist Temperature (Sample)", self.wrist_temperature_data[:10])

        if self.provenances_data:
            self._add_section_with_sample(sections, "Provenances (Sample)", self.provenances_data[:10])

        if self.source_devices_data:
            self._add_section_with_sample(sections, "Source Devices", self.source_devices_data)

        # Errors
        if self.errors:
            sections.append({
                "heading": "Errors",
                "content": self.errors,
                "style": "list",
            })

        metadata = {
            "Extraction Type": self.extraction_type,
            "Total Records": f"{total_records:,}",
        }

        report_path = self.core_api.generate_report(
            plugin_name=self.metadata.name,
            title="iOS Health Database Analysis",
            sections=sections,
            metadata=metadata,
        )

        self.core_api.print_success(f"Report generated: {report_path}")
        return report_path

    def _add_section_with_sample(self, sections: list, heading: str, data: list[dict]) -> None:
        """Add a section with sample data table."""
        if not data:
            return

        # Convert list of dicts to table format
        table = {}
        for key in data[0].keys():
            # Convert key to title case for display
            display_key = key.replace("_", " ").title()
            table[display_key] = [str(item.get(key, "")) for item in data]

        sections.append({
            "heading": heading,
            "content": table,
            "style": "table",
        })

    def _export_to_json(self) -> Path:
        """Export all data to JSON."""
        output_dir = self.core_api.get_case_output_dir("health_data")
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "health_all_data.json"

        export_data = {
            "workouts": self.workouts_data,
            "steps": self.steps_data,
            "heart_rate": self.heart_rate_data,
            "resting_heart_rate": self.resting_heart_rate_data,
            "sleep": self.sleep_data,
            "sleep_periods": self.sleep_period_data,
            "watch_worn": self.watch_worn_data,
            "achievements": self.achievements_data,
            "height": self.height_data,
            "weight": self.weight_data,
            "headphone_audio": self.headphone_audio_data,
            "wrist_temperature": self.wrist_temperature_data,
            "provenances": self.provenances_data,
            "source_devices": self.source_devices_data,
            "summary": {
                "total_workouts": len(self.workouts_data),
                "total_steps": len(self.steps_data),
                "total_heart_rate": len(self.heart_rate_data),
                "total_resting_heart_rate": len(self.resting_heart_rate_data),
                "total_sleep": len(self.sleep_data),
                "total_sleep_periods": len(self.sleep_period_data),
                "total_watch_worn": len(self.watch_worn_data),
                "total_achievements": len(self.achievements_data),
                "total_height": len(self.height_data),
                "total_weight": len(self.weight_data),
                "total_headphone_audio": len(self.headphone_audio_data),
                "total_wrist_temperature": len(self.wrist_temperature_data),
                "total_provenances": len(self.provenances_data),
                "total_devices": len(self.source_devices_data),
            },
            "errors": self.errors,
        }

        self.core_api.export_plugin_data_to_json(
            json_path,
            self.metadata.name,
            self.metadata.version,
            export_data,
            self.extraction_type,
        )

        self.core_api.print_success(f"JSON export: {json_path}")
        return json_path

    def _export_to_csv(self) -> list[str]:
        """Export each artifact to separate CSV files."""
        output_dir = self.core_api.get_case_output_dir("health_data")
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_paths = []

        artifacts = [
            ("workouts", self.workouts_data),
            ("steps", self.steps_data),
            ("heart_rate", self.heart_rate_data),
            ("resting_heart_rate", self.resting_heart_rate_data),
            ("sleep", self.sleep_data),
            ("sleep_periods", self.sleep_period_data),
            ("watch_worn", self.watch_worn_data),
            ("achievements", self.achievements_data),
            ("height", self.height_data),
            ("weight", self.weight_data),
            ("headphone_audio", self.headphone_audio_data),
            ("wrist_temperature", self.wrist_temperature_data),
            ("provenances", self.provenances_data),
            ("source_devices", self.source_devices_data),
        ]

        for name, data in artifacts:
            if data:
                csv_path = output_dir / f"health_{name}.csv"
                self.core_api.export_plugin_data_to_csv(
                    csv_path,
                    self.metadata.name,
                    self.metadata.version,
                    data,
                    self.extraction_type,
                )
                csv_paths.append(str(csv_path))

        if csv_paths:
            self.core_api.print_success(f"Exported {len(csv_paths)} CSV files")

        return csv_paths

    def cleanup(self) -> None:
        """Clean up plugin resources."""
        # Clean up temp directory if it still exists
        if self.temp_dir and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except Exception:
                pass

        self.core_api.log_info(f"Cleaning up {self.metadata.name}")
