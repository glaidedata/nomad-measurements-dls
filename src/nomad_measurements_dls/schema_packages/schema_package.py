from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from ientrance_instruments.schema_packages.schema_package import IEntranceInstrument
from nomad.datamodel.data import JSON, ArchiveSection, EntryData
from nomad.datamodel.metainfo.annotations import ELNComponentEnum
from nomad.datamodel.metainfo.basesections import Measurement, MeasurementResult
from nomad.metainfo import Quantity, SchemaPackage, Section, SubSection

from readers_ientrance.zmes_reader import read_zmes

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = SchemaPackage()


# ==========================================
# 1. SHARED DLS SETUP SECTIONS
# ==========================================
class DLSInstrumentSetup(ArchiveSection):
    """Details about the DLS instrument setup and optics."""

    scattering_angle = Quantity(
        type=np.float64,
        unit='deg',
        description='The angle at which scattered light is collected.'
    )
    wavelength = Quantity(
        type=np.float64,
        unit='nm',
        description='Wavelength of the excitation laser.'
    )


# ==========================================
# 2. SHARED DLS RESULTS
# ==========================================
class DLSData(ArchiveSection):
    """A section to hold the arrays, plots, and metadata for a single DLS/Zeta run."""

    m_def = Section(
        a_plot=[
            dict(
                label='Correlation Function',
                x='correlation_lag_times',
                y='correlation_data',
                lines=[dict(mode='lines', line=dict(color='blue'))],
            ),
            dict(
                label='Zeta Potential Distribution',
                x='zeta_potentials_x',
                y='zeta_potential_distribution',
                lines=[dict(mode='lines', line=dict(color='green'))],
            ),
            dict(
                label='Intensity Distribution',
                x='size_classes',
                y='intensity_distribution',
                lines=[dict(mode='lines', line=dict(color='red'))],
            )
        ]
    )

    record_name = Quantity(
        type=str,
        description='The sample name or identifier for this specific measurement run.',
    )

    measurement_type = Quantity(
        type=str,
        description='Type of measurement (e.g., Size, Zeta Potential).',
    )

    temperature = Quantity(
        type=np.float64,
        unit='°C',
        description='Temperature of the sample during this specific measurement.',
    )

    record_metadata = Quantity(
        type=JSON,
        description='A complete dictionary dump of unparsed metadata for this specific run.',
    )

    # --- Core Arrays ---
    correlation_lag_times = Quantity(
        type=np.float64, shape=['*'], unit='s', description='Lag times for the correlation function.'
    )
    correlation_data = Quantity(
        type=np.float64, shape=['*'], description='The correlation coefficients.'
    )

    size_classes = Quantity(
        type=np.float64, shape=['*'], unit='nm', description='Particle diameter bins for size distributions.'
    )
    intensity_distribution = Quantity(
        type=np.float64, shape=['*'], description='Particle size intensity distribution.'
    )
    volume_distribution = Quantity(
        type=np.float64, shape=['*'], description='Particle size volume distribution.'
    )
    number_distribution = Quantity(
        type=np.float64, shape=['*'], description='Particle size number distribution.'
    )

    zeta_potentials_x = Quantity(
        type=np.float64, shape=['*'], unit='mV', description='Zeta potential bins.'
    )
    zeta_potential_distribution = Quantity(
        type=np.float64, shape=['*'], description='Zeta potential distribution intensities.'
    )


class DLSResult(MeasurementResult):
    """Holds the data subsection for a single run in the batch."""
    data = SubSection(section_def=DLSData)


