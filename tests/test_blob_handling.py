"""Tests for BLOB handling in CoreAPI."""

import plistlib
import sqlite3
import zipfile
from pathlib import Path

import pytest

from yaft.core.api import CoreAPI


@pytest.fixture
def core_api(tmp_path):
    """Create CoreAPI instance with temp directory."""
    config_dir = tmp_path / "config"
    api = CoreAPI(config_dir=config_dir)
    api.base_output_dir = tmp_path / "yaft_output"
    return api


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory."""
    return tmp_path


# ========== BLOB Type Detection Tests ==========


def test_detect_blob_type_jpeg(core_api):
    """Test JPEG detection."""
    jpeg_data = b'\xff\xd8\xff' + b'\x00' * 100
    assert core_api.detect_blob_type(jpeg_data) == "jpeg"


def test_detect_blob_type_png(core_api):
    """Test PNG detection."""
    png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
    assert core_api.detect_blob_type(png_data) == "png"


def test_detect_blob_type_gif87(core_api):
    """Test GIF87a detection."""
    gif_data = b'GIF87a' + b'\x00' * 100
    assert core_api.detect_blob_type(gif_data) == "gif"


def test_detect_blob_type_gif89(core_api):
    """Test GIF89a detection."""
    gif_data = b'GIF89a' + b'\x00' * 100
    assert core_api.detect_blob_type(gif_data) == "gif"


def test_detect_blob_type_bmp(core_api):
    """Test BMP detection."""
    bmp_data = b'BM' + b'\x00' * 100
    assert core_api.detect_blob_type(bmp_data) == "bmp"


def test_detect_blob_type_ico(core_api):
    """Test ICO detection."""
    ico_data = b'\x00\x00\x01\x00' + b'\x00' * 100
    assert core_api.detect_blob_type(ico_data) == "ico"


def test_detect_blob_type_tiff_little_endian(core_api):
    """Test TIFF little-endian detection."""
    tiff_data = b'II*\x00' + b'\x00' * 100
    assert core_api.detect_blob_type(tiff_data) == "tiff"


def test_detect_blob_type_tiff_big_endian(core_api):
    """Test TIFF big-endian detection."""
    tiff_data = b'MM\x00*' + b'\x00' * 100
    assert core_api.detect_blob_type(tiff_data) == "tiff"


def test_detect_blob_type_plist(core_api):
    """Test binary plist detection."""
    plist_data = b'bplist00' + b'\x00' * 100
    assert core_api.detect_blob_type(plist_data) == "plist"


def test_detect_blob_type_unknown(core_api):
    """Test unknown type detection."""
    unknown_data = b'\x01\x02\x03\x04' + b'\x00' * 100
    assert core_api.detect_blob_type(unknown_data) == "unknown"


def test_detect_blob_type_empty(core_api):
    """Test empty data detection."""
    assert core_api.detect_blob_type(b'') == "unknown"


def test_detect_blob_type_too_short(core_api):
    """Test too short data detection."""
    assert core_api.detect_blob_type(b'\x01\x02\x03') == "unknown"


# ========== save_blob_as_file Tests ==========


def test_save_blob_as_file_jpeg_auto_extension(core_api, temp_dir):
    """Test saving JPEG with automatic extension detection."""
    jpeg_data = b'\xff\xd8\xff' + b'\x00' * 100
    output_path = temp_dir / "image.dat"

    saved_path = core_api.save_blob_as_file(jpeg_data, output_path, auto_extension=True)

    assert saved_path == temp_dir / "image.jpg"
    assert saved_path.exists()
    assert saved_path.read_bytes() == jpeg_data


def test_save_blob_as_file_png_auto_extension(core_api, temp_dir):
    """Test saving PNG with automatic extension detection."""
    png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
    output_path = temp_dir / "image.dat"

    saved_path = core_api.save_blob_as_file(png_data, output_path, auto_extension=True)

    assert saved_path == temp_dir / "image.png"
    assert saved_path.exists()


def test_save_blob_as_file_plist_auto_extension(core_api, temp_dir):
    """Test saving plist with automatic extension detection."""
    plist_data = b'bplist00' + b'\x00' * 100
    output_path = temp_dir / "data.dat"

    saved_path = core_api.save_blob_as_file(plist_data, output_path, auto_extension=True)

    assert saved_path == temp_dir / "data.plist"
    assert saved_path.exists()


def test_save_blob_as_file_no_auto_extension(core_api, temp_dir):
    """Test saving without automatic extension."""
    jpeg_data = b'\xff\xd8\xff' + b'\x00' * 100
    output_path = temp_dir / "image.dat"

    saved_path = core_api.save_blob_as_file(jpeg_data, output_path, auto_extension=False)

    assert saved_path == output_path
    assert saved_path.exists()
    assert saved_path.read_bytes() == jpeg_data


def test_save_blob_as_file_unknown_type(core_api, temp_dir):
    """Test saving unknown type doesn't change extension."""
    unknown_data = b'\x01\x02\x03\x04' + b'\x00' * 100
    output_path = temp_dir / "data.bin"

    saved_path = core_api.save_blob_as_file(unknown_data, output_path, auto_extension=True)

    assert saved_path == output_path
    assert saved_path.exists()


