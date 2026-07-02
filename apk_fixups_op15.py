from __future__ import annotations

from pathlib import Path
import re

from extract_utils.fixups_blob import apktool_path, java_path
from extract_utils.utils import run_cmd


def _manifest(tmp_dir: str) -> Path:
    return Path(tmp_dir) / 'AndroidManifest.xml'


def _replace_smali_method(data: str, signature: str, body: str) -> str:
    return re.sub(
        rf'(?ms)^\.method {re.escape(signature)}\n.*?^\.end method',
        f'.method {signature}\n{body}.end method',
        data,
    )


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


def blob_fixup_apktool_unpack_full(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    if tmp_dir is None:
        return
    run_cmd([java_path, '-Xmx8g', '-jar', apktool_path, 'd', file_path, '-o', tmp_dir, '-f'])


def blob_fixup_add_oplus_camera_stubs(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    if tmp_dir is None:
        return
    manifest = _manifest(tmp_dir)
    data = manifest.read_text(encoding='utf-8') if manifest.exists() else ''
    if not data or 'oplus.camera.stubs' in data:
        return
    entry = '        <uses-library android:name="oplus.camera.stubs" android:required="false"/>\n'
    sdk_entry = '        <uses-library android:name="com.oplus.camera.unit.sdk" android:required="false"/>\n'
    if sdk_entry in data:
        fixed = data.replace(sdk_entry, entry + sdk_entry, 1)
    else:
        fixed = data.replace('</application>', entry + '    </application>', 1)
    if fixed != data:
        manifest.write_text(fixed, encoding='utf-8')


def blob_fixup_fileencryption_permissions(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    if tmp_dir is not None:
        _add_permissions(
            tmp_dir,
            (
                'android.permission.USE_BIOMETRIC',
                'android.permission.USE_FINGERPRINT',
                'android.permission.WRITE_SECURE_SETTINGS',
            ),
        )


def blob_fixup_fileencryption_biometric_enrollment(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    if tmp_dir is None:
        return
    smali = Path(tmp_dir) / 'smali/c9/a.smali'
    data = smali.read_text(encoding='utf-8') if smali.exists() else ''
    if not data:
        raise ValueError('FileEncryption biometric helper not found')

    face_body = (
        '    .locals 2\n\n'
        '    :try_start_0\n'
        '    const-string v0, "face"\n\n'
        '    invoke-virtual {p0, v0}, Landroid/content/Context;'
        '->getSystemService(Ljava/lang/String;)Ljava/lang/Object;\n\n'
        '    move-result-object p0\n\n'
        '    instance-of v0, p0, Landroid/hardware/face/FaceManager;\n\n'
        '    if-eqz v0, :cond_0\n\n'
        '    check-cast p0, Landroid/hardware/face/FaceManager;\n\n'
        '    invoke-virtual {p0}, Landroid/hardware/face/FaceManager;->hasEnrolledTemplates()Z\n\n'
        '    move-result p0\n\n'
        '    return p0\n'
        '    :try_end_0\n'
        '    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_0\n\n'
        '    :catch_0\n'
        '    move-exception p0\n\n'
        '    :cond_0\n'
        '    const/4 p0, 0x0\n\n'
        '    return p0\n'
    )
    fingerprint_body = (
        '    .locals 2\n\n'
        '    :try_start_0\n'
        '    const-string v0, "fingerprint"\n\n'
        '    invoke-virtual {p0, v0}, Landroid/content/Context;'
        '->getSystemService(Ljava/lang/String;)Ljava/lang/Object;\n\n'
        '    move-result-object p0\n\n'
        '    instance-of v0, p0, Landroid/hardware/fingerprint/FingerprintManager;\n\n'
        '    if-eqz v0, :cond_0\n\n'
        '    check-cast p0, Landroid/hardware/fingerprint/FingerprintManager;\n\n'
        '    invoke-virtual {p0}, Landroid/hardware/fingerprint/FingerprintManager;->isHardwareDetected()Z\n\n'
        '    move-result v0\n\n'
        '    if-eqz v0, :cond_0\n\n'
        '    invoke-virtual {p0}, Landroid/hardware/fingerprint/FingerprintManager;->hasEnrolledFingerprints()Z\n\n'
        '    move-result p0\n\n'
        '    return p0\n'
        '    :try_end_0\n'
        '    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_0\n\n'
        '    :catch_0\n'
        '    move-exception p0\n\n'
        '    :cond_0\n'
        '    const/4 p0, 0x0\n\n'
        '    return p0\n'
    )
    face_signature = 'public static final b(Landroid/content/Context;)Z'
    fingerprint_signature = 'public static final c(Landroid/content/Context;)Z'
    fixed, face_count = re.subn(
        rf'(?ms)^\.method {re.escape(face_signature)}\n.*?^\.end method',
        f'.method {face_signature}\n{face_body}.end method',
        data,
        count=1,
    )
    fixed, fingerprint_count = re.subn(
        rf'(?ms)^\.method {re.escape(fingerprint_signature)}\n.*?^\.end method',
        f'.method {fingerprint_signature}\n{fingerprint_body}.end method',
        fixed,
        count=1,
    )
    if face_count != 1 or fingerprint_count != 1:
        raise ValueError('FileEncryption biometric enrollment checks not patched exactly once')
    smali.write_text(fixed, encoding='utf-8')


def blob_fixup_phonemanager_permissions(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    if tmp_dir is not None:
        _add_permissions(tmp_dir, ('android.permission.WRITE_SECURE_SETTINGS',))


def blob_fixup_ums_permissions(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    if tmp_dir is not None:
        _add_permissions(tmp_dir, ('android.permission.SET_ACTIVITY_WATCHER',))


def blob_fixup_phonemanager_settings_category(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    if tmp_dir is None:
        return
    manifest = _manifest(tmp_dir)
    data = manifest.read_text(encoding='utf-8') if manifest.exists() else ''
    old = 'android:value="com.oplus.settings.category.ia.phone_manager"'
    new = 'android:value="com.android.settings.category.ia.more_security_privacy_settings"'
    fixed = data.replace(old, new, 1)
    if fixed != data:
        manifest.write_text(fixed, encoding='utf-8')
    elif new not in data:
        raise ValueError('PhoneManager Settings category metadata not found')


def blob_fixup_phonemanager_permission_controller(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    if tmp_dir is None:
        return
    replaced = False
    for path in Path(tmp_dir).glob('**/*'):
        if not path.is_file() or path.suffix not in {'.smali', '.xml'}:
            continue
        data = path.read_text(encoding='utf-8', errors='ignore')
        if 'com.google.android.permissioncontroller' not in data:
            continue
        fixed = data.replace(
            'com.google.android.permissioncontroller',
            'com.android.permissioncontroller',
        )
        path.write_text(fixed, encoding='utf-8')
        replaced = True
    if not replaced:
        raise ValueError('PhoneManager permission controller package string not found')


def blob_fixup_filemanager_cut_same_disk(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    if tmp_dir is None:
        return
    smali = Path(tmp_dir) / 'smali/com/filemanager/fileoperate/cut/FileActionCut.smali'
    data = smali.read_text(encoding='utf-8')
    if 'iget-boolean v2, p0, Lcom/filemanager/fileoperate/cut/FileActionCut;->V:Z' in data:
        return
    pattern = (
        r'(?m)^(?P<label>    :cond_\w+\n)'
        r'(?P<call>    invoke-virtual \{p0\}, Lcom/filemanager/fileoperate/cut/FileActionCut;->K0\(\)Z\n'
        r'\n    move-result v2\n\n    if-eqz v2, :(?P<after>cond_\w+)\n)'
    )
    data, count = re.subn(
        pattern,
        lambda match: (
            match.group('label')
            + '    iget-boolean v2, p0, Lcom/filemanager/fileoperate/cut/FileActionCut;->V:Z\n'
            + f'    if-nez v2, :{match.group("after")}\n'
            + match.group('call')
        ),
        data,
        count=1,
    )
    if count != 1:
        raise ValueError('FileManager FileActionCut K0() block not found exactly once')
    smali.write_text(data, encoding='utf-8')


def blob_fixup_filemanager_select_dir_fallback(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    if tmp_dir is None:
        return
    smali = Path(tmp_dir) / 'smali_classes3/com/oplus/selectdir/SelectDirPathPanelFragment.smali'
    data = smali.read_text(encoding='utf-8')
    log_anchor = '    const-string v4, "selectButton click -> select path:"\n'
    button_anchor = (
        '    iget-object p1, p0, Lcom/oplus/selectdir/SelectDirPathPanelFragment;'
        '->mSelectButton:Lcom/coui/appcompat/button/COUIButton;\n'
    )
    new = (
        '    iget-object v0, p0, Lcom/oplus/selectdir/SelectDirPathPanelFragment;'
        '->mPathBar:Lcom/filemanager/common/view/BrowserPathBar;\n'
        '    if-eqz v0, :cond_pathbar_skip\n'
        '    invoke-virtual {v0}, Lcom/filemanager/common/view/BrowserPathBar;->getCurrentPath()Ljava/lang/String;\n'
        '    move-result-object v0\n'
        '    if-eqz v0, :cond_pathbar_skip\n'
        '    iget-object p1, v1, Lkotlin/jvm/internal/Ref$ObjectRef;->element:Ljava/lang/Object;\n'
        '    check-cast p1, Ljava/util/List;\n'
        '    if-eqz p1, :cond_pathbar_set\n'
        '    invoke-interface {p1}, Ljava/util/List;->isEmpty()Z\n'
        '    move-result p1\n'
        '    if-eqz p1, :cond_pathbar_skip\n'
        '    :cond_pathbar_set\n'
        '    invoke-static {v0}, Lkotlin/collections/p;->e(Ljava/lang/Object;)Ljava/util/List;\n'
        '    move-result-object v0\n'
        '    iput-object v0, v1, Lkotlin/jvm/internal/Ref$ObjectRef;->element:Ljava/lang/Object;\n'
        '    :cond_pathbar_skip\n'
    )
    log_idx = data.find(log_anchor)
    button_idx = data.find(button_anchor, log_idx)
    if log_idx == -1 or button_idx == -1:
        raise ValueError('FileManager SelectDirPathPanelFragment path fallback anchors not found')
    if ':cond_pathbar_skip' not in data[log_idx:button_idx]:
        data = data[:button_idx] + new + data[button_idx:]
    smali.write_text(data, encoding='utf-8')


def blob_fixup_filemanager_skip_osense_scene(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    if tmp_dir is None:
        return
    smali = Path(tmp_dir) / 'smali/com/filemanager/fileoperate/copy/FileActionBaseCopyCut.smali'
    data = smali.read_text(encoding='utf-8')
    fixed = _replace_smali_method(data, 'public final c0()V', '    .locals 0\n\n    return-void\n')
    if fixed == data:
        raise ValueError('FileManager FileActionBaseCopyCut.c0() method not found')
    smali.write_text(fixed, encoding='utf-8')


def blob_fixup_cryptoeng_permissions_xml(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    path = Path(file_path)
    data = path.read_text(encoding='utf-8')
    path.write_text(data.replace('\n</permissions>\n\n<permissions>\n', '\n'), encoding='utf-8')


def blob_fixup_cryptoeng_init_rc(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    path = Path(file_path)
    data = path.read_text(encoding='utf-8')
    fixed = data.replace(
        '    mkdir /data/vendor_de/0/cryptoeng 0770 system system encryption=None\n',
        '    mkdir /data/vendor_de/0/cryptoeng 0770 system system encryption=None\n'
        '    restorecon_recursive /data/vendor_de/0/cryptoeng\n',
        1,
    )
    path.write_text(fixed, encoding='utf-8')


def blob_fixup_cryptoeng_manifest(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    path = Path(file_path)
    data = path.read_text(encoding='utf-8')
    data = data.replace('<!--\n    <hal format="hidl">', '    <hal format="hidl">')
    data = data.replace('    </hal>\n-->\n    <hal format="aidl">', '    </hal>\n    <hal format="aidl">')
    path.write_text(data, encoding='utf-8')