# ==========================================
# 3. BASE DLS ENTRY
# ==========================================
class BaseDynamicLightScattering(Measurement):
    """Base class containing shared attributes for all DLS entries."""

    #_instrument_schema_preload = Quantity(type=IEntranceInstrument)

    data_file = Quantity(
        type=str,
        a_eln=dict(component=ELNComponentEnum.FileEditQuantity),
        a_browser=dict(adaptor='RawFileAdaptor'),
        description='The raw DLS measurement file.',
    )

    instrument_model = Quantity(
        type=str,
        description='The model of the DLS instrument.',
        a_eln=dict(component=ELNComponentEnum.StringEditQuantity),
    )

    software_version = Quantity(
        type=str,
        description='Software used to record the measurements.',
        a_eln=dict(component=ELNComponentEnum.StringEditQuantity),
    )

    # Global metadata for the entire file (if any)
    raw_metadata = Quantity(
        type=JSON,
        description='Global file-level metadata.',
    )

    instrument_setup = SubSection(section_def=DLSInstrumentSetup)

    # Repeats=True allows us to store the 102 runs inside the single file
    results = SubSection(section_def=DLSResult, repeats=True)


# ==========================================
# 4. MALVERN ZMES SPECIFIC SCHEMA
# ==========================================
class ELNMalvernZmes(BaseDynamicLightScattering, EntryData):
    m_def = Section(
        label='Malvern Zetasizer (ZMES)',
        a_eln=dict(lane_width='600px'),
        a_template=dict(measurement_identifiers=dict()),
    )

    def _init_subsections(self):
        """Helper method to initialize root schema sections."""
        if not self.instrument_setup:
            self.instrument_setup = DLSInstrumentSetup()

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        if not self.data_file:
            super().normalize(archive, logger)
            return

        try:
            # 1. Get the absolute OS path
            file_path = archive.m_context.upload_files.raw_file_object(
                self.data_file
            ).os_path

            # 2. Extract data using the custom zmes_reader
            zmes_data = read_zmes(file_path)

            if "extraction_error" in zmes_data.metadata:
                logger.warning(f"ZMES Reader Warning: {zmes_data.metadata['extraction_error']}")

            self._init_subsections()

            # 3. Map Top-Level Metadata (Extracting from the first record as a representative)
            if zmes_data.records:
                first_record = list(zmes_data.records.values())[0]
                self.instrument_model = "Malvern Zetasizer"
                self.software_version = str(first_record.metadata.get("Software Version", "Unknown"))

                angle = first_record.metadata.get("Scattering Collection Angle (°)")
                if angle is not None:
                    self.instrument_setup.scattering_angle = float(angle)

            self.raw_metadata = zmes_data.metadata
            self.results = [] # Clear existing results to prevent duplication on re-saving

            # 4. Iterate through the batch and map each measurement run
            for record_name, record in zmes_data.records.items():
                result_section = DLSResult()
                data_section = DLSData()

                data_section.record_name = record_name

                # Determine measurement type based on which arrays are present
                if record.correlation_data is not None:
                    data_section.measurement_type = "Size (DLS)"
                elif record.zeta_potential_distribution is not None:
                    data_section.measurement_type = "Zeta Potential"
                else:
                    data_section.measurement_type = "Other"

                # Extract specific useful metadata
                temp = record.metadata.get("Temperature (°C)") or record.metadata.get("Temperature")
                if temp is not None:
                    data_section.temperature = float(temp)

                data_section.record_metadata = record.metadata

                # Map Core Arrays
                data_section.correlation_lag_times = record.correlation_lag_times
                data_section.correlation_data = record.correlation_data
                data_section.size_classes = record.size_classes
                data_section.intensity_distribution = record.intensity_distribution
                data_section.volume_distribution = record.volume_distribution
                data_section.number_distribution = record.number_distribution
                data_section.zeta_potentials_x = record.zeta_potentials_x
                data_section.zeta_potential_distribution = record.zeta_potential_distribution

                result_section.data = data_section
                self.results.append(result_section)

        except Exception as e:
            if logger:
                logger.error(f'Error parsing Malvern ZMES file: {e}')
            raise e

        super().normalize(archive, logger)


class RawFileDLSData(EntryData):
    """Placeholder for the raw ZMES file to point to the generated ELN."""

    m_def = Section(label='Raw DLS Data File')

    measurement = Quantity(
        type=ELNMalvernZmes,
        a_eln=dict(component=ELNComponentEnum.ReferenceEditQuantity),
        description='The editable ELN archive generated from this raw file.',
    )


m_package.__init_metainfo__()