def test_save_blob_as_file_creates_directories(core_api, temp_dir):
    """Test that parent directories are created."""
    jpeg_data = b'\xff\xd8\xff' + b'\x00' * 100
    output_path = temp_dir / "subdir" / "nested" / "image.jpg"

    saved_path = core_api.save_blob_as_file(jpeg_data, output_path)

    assert saved_path.exists()
    assert output_path.parent.exists()


# ========== parse_blob_as_plist Tests ==========


def test_parse_blob_as_plist_dict(core_api):
    """Test parsing binary plist dict."""
    # Create a simple plist
    plist_dict = {"name": "Test", "version": "1.0", "enabled": True}
    plist_bytes = plistlib.dumps(plist_dict, fmt=plistlib.FMT_BINARY)

    result = core_api.parse_blob_as_plist(plist_bytes)

    assert result == plist_dict
    assert result["name"] == "Test"
    assert result["version"] == "1.0"
    assert result["enabled"] is True


def test_parse_blob_as_plist_list(core_api):
    """Test parsing binary plist list."""
    plist_list = ["item1", "item2", "item3"]
    plist_bytes = plistlib.dumps(plist_list, fmt=plistlib.FMT_BINARY)

    result = core_api.parse_blob_as_plist(plist_bytes)

    assert result == plist_list


def test_parse_blob_as_plist_invalid_data(core_api):
    """Test parsing invalid plist data raises exception."""
    invalid_data = b'\x00\x01\x02\x03\x04\x05'

    with pytest.raises(Exception):
        core_api.parse_blob_as_plist(invalid_data)


# ========== extract_blob_from_zip Tests ==========


def test_extract_blob_from_zip_single_blob(core_api, temp_dir):
    """Test extracting single BLOB from ZIP."""
    zip_path = temp_dir / "test.zip"

    # Create database with BLOB data
    db_path = temp_dir / "test.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create table with BLOB column
    cursor.execute("CREATE TABLE images (id INTEGER, name TEXT, data BLOB)")

    # Insert JPEG blob
    jpeg_data = b'\xff\xd8\xff' + b'\x00' * 100
    cursor.execute("INSERT INTO images VALUES (?, ?, ?)", (1, "avatar.jpg", jpeg_data))

    # Insert PNG blob
    png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 200
    cursor.execute("INSERT INTO images VALUES (?, ?, ?)", (2, "icon.png", png_data))

    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(db_path, "test.db")

    # Set ZIP file and extract BLOB
    core_api.set_zip_file(zip_path)

    blob = core_api.extract_blob_from_zip("test.db", "SELECT data FROM images WHERE id = 1")

    assert blob is not None
    assert blob == jpeg_data


