from pathlib import Path

from extract_utils.fixups_blob import apktool_path, java_path
from extract_utils.utils import run_cmd


def blob_fixup_apktool_unpack_full(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    if tmp_dir is None:
        return
    run_cmd([java_path, '-Xmx8g', '-jar', apktool_path, 'd', file_path, '-o', tmp_dir, '-f'])


def blob_fixup_cryptoeng_permissions_xml(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    path = Path(file_path)
    data = path.read_text(encoding='utf-8')
    path.write_text(data.replace('\n</permissions>\n\n<permissions>\n', '\n'), encoding='utf-8')


def blob_fixup_cryptoeng_manifest(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    path = Path(file_path)
    data = path.read_text(encoding='utf-8')
    data = data.replace('<!--\n    <hal format="hidl">', '    <hal format="hidl">')
    data = data.replace('    </hal>\n-->\n    <hal format="aidl">', '    </hal>\n    <hal format="aidl">')
    path.write_text(data, encoding='utf-8')
