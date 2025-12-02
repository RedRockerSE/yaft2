"""Tests for iOS Keychain and Android Keystore extraction in CoreAPI."""

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


# ========== iOS Keychain Tests ==========


def test_parse_ios_keychain_generic_passwords(core_api, temp_dir):
    """Test parsing iOS keychain generic passwords (genp table)."""
    zip_path = temp_dir / "ios_extraction.zip"

    # Create mock keychain database
    keychain_db = temp_dir / "keychain-2.db"
    conn = sqlite3.connect(str(keychain_db))
    cursor = conn.cursor()

    # Create genp table
    cursor.execute("""
        CREATE TABLE genp (
            rowid INTEGER PRIMARY KEY,
            cdat REAL,
            mdat REAL,
            desc TEXT,
            labl TEXT,
            acct BLOB,
            svce BLOB,
            agrp TEXT,
            pdmn BLOB,
            sync INTEGER,
            data BLOB,
            sha1 BLOB
        )
    """)

    # Insert test data
    cursor.execute("""
        INSERT INTO genp (rowid, cdat, mdat, desc, labl, acct, svce, agrp, pdmn, sync, data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        1,
        631152000.0,  # Creation date (Apple timestamp)
        631152000.0,  # Modification date
        b'Mail Password',
        b'work@example.com',
        b'\x00\x01\x02\x03',  # Encrypted account
        b'\x04\x05\x06\x07',  # Encrypted service
        'com.apple.mail',
        b'ck',  # Protection domain
        1,  # Sync enabled
        b'\x08\x09\x0a\x0b'  # Encrypted data
    ))

    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(keychain_db, "private/var/Keychains/keychain-2.db")

    core_api.set_zip_file(zip_path)

    # Parse keychain
    result = core_api.parse_ios_keychain("private/var/Keychains/keychain-2.db")

    # Verify results
    assert result is not None
    assert 'generic_passwords' in result
    assert len(result['generic_passwords']) == 1

    entry = result['generic_passwords'][0]
    assert entry['rowid'] == 1
    assert entry['access_group'] == 'com.apple.mail'
    assert entry['sync_enabled'] is True
    assert entry['is_encrypted'] is True
    assert entry['type'] == 'generic_password'

    # Verify summary
    assert result['summary']['total_entries'] == 1
    assert result['summary']['generic_passwords_count'] == 1
    assert result['summary']['encrypted_entries'] == 1

    # Verify security note exists
    assert 'security_note' in result
    assert 'Secure Enclave' in result['security_note']


def test_parse_ios_keychain_internet_passwords(core_api, temp_dir):
    """Test parsing iOS keychain internet passwords (inet table)."""
    zip_path = temp_dir / "ios_extraction.zip"

    # Create mock keychain database
    keychain_db = temp_dir / "keychain-2.db"
    conn = sqlite3.connect(str(keychain_db))
    cursor = conn.cursor()

    # Create genp table (empty)
    cursor.execute("""
        CREATE TABLE genp (
            rowid INTEGER PRIMARY KEY,
            cdat REAL,
            mdat REAL,
            data BLOB
        )
    """)

    # Create inet table
    cursor.execute("""
        CREATE TABLE inet (
            rowid INTEGER PRIMARY KEY,
            cdat REAL,
            mdat REAL,
            desc TEXT,
            labl TEXT,
            acct BLOB,
            sdmn TEXT,
            srvr TEXT,
            ptcl INTEGER,
            atyp INTEGER,
            port INTEGER,
            path TEXT,
            agrp TEXT,
            pdmn BLOB,
            sync INTEGER,
            data BLOB
        )
    """)

    # Insert test data
    cursor.execute("""
        INSERT INTO inet (rowid, cdat, mdat, labl, acct, srvr, ptcl, port, agrp, sync, data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        1,
        631152000.0,
        631152000.0,
        b'Gmail',
        b'\x00\x01\x02\x03',  # Encrypted account
        'imap.gmail.com',
        143,  # IMAP port
        993,  # IMAP SSL port
        'com.apple.mail',
        1,
        b'\x08\x09\x0a\x0b'  # Encrypted data
    ))

    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(keychain_db, "private/var/Keychains/keychain-2.db")

    core_api.set_zip_file(zip_path)

    # Parse keychain
    result = core_api.parse_ios_keychain("private/var/Keychains/keychain-2.db")

    # Verify results
    assert 'internet_passwords' in result
    assert len(result['internet_passwords']) == 1

    entry = result['internet_passwords'][0]
    assert entry['rowid'] == 1
    assert entry['server'] == 'imap.gmail.com'
    assert entry['port'] == 993
    assert entry['access_group'] == 'com.apple.mail'
    assert entry['is_encrypted'] is True
    assert entry['type'] == 'internet_password'