def test_extract_blob_from_zip_with_params(core_api, temp_dir):
    """Test extracting BLOB with query parameters."""
    zip_path = temp_dir / "test.zip"

    # Create database
    db_path = temp_dir / "test.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("CREATE TABLE contacts (id INTEGER, name TEXT, photo BLOB)")
    photo_blob = b'\xff\xd8\xff' + b'photo_data' * 10
    cursor.execute("INSERT INTO contacts VALUES (?, ?, ?)", (1, "John", photo_blob))
    cursor.execute("INSERT INTO contacts VALUES (?, ?, ?)", (2, "Jane", b'other_photo'))

    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(db_path, "test.db")

    core_api.set_zip_file(zip_path)

    blob = core_api.extract_blob_from_zip(
        "test.db",
        "SELECT photo FROM contacts WHERE name = ?",
        params=("John",)
    )

    assert blob == photo_blob


def test_extract_blob_from_zip_no_results(core_api, temp_dir):
    """Test extracting BLOB when query returns no results."""
    zip_path = temp_dir / "test.zip"

    # Create empty database
    db_path = temp_dir / "test.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE images (id INTEGER, data BLOB)")
    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(db_path, "test.db")

    core_api.set_zip_file(zip_path)

    blob = core_api.extract_blob_from_zip("test.db", "SELECT data FROM images WHERE id = 999")

    assert blob is None


def test_extract_blob_from_zip_null_value(core_api, temp_dir):
    """Test extracting NULL BLOB returns None."""
    zip_path = temp_dir / "test.zip"

    # Create database with NULL BLOB
    db_path = temp_dir / "test.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE images (id INTEGER, data BLOB)")
    cursor.execute("INSERT INTO images VALUES (1, NULL)")
    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(db_path, "test.db")

    core_api.set_zip_file(zip_path)

    blob = core_api.extract_blob_from_zip("test.db", "SELECT data FROM images WHERE id = 1")

    assert blob is None


# ========== extract_blobs_from_zip Tests ==========


def test_extract_blobs_from_zip_multiple(core_api, temp_dir):
    """Test extracting multiple BLOBs from ZIP."""
    zip_path = temp_dir / "test.zip"

    # Create database with multiple BLOBs
    db_path = temp_dir / "test.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("CREATE TABLE photos (id INTEGER, data BLOB)")

    blob1 = b'\xff\xd8\xff' + b'photo1' * 10
    blob2 = b'\x89PNG\r\n\x1a\n' + b'photo2' * 10
    blob3 = b'GIF89a' + b'photo3' * 10

    cursor.execute("INSERT INTO photos VALUES (?, ?)", (1, blob1))
    cursor.execute("INSERT INTO photos VALUES (?, ?)", (2, blob2))
    cursor.execute("INSERT INTO photos VALUES (?, ?)", (3, blob3))

    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(db_path, "test.db")

    core_api.set_zip_file(zip_path)

    blobs = core_api.extract_blobs_from_zip("test.db", "SELECT data FROM photos ORDER BY id")

    assert len(blobs) == 3
    assert blobs[0] == blob1
    assert blobs[1] == blob2
    assert blobs[2] == blob3


def test_extract_blobs_from_zip_excludes_nulls(core_api, temp_dir):
    """Test that NULL values are excluded from results."""
    zip_path = temp_dir / "test.zip"

    # Create database with NULLs
    db_path = temp_dir / "test.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("CREATE TABLE photos (id INTEGER, data BLOB)")
    cursor.execute("INSERT INTO photos VALUES (1, ?)", (b'blob1',))
    cursor.execute("INSERT INTO photos VALUES (2, NULL)")
    cursor.execute("INSERT INTO photos VALUES (3, ?)", (b'blob3',))

    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(db_path, "test.db")

    core_api.set_zip_file(zip_path)

    blobs = core_api.extract_blobs_from_zip("test.db", "SELECT data FROM photos ORDER BY id")

    # Should only return non-NULL values
    assert len(blobs) == 2
    assert blobs[0] == b'blob1'
    assert blobs[1] == b'blob3'


def test_extract_blobs_from_zip_empty_results(core_api, temp_dir):
    """Test extracting BLOBs when query returns no results."""
    zip_path = temp_dir / "test.zip"

    # Create empty database
    db_path = temp_dir / "test.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE photos (id INTEGER, data BLOB)")
    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(db_path, "test.db")

    core_api.set_zip_file(zip_path)

    blobs = core_api.extract_blobs_from_zip("test.db", "SELECT data FROM photos")

    assert blobs == []


# ========== Integration Tests ==========


