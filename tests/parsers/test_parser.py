from unittest.mock import MagicMock, patch

from nomad.datamodel.datamodel import EntryArchive

from nomad_measurements_dls.parsers.parser import DLSParser
from nomad_measurements_dls.schema_packages.schema_package import (
    ELNMalvernZmes,
    RawFileDLSData,
)


def test_is_mainfile():
    """Test that the parser correctly identifies .zmes files and rejects others."""
    parser = DLSParser()
    assert (
        parser.is_mainfile('sample.zmes', 'application/octet-stream', b'dummy_data', '')
        is True
    )
    assert (
        parser.is_mainfile('SAMPLE.ZMES', 'application/octet-stream', b'dummy_data', '')
        is True
    )
    assert (
        parser.is_mainfile('sample.zmes', 'application/octet-stream', b'', '') is False
    )
    assert parser.is_mainfile('sample.txt', 'text/plain', b'dummy', '') is False


@patch('nomad_measurements_dls.parsers.parser.create_archive')
def test_parse(mock_create_archive):
    """Test that the parser instantiates the correct schema and links it."""
    parser = DLSParser()
    archive = EntryArchive()
    logger = MagicMock()

    # FIX: Tell the mock to return a valid NOMAD section so the strictly-typed metainfo doesn't crash
    mock_create_archive.return_value = ELNMalvernZmes()

    parser.parse('my_folder/my_measurement.zmes', archive, logger=logger)

    mock_create_archive.assert_called_once()
    args, _ = mock_create_archive.call_args
    eln_entry = args[0]

    assert eln_entry.m_def.name == 'ELNMalvernZmes'
    assert eln_entry.data_file == 'my_measurement.zmes'
    assert isinstance(archive.data, RawFileDLSData)