def test_parse_ios_keychain_empty_tables(core_api, temp_dir):
    """Test parsing iOS keychain with empty tables."""
    zip_path = temp_dir / "ios_extraction.zip"

    # Create empty keychain database
    keychain_db = temp_dir / "keychain-2.db"
    conn = sqlite3.connect(str(keychain_db))
    cursor = conn.cursor()

    # Create empty tables
    cursor.execute("CREATE TABLE genp (rowid INTEGER PRIMARY KEY)")
    cursor.execute("CREATE TABLE inet (rowid INTEGER PRIMARY KEY)")
    cursor.execute("CREATE TABLE cert (rowid INTEGER PRIMARY KEY)")
    cursor.execute("CREATE TABLE keys (rowid INTEGER PRIMARY KEY)")

    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(keychain_db, "private/var/Keychains/keychain-2.db")

    core_api.set_zip_file(zip_path)

    # Parse keychain
    result = core_api.parse_ios_keychain("private/var/Keychains/keychain-2.db")

    # Verify empty results
    assert result['summary']['total_entries'] == 0
    assert result['summary']['generic_passwords_count'] == 0
    assert result['summary']['internet_passwords_count'] == 0
    assert result['summary']['certificates_count'] == 0
    assert result['summary']['keys_count'] == 0


# ========== Android Locksettings Tests ==========


def test_parse_android_locksettings_pin(core_api, temp_dir):
    """Test parsing Android locksettings with PIN lock."""
    zip_path = temp_dir / "android_extraction.zip"

    # Create mock locksettings database
    locksettings_db = temp_dir / "locksettings.db"
    conn = sqlite3.connect(str(locksettings_db))
    cursor = conn.cursor()

    # Create locksettings table
    cursor.execute("""
        CREATE TABLE locksettings (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            user INTEGER,
            value TEXT
        )
    """)

    # Insert PIN lock settings
    cursor.execute("INSERT INTO locksettings (name, user, value) VALUES (?, ?, ?)",
                   ('lockscreen.password_type', 0, '196608'))  # PIN
    cursor.execute("INSERT INTO locksettings (name, user, value) VALUES (?, ?, ?)",
                   ('lockscreen.passwordhistory', 0, 'hashed_password_history'))
    cursor.execute("INSERT INTO locksettings (name, user, value) VALUES (?, ?, ?)",
                   ('lockscreen.disabled', 0, '0'))

    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(locksettings_db, "data/system/locksettings.db")

    core_api.set_zip_file(zip_path)

    # Parse locksettings
    result = core_api.parse_android_locksettings("data/system/locksettings.db")

    # Verify results
    assert result is not None
    assert 'lock_settings' in result
    assert 'summary' in result

    # Verify lock type
    assert result['summary']['lock_type'] == 'PIN'
    assert result['summary']['lock_password_enabled'] is True
    assert result['summary']['lockscreen_disabled'] is False

    # Verify security note exists
    assert 'security_note' in result
    assert 'Gatekeeper' in result['security_note']


def test_parse_android_locksettings_pattern(core_api, temp_dir):
    """Test parsing Android locksettings with pattern lock."""
    zip_path = temp_dir / "android_extraction.zip"

    # Create mock locksettings database
    locksettings_db = temp_dir / "locksettings.db"
    conn = sqlite3.connect(str(locksettings_db))
    cursor = conn.cursor()

    # Create locksettings table
    cursor.execute("""
        CREATE TABLE locksettings (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            user INTEGER,
            value TEXT
        )
    """)

    # Insert pattern lock settings
    cursor.execute("INSERT INTO locksettings (name, user, value) VALUES (?, ?, ?)",
                   ('lockscreen.password_type', 0, '131072'))  # Pattern
    cursor.execute("INSERT INTO locksettings (name, user, value) VALUES (?, ?, ?)",
                   ('lockscreen.patterneverchosen', 0, '0'))  # Pattern chosen

    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(locksettings_db, "data/system/locksettings.db")

    core_api.set_zip_file(zip_path)

    # Parse locksettings
    result = core_api.parse_android_locksettings("data/system/locksettings.db")

    # Verify lock type
    assert result['summary']['lock_type'] == 'pattern'
    assert result['summary']['lock_pattern_enabled'] is True