def test_blob_workflow_extract_and_save(core_api, temp_dir):
    """Test complete workflow: extract BLOB and save to file."""
    zip_path = temp_dir / "test.zip"

    # Create database with JPEG BLOB
    db_path = temp_dir / "test.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE avatars (user_id INTEGER, photo BLOB)")

    jpeg_data = b'\xff\xd8\xff' + b'\x00' * 500
    cursor.execute("INSERT INTO avatars VALUES (?, ?)", (123, jpeg_data))

    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(db_path, "test.db")

    core_api.set_zip_file(zip_path)

    # Extract BLOB
    blob = core_api.extract_blob_from_zip(
        "test.db",
        "SELECT photo FROM avatars WHERE user_id = ?",
        params=(123,)
    )

    assert blob is not None

    # Detect type
    blob_type = core_api.detect_blob_type(blob)
    assert blob_type == "jpeg"

    # Save to file
    output_path = temp_dir / "output" / "avatar.dat"
    saved_path = core_api.save_blob_as_file(blob, output_path, auto_extension=True)

    assert saved_path == temp_dir / "output" / "avatar.jpg"
    assert saved_path.exists()
    assert saved_path.read_bytes() == jpeg_data


def test_blob_workflow_extract_plist_and_parse(core_api, temp_dir):
    """Test complete workflow: extract plist BLOB and parse it."""
    zip_path = temp_dir / "test.zip"

    # Create plist data
    plist_dict = {
        "app_name": "TestApp",
        "version": "2.0.1",
        "settings": {
            "enabled": True,
            "count": 42
        }
    }
    plist_blob = plistlib.dumps(plist_dict, fmt=plistlib.FMT_BINARY)

    # Create database
    db_path = temp_dir / "test.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE preferences (key TEXT, value BLOB)")
    cursor.execute("INSERT INTO preferences VALUES (?, ?)", ("app_config", plist_blob))
    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(db_path, "test.db")

    core_api.set_zip_file(zip_path)

    # Extract BLOB
    blob = core_api.extract_blob_from_zip(
        "test.db",
        "SELECT value FROM preferences WHERE key = ?",
        params=("app_config",)
    )

    assert blob is not None

    # Detect type
    blob_type = core_api.detect_blob_type(blob)
    assert blob_type == "plist"

    # Parse as plist
    parsed_data = core_api.parse_blob_as_plist(blob)

    assert parsed_data == plist_dict
    assert parsed_data["app_name"] == "TestApp"
    assert parsed_data["settings"]["count"] == 42


def test_blob_batch_extraction(core_api, temp_dir):
    """Test batch extraction of multiple BLOBs with different types."""
    zip_path = temp_dir / "test.zip"

    # Create database with various BLOBs
    db_path = temp_dir / "test.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE media (id INTEGER, type TEXT, data BLOB)")

    jpeg_blob = b'\xff\xd8\xff' + b'jpeg_data' * 20
    png_blob = b'\x89PNG\r\n\x1a\n' + b'png_data' * 20
    gif_blob = b'GIF89a' + b'gif_data' * 20

    cursor.execute("INSERT INTO media VALUES (?, ?, ?)", (1, "avatar", jpeg_blob))
    cursor.execute("INSERT INTO media VALUES (?, ?, ?)", (2, "icon", png_blob))
    cursor.execute("INSERT INTO media VALUES (?, ?, ?)", (3, "banner", gif_blob))

    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(db_path, "test.db")

    core_api.set_zip_file(zip_path)

    # Extract all BLOBs
    blobs = core_api.extract_blobs_from_zip("test.db", "SELECT data FROM media ORDER BY id")

    assert len(blobs) == 3

    # Save each with auto-detection
    output_dir = temp_dir / "output"
    for i, blob in enumerate(blobs):
        saved_path = core_api.save_blob_as_file(blob, output_dir / f"media_{i}.dat")
        assert saved_path.exists()

    # Verify extensions were corrected
    assert (output_dir / "media_0.jpg").exists()
    assert (output_dir / "media_1.png").exists()
    assert (output_dir / "media_2.gif").exists()


# ========== SQLCipher BLOB Tests ==========

