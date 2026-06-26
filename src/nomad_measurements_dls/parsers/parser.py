from nomad.datamodel.context import ServerContext
from nomad.datamodel.datamodel import EntryArchive
from nomad.parsing.parser import MatchingParser
from nomad_measurements.utils import create_archive

from nomad_measurements_dls.schema_packages.schema_package import (
    ELNMalvernZmes,
    RawFileDLSData,
)


class DLSParser(MatchingParser):
    def is_mainfile(
        self,
        filename: str,
        mime: str,
        buffer: bytes,
        decoded_buffer: str,
        compression: str = None,
    ) -> bool:
        """Gatekeeper for DLS files."""

        filename_lower = filename.lower()

        # 1. Malvern ZMES Check (.zmes)
        if filename_lower.endswith('.zmes'):
            # ZMES files are binary SQLite databases, ensure the buffer isn't empty.
            if buffer:
                return True

        return False

    def parse(
        self,
        mainfile: str,
        archive: EntryArchive,
        logger=None,
        child_archives=None,
    ) -> None:
        logger = logger or archive.m_context.logger

        # Extract the filename, handling server context paths correctly
        data_file = mainfile.rsplit('/', maxsplit=1)[-1]
        if isinstance(archive.m_context, ServerContext):
            data_file = mainfile.split('/raw/', 1)[1]

        filename_lower = data_file.lower()

        # Route to the correct Schema based on the file extension
        if filename_lower.endswith('.zmes'):
            entry = ELNMalvernZmes()
        else:
            logger.error(f'Unsupported DLS file format: {data_file}')
            return

        # Assign the file name to the entry
        entry.data_file = data_file

        # Create the separate editable .archive.json file to preserve ELN edits
        archive_name = f'{"".join(data_file.split(".")[:-1])}.archive.json'
        eln_ref = create_archive(entry, archive, archive_name)

        # Link the raw .zmes file to the generated ELN to prevent crashes and duplication
        archive.data = RawFileDLSData(measurement=eln_ref)
