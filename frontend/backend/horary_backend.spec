# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\sabaa\\Downloads\\codexhorary\\backend\\app.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\sabaa\\Downloads\\codexhorary\\backend\\horary_constants.yaml', '.'), ('C:\\Users\\sabaa\\Downloads\\codexhorary\\backend\\event_keywords_catalog.md', '.'), ('C:\\Users\\sabaa\\Downloads\\codexhorary\\backend\\synastry_rule_catalog.json', '.'), ('C:\\Users\\sabaa\\Downloads\\codexhorary\\backend\\horary_config.py', '.'), ('C:\\Users\\sabaa\\Downloads\\codexhorary\\backend\\production_server.py', '.'), ('C:\\Users\\sabaa\\Downloads\\codexhorary\\backend\\knowledge\\astrocartography', 'knowledge/astrocartography'), ('C:\\Users\\sabaa\\Downloads\\codexhorary\\backend\\knowledge\\mundane', 'knowledge/mundane'), ('C:\\Users\\sabaa\\Downloads\\codexhorary\\backend\\knowledge\\weather', 'knowledge/weather'), ('C:\\Users\\sabaa\\Downloads\\codexhorary\\backend\\benchmarks', 'benchmarks'), ('C:\\Users\\sabaa\\Downloads\\codexhorary\\backend\\rules_lilly_general_v1.yaml', '.'), ('C:\\Users\\sabaa\\Downloads\\codexhorary\\backend\\forensic\\knowledge', 'forensic/knowledge'), ('C:\\Users\\sabaa\\Downloads\\codexhorary\\backend\\traits\\catalog', 'traits/catalog'), ('C:\\Users\\sabaa\\Downloads\\codexhorary\\backend\\traits\\traits.json', 'traits'), ('C:\\Users\\sabaa\\Downloads\\codexhorary\\backend\\traits\\knowledge', 'traits/knowledge'), ('C:\\Users\\sabaa\\Downloads\\codexhorary\\backend\\Phsychology traits', 'Phsychology traits'), ('C:\\Users\\sabaa\\Downloads\\codexhorary\\backend\\ephemeris\\sweph', 'ephemeris/sweph'), ('C:\\Users\\sabaa\\Downloads\\codexhorary\\backend\\build\\build_metadata.json', '.')],
    hiddenimports=['swisseph', 'timezonefinder', 'pytz', 'flask', 'flask_cors', 'nacl', 'nacl.bindings', 'nacl.signing', 'nacl.exceptions', 'astro_clock_api', 'birth_certification', 'runtime_import_paths', 'licensing', 'mundane_assets', 'mundane_benchmark_profiles', 'mundane_chart_rules', 'mundane_domain_rules', 'mundane_models', 'mundane_resource_paths', 'mundane_scan_grid', 'mundane_scan_models', 'mundane_scan_service', 'mundane_service', 'mundane_trigger_rules', 'weather_assets', 'weather_benchmark_profiles', 'weather_chart_rules', 'weather_domain_rules', 'weather_models', 'weather_resource_paths', 'weather_scan_models', 'weather_scan_service', 'weather_service'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='horary_backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='horary_backend',
)