# Check if sqlcipher3 is available
try:
    from sqlcipher3 import dbapi2 as sqlcipher
    SQLCIPHER_AVAILABLE = True
except ImportError:
    SQLCIPHER_AVAILABLE = False

pytestmark_sqlcipher = pytest.mark.skipif(
    not SQLCIPHER_AVAILABLE,
    reason="sqlcipher3 not installed"
)


@pytest.mark.skipif(not SQLCIPHER_AVAILABLE, reason="sqlcipher3 not installed")
def test_extract_blob_from_sqlcipher_zip_single(core_api, temp_dir):
    """Test extracting single BLOB from encrypted database."""
    from sqlcipher3 import dbapi2 as sqlcipher

    zip_path = temp_dir / "test.zip"
    encryption_key = "test_encryption_key_123"

    # Create encrypted database with BLOB
    db_path = temp_dir / "encrypted.db"
    conn = sqlcipher.connect(str(db_path))
    cursor = conn.cursor()

    # Set encryption key
    cursor.execute(f"PRAGMA key = '{encryption_key}'")

    # Create table and insert BLOB
    cursor.execute("CREATE TABLE avatars (user_id INTEGER, photo BLOB)")
    jpeg_blob = b'\xff\xd8\xff' + b'encrypted_photo' * 10
    cursor.execute("INSERT INTO avatars VALUES (?, ?)", (1, jpeg_blob))

    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(db_path, "encrypted.db")

    core_api.set_zip_file(zip_path)

    # Extract BLOB
    blob = core_api.extract_blob_from_sqlcipher_zip(
        "encrypted.db",
        encryption_key,
        "SELECT photo FROM avatars WHERE user_id = ?",
        params=(1,)
    )

    assert blob is not None
    assert blob == jpeg_blob


@pytest.mark.skipif(not SQLCIPHER_AVAILABLE, reason="sqlcipher3 not installed")
def test_extract_blob_from_sqlcipher_zip_wrong_key(core_api, temp_dir):
    """Test that wrong encryption key raises error."""
    from sqlcipher3 import dbapi2 as sqlcipher

    zip_path = temp_dir / "test.zip"
    correct_key = "correct_key_123"
    wrong_key = "wrong_key_456"

    # Create encrypted database
    db_path = temp_dir / "encrypted.db"
    conn = sqlcipher.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA key = '{correct_key}'")
    cursor.execute("CREATE TABLE data (id INTEGER, content BLOB)")
    cursor.execute("INSERT INTO data VALUES (1, ?)", (b'secret_data',))
    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(db_path, "encrypted.db")

    core_api.set_zip_file(zip_path)

    # Try to extract with wrong key
    with pytest.raises(ValueError, match="Failed to decrypt database"):
        core_api.extract_blob_from_sqlcipher_zip(
            "encrypted.db",
            wrong_key,
            "SELECT content FROM data WHERE id = 1"
        )


@pytest.mark.skipif(not SQLCIPHER_AVAILABLE, reason="sqlcipher3 not installed")
def test_extract_blobs_from_sqlcipher_zip_multiple(core_api, temp_dir):
    """Test extracting multiple BLOBs from encrypted database."""
    from sqlcipher3 import dbapi2 as sqlcipher

    zip_path = temp_dir / "test.zip"
    encryption_key = "test_key_456"

    # Create encrypted database with multiple BLOBs
    db_path = temp_dir / "encrypted.db"
    conn = sqlcipher.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA key = '{encryption_key}'")

    cursor.execute("CREATE TABLE attachments (id INTEGER, data BLOB)")

    blob1 = b'\xff\xd8\xff' + b'attachment1' * 10
    blob2 = b'\x89PNG\r\n\x1a\n' + b'attachment2' * 10
    blob3 = b'GIF89a' + b'attachment3' * 10

    cursor.execute("INSERT INTO attachments VALUES (?, ?)", (1, blob1))
    cursor.execute("INSERT INTO attachments VALUES (?, ?)", (2, blob2))
    cursor.execute("INSERT INTO attachments VALUES (?, ?)", (3, blob3))

    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(db_path, "encrypted.db")

    core_api.set_zip_file(zip_path)

    # Extract all BLOBs
    blobs = core_api.extract_blobs_from_sqlcipher_zip(
        "encrypted.db",
        encryption_key,
        "SELECT data FROM attachments ORDER BY id"
    )

    assert len(blobs) == 3
    assert blobs[0] == blob1
    assert blobs[1] == blob2
    assert blobs[2] == blob3