def test_parse_android_locksettings_password(core_api, temp_dir):
    """Test parsing Android locksettings with password lock."""
    zip_path = temp_dir / "android_extraction.zip"

    # Create mock locksettings database
    locksettings_db = temp_dir / "locksettings.db"
    conn = sqlite3.connect(str(locksettings_db))
    cursor = conn.cursor()

    # Create locksettings table
    cursor.execute("""
        CREATE TABLE locksettings (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            user INTEGER,
            value TEXT
        )
    """)

    # Insert password lock settings
    cursor.execute("INSERT INTO locksettings (name, user, value) VALUES (?, ?, ?)",
                   ('lockscreen.password_type', 0, '262144'))  # Password

    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(locksettings_db, "data/system/locksettings.db")

    core_api.set_zip_file(zip_path)

    # Parse locksettings
    result = core_api.parse_android_locksettings("data/system/locksettings.db")

    # Verify lock type
    assert result['summary']['lock_type'] == 'password'
    assert result['summary']['lock_password_enabled'] is True


def test_parse_android_locksettings_no_lock(core_api, temp_dir):
    """Test parsing Android locksettings with no lock screen."""
    zip_path = temp_dir / "android_extraction.zip"

    # Create mock locksettings database
    locksettings_db = temp_dir / "locksettings.db"
    conn = sqlite3.connect(str(locksettings_db))
    cursor = conn.cursor()

    # Create locksettings table
    cursor.execute("""
        CREATE TABLE locksettings (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            user INTEGER,
            value TEXT
        )
    """)

    # Insert no lock settings
    cursor.execute("INSERT INTO locksettings (name, user, value) VALUES (?, ?, ?)",
                   ('lockscreen.password_type', 0, '0'))  # No lock
    cursor.execute("INSERT INTO locksettings (name, user, value) VALUES (?, ?, ?)",
                   ('lockscreen.disabled', 0, '1'))  # Disabled

    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(locksettings_db, "data/system/locksettings.db")

    core_api.set_zip_file(zip_path)

    # Parse locksettings
    result = core_api.parse_android_locksettings("data/system/locksettings.db")

    # Verify no lock
    assert result['summary']['lock_type'] == 'none'
    assert result['summary']['lockscreen_disabled'] is True


def test_parse_android_locksettings_multiuser(core_api, temp_dir):
    """Test parsing Android locksettings with multiple users."""
    zip_path = temp_dir / "android_extraction.zip"

    # Create mock locksettings database
    locksettings_db = temp_dir / "locksettings.db"
    conn = sqlite3.connect(str(locksettings_db))
    cursor = conn.cursor()

    # Create locksettings table
    cursor.execute("""
        CREATE TABLE locksettings (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            user INTEGER,
            value TEXT
        )
    """)

    # Insert settings for multiple users
    cursor.execute("INSERT INTO locksettings (name, user, value) VALUES (?, ?, ?)",
                   ('lockscreen.password_type', 0, '196608'))  # User 0: PIN
    cursor.execute("INSERT INTO locksettings (name, user, value) VALUES (?, ?, ?)",
                   ('lockscreen.password_type', 10, '131072'))  # User 10: Pattern

    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(locksettings_db, "data/system/locksettings.db")

    core_api.set_zip_file(zip_path)

    # Parse locksettings
    result = core_api.parse_android_locksettings("data/system/locksettings.db")

    # Verify multiple users
    assert result['summary']['user_count'] == 2
    assert 0 in result['user_settings']
    assert 10 in result['user_settings']


# ========== Android Keystore Tests ==========


