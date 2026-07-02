from __future__ import annotations

from pathlib import Path


def _manifest(tmp_dir: str) -> Path:
    return Path(tmp_dir) / 'AndroidManifest.xml'


def _add_permissions(tmp_dir: str, permissions: tuple[str, ...]) -> None:
    manifest = _manifest(tmp_dir)
    data = manifest.read_text(encoding='utf-8') if manifest.exists() else ''
    entries = ''.join(
        f'    <uses-permission android:name="{permission}"/>\n'
        for permission in permissions
        if permission not in data
    )
    if entries:
        manifest.write_text(data.replace('<application ', entries + '    <application ', 1), encoding='utf-8')


def blob_fixup_opluscamera_component_safe_permission(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    if tmp_dir is not None:
        _add_permissions(tmp_dir, ('oppo.permission.OPPO_COMPONENT_SAFE',))