@pytest.mark.skipif(not SQLCIPHER_AVAILABLE, reason="sqlcipher3 not installed")
def test_extract_blob_from_sqlcipher_zip_with_cipher_version(core_api, temp_dir):
    """Test extracting BLOB with specific cipher version."""
    from sqlcipher3 import dbapi2 as sqlcipher

    zip_path = temp_dir / "test.zip"
    encryption_key = "test_key_v3"

    # Create encrypted database
    db_path = temp_dir / "encrypted.db"
    conn = sqlcipher.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA key = '{encryption_key}'")
    cursor.execute("PRAGMA cipher_compatibility = 3")  # Use version 3

    cursor.execute("CREATE TABLE data (id INTEGER, blob_data BLOB)")
    test_blob = b'\xff\xd8\xff' + b'v3_data' * 10
    cursor.execute("INSERT INTO data VALUES (?, ?)", (1, test_blob))

    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(db_path, "encrypted.db")

    core_api.set_zip_file(zip_path)

    # Extract with cipher version 3
    blob = core_api.extract_blob_from_sqlcipher_zip(
        "encrypted.db",
        encryption_key,
        "SELECT blob_data FROM data WHERE id = 1",
        cipher_version=3
    )

    assert blob is not None
    assert blob == test_blob


@pytest.mark.skipif(not SQLCIPHER_AVAILABLE, reason="sqlcipher3 not installed")
def test_sqlcipher_blob_workflow_whatsapp_scenario(core_api, temp_dir):
    """Test realistic WhatsApp-like scenario: extract encrypted avatar and save."""
    from sqlcipher3 import dbapi2 as sqlcipher

    zip_path = temp_dir / "whatsapp_extraction.zip"
    whatsapp_key = "whatsapp_encryption_key"

    # Create WhatsApp-like database structure
    db_path = temp_dir / "wa.db"
    conn = sqlcipher.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA key = '{whatsapp_key}'")

    # Create contacts table with photo BLOBs
    cursor.execute("CREATE TABLE wa_contacts (jid TEXT, display_name TEXT, photo BLOB)")

    # Insert contacts with avatar photos
    avatar1 = b'\xff\xd8\xff' + b'contact1_photo' * 20
    avatar2 = b'\x89PNG\r\n\x1a\n' + b'contact2_photo' * 20

    cursor.execute("INSERT INTO wa_contacts VALUES (?, ?, ?)",
                   ("+1234567890@s.whatsapp.net", "John Doe", avatar1))
    cursor.execute("INSERT INTO wa_contacts VALUES (?, ?, ?)",
                   ("+0987654321@s.whatsapp.net", "Jane Smith", avatar2))
    cursor.execute("INSERT INTO wa_contacts VALUES (?, ?, ?)",
                   ("+1111111111@s.whatsapp.net", "No Avatar", None))

    conn.commit()
    conn.close()

    # Create ZIP (simulating forensic extraction)
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(db_path, "data/data/com.whatsapp/databases/wa.db")

    core_api.set_zip_file(zip_path)

    # Extract all contact avatars (excluding NULLs)
    avatars = core_api.extract_blobs_from_sqlcipher_zip(
        "data/data/com.whatsapp/databases/wa.db",
        whatsapp_key,
        "SELECT photo FROM wa_contacts WHERE photo IS NOT NULL ORDER BY jid"
    )

    assert len(avatars) == 2

    # Save avatars with auto-detection
    output_dir = temp_dir / "whatsapp_avatars"
    for i, avatar in enumerate(avatars):
        saved_path = core_api.save_blob_as_file(
            avatar,
            output_dir / f"contact_{i}.dat",
            auto_extension=True
        )
        assert saved_path.exists()

    # Verify file types were detected and extensions corrected
    assert (output_dir / "contact_0.jpg").exists()
    assert (output_dir / "contact_1.png").exists()