def test_identify_android_keystore_files_masterkey(core_api, temp_dir):
    """Test identifying Android keystore .masterkey files."""
    zip_path = temp_dir / "android_extraction.zip"

    # Create mock keystore files
    keystore_dir = temp_dir / "keystore"
    keystore_dir.mkdir()

    (keystore_dir / ".masterkey").write_bytes(b'\x00\x01\x02\x03')
    (keystore_dir / "user_0").mkdir()
    (keystore_dir / "user_0" / ".masterkey").write_bytes(b'\x04\x05\x06\x07')

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(keystore_dir / ".masterkey", "data/misc/keystore/.masterkey")
        zf.write(keystore_dir / "user_0" / ".masterkey", "data/misc/keystore/user_0/.masterkey")

    core_api.set_zip_file(zip_path)

    # Identify keystore files
    result = core_api.identify_android_keystore_files()

    # Verify results
    assert result is not None
    assert 'keystore_files' in result
    assert len(result['keystore_files']) == 2

    # Verify masterkey files found
    masterkey_files = [f for f in result['keystore_files'] if f['type'] == 'master_key']
    assert len(masterkey_files) == 2

    # Verify user-specific keystore
    assert '0' in result['user_keystores']
    assert len(result['user_keystores']['0']) == 1


def test_identify_android_keystore_files_gatekeeper(core_api, temp_dir):
    """Test identifying Android Gatekeeper credential files."""
    zip_path = temp_dir / "android_extraction.zip"

    # Create mock credential files in data/system
    system_dir = temp_dir / "system"
    system_dir.mkdir()

    (system_dir / "gatekeeper.password.key").write_bytes(b'\x00\x01\x02\x03')
    (system_dir / "gatekeeper.pattern.key").write_bytes(b'\x04\x05\x06\x07')

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(system_dir / "gatekeeper.password.key", "data/system/gatekeeper.password.key")
        zf.write(system_dir / "gatekeeper.pattern.key", "data/system/gatekeeper.pattern.key")

    core_api.set_zip_file(zip_path)

    # Identify keystore files
    result = core_api.identify_android_keystore_files()

    # Verify results
    assert 'credential_files' in result
    assert len(result['credential_files']) >= 2

    # Verify Gatekeeper detection
    assert result['summary']['has_gatekeeper'] is True

    # Verify credential files
    gatekeeper_files = [f for f in result['credential_files'] if f['type'] == 'gatekeeper_key']
    assert len(gatekeeper_files) >= 2


def test_identify_android_keystore_files_legacy(core_api, temp_dir):
    """Test identifying legacy Android credential files."""
    zip_path = temp_dir / "android_extraction.zip"

    # Create legacy credential files
    system_dir = temp_dir / "system"
    system_dir.mkdir()

    (system_dir / "password.key").write_bytes(b'\x00\x01\x02\x03')
    (system_dir / "gesture.key").write_bytes(b'\x04\x05\x06\x07')

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(system_dir / "password.key", "data/system/password.key")
        zf.write(system_dir / "gesture.key", "data/system/gesture.key")

    core_api.set_zip_file(zip_path)

    # Identify keystore files
    result = core_api.identify_android_keystore_files()

    # Verify results
    assert result['summary']['has_legacy_credentials'] is True

    # Verify credential files
    legacy_files = [f for f in result['credential_files'] if f['type'] == 'legacy_credential']
    assert len(legacy_files) >= 2


def test_identify_android_keystore_files_empty(core_api, temp_dir):
    """Test identifying keystore files when none exist."""
    zip_path = temp_dir / "android_extraction.zip"

    # Create empty ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        pass

    core_api.set_zip_file(zip_path)

    # Identify keystore files
    result = core_api.identify_android_keystore_files()

    # Verify empty results
    assert result['summary']['total_keystore_files'] == 0
    assert result['summary']['total_credential_files'] == 0
    assert result['summary']['has_gatekeeper'] is False
    assert result['summary']['has_legacy_credentials'] is False

    # Verify security note exists
    assert 'security_note' in result
    assert 'TEE' in result['security_note']


# ========== Integration Tests ==========


