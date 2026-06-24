from nomad.config.models.plugins import ParserEntryPoint


class DLSParserEntryPoint(ParserEntryPoint):
    def load(self):
        from nomad_measurements_dls.parsers.parser import DLSParser

        return DLSParser(**self.dict())


parser_entry_point = DLSParserEntryPoint(
    name='DLSParser',
    description='Parser for Dynamic Light Scattering (DLS) measurement files.',
    mainfile_name_re=r'.*\.zmes$',
)