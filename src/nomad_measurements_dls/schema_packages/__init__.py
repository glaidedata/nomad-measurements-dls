from nomad.config.models.plugins import SchemaPackageEntryPoint


class DLSSchemaPackageEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_measurements_dls.schema_packages.schema_package import m_package

        return m_package


schema_package_entry_point = DLSSchemaPackageEntryPoint(
    name='DLSSchemaPackage',
    description='Schema package for Dynamic Light Scattering (DLS) and Zeta Potential measurements.',
)