def test_ios_keychain_full_workflow(core_api, temp_dir):
    """Test complete iOS keychain extraction workflow."""
    zip_path = temp_dir / "ios_extraction.zip"

    # Create comprehensive keychain database
    keychain_db = temp_dir / "keychain-2.db"
    conn = sqlite3.connect(str(keychain_db))
    cursor = conn.cursor()

    # Create all tables with required columns
    cursor.execute("CREATE TABLE genp (rowid INTEGER PRIMARY KEY, cdat REAL, mdat REAL, desc TEXT, labl TEXT, acct BLOB, svce BLOB, agrp TEXT, pdmn BLOB, sync INTEGER, data BLOB, sha1 BLOB)")
    cursor.execute("CREATE TABLE inet (rowid INTEGER PRIMARY KEY, cdat REAL, mdat REAL, desc TEXT, labl TEXT, acct BLOB, sdmn TEXT, srvr TEXT, ptcl INTEGER, atyp INTEGER, port INTEGER, path TEXT, agrp TEXT, pdmn BLOB, sync INTEGER, data BLOB)")
    cursor.execute("CREATE TABLE cert (rowid INTEGER PRIMARY KEY, cdat REAL, mdat REAL, ctyp INTEGER, cenc INTEGER, labl TEXT, certType INTEGER, agrp TEXT, pdmn BLOB, sync INTEGER, data BLOB, sha1 BLOB)")
    cursor.execute("CREATE TABLE keys (rowid INTEGER PRIMARY KEY, cdat REAL, mdat REAL, kcls INTEGER, labl TEXT, atag BLOB, crtr INTEGER, type INTEGER, bsiz INTEGER, esiz INTEGER, agrp TEXT, pdmn BLOB, sync INTEGER, data BLOB)")

    # Insert sample data in each table
    cursor.execute("INSERT INTO genp (acct, svce, agrp, data) VALUES (?, ?, ?, ?)",
                   (b'\x00\x01', b'\x02\x03', 'com.apple.mail', b'\x04\x05'))
    cursor.execute("INSERT INTO inet (srvr, agrp, data) VALUES (?, ?, ?)",
                   ('imap.gmail.com', 'com.apple.mail', b'\x06\x07'))
    cursor.execute("INSERT INTO cert (labl, data) VALUES (?, ?)",
                   ('Root CA', b'\x08\x09'))
    cursor.execute("INSERT INTO keys (labl, data) VALUES (?, ?)",
                   ('Private Key', b'\x0a\x0b'))

    conn.commit()
    conn.close()

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(keychain_db, "private/var/Keychains/keychain-2.db")

    core_api.set_zip_file(zip_path)

    # Parse keychain
    result = core_api.parse_ios_keychain("private/var/Keychains/keychain-2.db")

    # Verify all entry types found
    assert len(result['generic_passwords']) == 1
    assert len(result['internet_passwords']) == 1
    assert len(result['certificates']) == 1
    assert len(result['keys']) == 1
    assert result['summary']['total_entries'] == 4


def test_android_keystore_full_workflow(core_api, temp_dir):
    """Test complete Android keystore extraction workflow."""
    zip_path = temp_dir / "android_extraction.zip"

    # Create locksettings database
    locksettings_db = temp_dir / "locksettings.db"
    conn = sqlite3.connect(str(locksettings_db))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE locksettings (name TEXT, user INTEGER, value TEXT)")
    cursor.execute("INSERT INTO locksettings VALUES (?, ?, ?)",
                   ('lockscreen.password_type', 0, '196608'))
    conn.commit()
    conn.close()

    # Create keystore files
    keystore_dir = temp_dir / "keystore"
    keystore_dir.mkdir()
    (keystore_dir / ".masterkey").write_bytes(b'\x00\x01')

    system_dir = temp_dir / "system"
    system_dir.mkdir()
    (system_dir / "gatekeeper.password.key").write_bytes(b'\x02\x03')

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(locksettings_db, "data/system/locksettings.db")
        zf.write(keystore_dir / ".masterkey", "data/misc/keystore/.masterkey")
        zf.write(system_dir / "gatekeeper.password.key", "data/system/gatekeeper.password.key")

    core_api.set_zip_file(zip_path)

    # Parse locksettings
    lock_result = core_api.parse_android_locksettings("data/system/locksettings.db")
    assert lock_result['summary']['lock_type'] == 'PIN'

    # Identify keystore files
    keystore_result = core_api.identify_android_keystore_files()
    assert keystore_result['summary']['total_keystore_files'] >= 1
    assert keystore_result['summary']['has_gatekeeper'] is True
