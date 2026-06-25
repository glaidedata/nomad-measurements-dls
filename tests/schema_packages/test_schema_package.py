import pytest
import numpy as np
from unittest.mock import patch, MagicMock

# FIX: Import EntryMetadata alongside EntryArchive
from nomad.datamodel.datamodel import EntryArchive, EntryMetadata
from nomad_measurements_dls.schema_packages.schema_package import (
    ELNMalvernZmes,
    DLSResult,
    DLSData,
    DLSInstrumentSetup
)

def test_schema_instantiation():
    """Test that the root schemas and subsections can be instantiated."""
    entry = ELNMalvernZmes()
    assert entry.m_def.name == 'ELNMalvernZmes'

    entry._init_subsections()
    assert isinstance(entry.instrument_setup, DLSInstrumentSetup)

    result = DLSResult()
    data = DLSData(record_name="Test Run", temperature=25.0)
    result.data = data

    entry.results = [result]
    assert len(entry.results) == 1
    assert entry.results[0].data.record_name == "Test Run"


@patch("nomad_measurements_dls.schema_packages.schema_package.read_zmes")
def test_eln_normalization(mock_read_zmes):
    """Test the normalize function by mocking the reader output and NOMAD context."""
    mock_data = MagicMock()
    mock_data.metadata = {"Global Parameter": "Test Value"}

    mock_record = MagicMock()
    mock_record.metadata = {
        "Software Version": "4.2.0",
        "Scattering Collection Angle (°)": 173.0,
        "Temperature (°C)": 25.0
    }

    mock_record.correlation_lag_times = np.array([1, 2, 3], dtype=np.float64)
    mock_record.correlation_data = np.array([0.9, 0.5, 0.1], dtype=np.float64)
    mock_record.size_classes = None
    mock_record.intensity_distribution = None
    mock_record.volume_distribution = None
    mock_record.number_distribution = None
    mock_record.zeta_potentials_x = None
    mock_record.zeta_potential_distribution = None

    mock_data.records = {"Sample A": mock_record}
    mock_read_zmes.return_value = mock_data

    entry = ELNMalvernZmes(data_file="mocked_file.zmes")
    archive = EntryArchive()

    # FIX: Provide a dummy metadata section so NOMAD's base classes don't crash
    archive.metadata = EntryMetadata(entry_name="mocked_file.zmes")

    archive.m_context = MagicMock()
    archive.m_context.upload_files.raw_file_object.return_value.os_path = "/fake/path/mocked_file.zmes"

    logger = MagicMock()
    entry.normalize(archive, logger)

    mock_read_zmes.assert_called_once_with("/fake/path/mocked_file.zmes")
    assert entry.instrument_model == "Malvern Zetasizer"
    assert entry.software_version == "4.2.0"

    assert entry.instrument_setup.scattering_angle.magnitude == 173.0
    assert entry.raw_metadata["Global Parameter"] == "Test Value"

    assert len(entry.results) == 1
    result_data = entry.results[0].data

    assert result_data.record_name == "Sample A"

    # FIX: Extract the .magnitude from the temperature Quantity
    assert result_data.temperature.magnitude == 25.0
    assert result_data.measurement_type == "Size (DLS)"


    assert np.array_equal(result_data.correlation_lag_times.magnitude, np.array([1, 2, 3], dtype=np.float64))
    assert np.array_equal(result_data.correlation_data, np.array([0.9, 0.5, 0.1], dtype=np.float64))
    assert result_data.zeta_potential_distribution is None