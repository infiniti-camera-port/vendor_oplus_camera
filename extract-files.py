#!/usr/bin/env -S PYTHONPATH=../../../tools/extract-utils python3
#
# SPDX-FileCopyrightText: 2016 The CyanogenMod Project
# SPDX-FileCopyrightText: 2017-2024 The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#

from extract_utils.fixups_lib import (
    lib_fixups,
    lib_fixups_user_type,
)
from extract_utils.fixups_blob import (
    apktool_path,
    blob_fixup,
    blob_fixups_user_type,
    java_path,
)
from extract_utils.main import (
    ExtractUtils,
    ExtractUtilsModule,
)
from extract_utils.utils import run_cmd
from pathlib import Path
import glob
import re

from apk_fixups_op15 import (
    blob_fixup_add_oplus_camera_stubs,
    blob_fixup_apktool_unpack_full,
    blob_fixup_cryptoeng_init_rc,
    blob_fixup_cryptoeng_manifest,
    blob_fixup_cryptoeng_permissions_xml,
    blob_fixup_fileencryption_biometric_enrollment,
    blob_fixup_fileencryption_permissions,
    blob_fixup_filemanager_cut_same_disk,
    blob_fixup_filemanager_select_dir_fallback,
    blob_fixup_filemanager_skip_osense_scene,
    blob_fixup_phonemanager_permission_controller,
    blob_fixup_phonemanager_permissions,
    blob_fixup_phonemanager_settings_category,
    blob_fixup_ums_permissions,
)
from apk_permissions_op15 import blob_fixup_securitypermission_safe_permissions


def lib_fixup_system_ext_suffix(lib: str, partition: str, *args, **kwargs):
    """
    Mirrors lib_to_package_fixup_system_ext_variants from the old setup-makefiles.sh.
    These libs exist as system_ext variants and need a _system_ext suffix
    when pulled from that partition.
    """
    if partition != 'system_ext':
        return None

    system_ext_libs = {
        'libSuperTextWrapper',
        'libXDocProcessSDK',
        'libYTCommon',
        'libmpbase',
        'libextendfile',
    }

    return f'{lib}_system_ext' if lib in system_ext_libs else None


def _replace_smali_method(data: str, signature: str, body: str) -> str:
    # Replace a smali method body by its signature, independent of the (R8-obfuscated,
    # build-drifting) class path. The signature is the stable anchor.
    return re.sub(
        rf'(?ms)^\.method {re.escape(signature)}\n.*?^\.end method',
        f'.method {signature}\n{body}.end method',
        data,
    )


def blob_fixup_opluscamera_unpack(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    if tmp_dir is None:
        return
    run_cmd([java_path, '-Xmx8g', '-jar', apktool_path, 'd', file_path, '-o', tmp_dir, '-f'])


def blob_fixup_opluscamera_font(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    # OEM camera font-NPE neutralizer, re-anchored for infiniti: the
    # TypeFaceUtil static a(Context)->Typeface reads OplusBaseConfiguration.
    # mOplusExtraConfiguration.mFontVariationSettings; with the OEM font framework absent that
    # path crashes -> camera force-finishes on open. Return Typeface.DEFAULT to skip it.
    # Anchored on the "TypeFaceUtil" log tag + the method signature (class path drifts
    # between builds), so it stays correct across rebuilds.
    if tmp_dir is None:
        return
    signature = 'public static a(Landroid/content/Context;)Landroid/graphics/Typeface;'
    body = (
        '    .locals 1\n'
        '\n'
        '    sget-object v0, Landroid/graphics/Typeface;->DEFAULT:Landroid/graphics/Typeface;\n'
        '\n'
        '    return-object v0\n'
    )
    for smali in glob.glob(str(Path(tmp_dir) / 'smali*/**/*.smali'), recursive=True):
        try:
            data = open(smali, encoding='utf-8', errors='ignore').read()
        except OSError:
            continue
        if '"TypeFaceUtil"' in data and f'.method {signature}' in data:
            fixed = _replace_smali_method(data, signature, body)
            if fixed != data:
                open(smali, 'w', encoding='utf-8').write(fixed)
            return


def blob_fixup_opluscamera_strip_oem_perms(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    # Strip the android:permission="<oem>" gate attribute from
    # component declarations (oplus/oppo/heytap perms are undefined on LineageOS, so a gated
    # activity/service/receiver/provider fails to register -> crash-on-open). Components are
    # kept; only the gate attribute is removed. Anchored on the perm-value namespace.
    if tmp_dir is None:
        return
    manifest = Path(tmp_dir) / 'AndroidManifest.xml'
    if not manifest.exists():
        return
    data = manifest.read_text(encoding='utf-8')
    fixed = re.sub(
        r'\s+android:permission="(?:oplus|oppo|com\.oplus|com\.oppo|com\.heytap)[^"]*"',
        '',
        data,
    )
    if fixed != data:
        manifest.write_text(fixed, encoding='utf-8')


def blob_fixup_sdk_facebeauty(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    # Re-point the guarded ProductJni probe from /product/lib64 to /system_ext/lib64.
    # On LineageOS the lib ships at system_ext (my_product->system_ext remap), so the
    # /product probe fails -> unguarded fallback -> zero FaceBeautyParams -> SIGSEGV.
    # Anchored on the globally unique lib-path string in OplusFaceBeautyPreview;
    # immune to R8/obfuscated class-path drift — no line-context dependency.
    if tmp_dir is None:
        return
    OLD = '/product/lib64/libApsFaceBeautyPreviewProductJni.so'
    NEW = '/system_ext/lib64/libApsFaceBeautyPreviewProductJni.so'
    for smali in glob.glob(str(Path(tmp_dir) / 'smali*/**/*.smali'), recursive=True):
        try:
            data = open(smali, encoding='utf-8', errors='ignore').read()
        except OSError:
            continue
        if OLD in data:
            open(smali, 'w', encoding='utf-8').write(data.replace(OLD, NEW))
            return


def blob_fixup_oppogallery_unpack(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    # Gallery manifest-only fix: skip smali decode/reassembly (-s). Only the
    # AndroidManifest is edited (strip undefined OEM permission gates), so the
    # original classes*.dex are kept verbatim. This sidesteps the version-specific
    # smali rejects that forced the whole OppoGallery2 apktool patch to be disabled
    # manifest re-encode succeeds where smali reassembly
    # of the obfuscated app did not. The 348 MB apk also makes a full smali decode
    # prohibitively heavy.
    if tmp_dir is None:
        return
    run_cmd([java_path, '-Xmx8g', '-jar', apktool_path, 'd', '-s', file_path, '-o', tmp_dir, '-f'])


lib_fixups: lib_fixups_user_type = {
    # **lib_fixups already includes the clang RT ubsan and proto 3.9.1
    # fixups that were previously handled by the bash helper functions
    # lib_to_package_fixup_clang_rt_ubsan_standalone and
    # lib_to_package_fixup_proto_3_9_1 — no need to add them explicitly.
    **lib_fixups,
    (
        'libSuperTextWrapper',
        'libXDocProcessSDK',
        'libYTCommon',
        'libmpbase',
        'libextendfile',
    ): lib_fixup_system_ext_suffix,
}

blob_fixups = {
    'system_ext/framework/com.oplus.camera.unit.sdk.jar': blob_fixup()
        .apktool_unpack('patches-sdk')
        .patch_dir('patches-sdk')
        .call(blob_fixup_sdk_facebeauty)
        .apktool_pack()
        .stripzip(),
    # OplusCamera.apk crash-on-open fixes (re-authored to be
    # signature-anchored, verified against the apk bytecode): font-NPE neuter +
    # strip undefined OEM permission gates. apktool unpack -> edit smali/manifest -> repack.
    'system_ext/priv-app/OplusCamera/OplusCamera.apk': blob_fixup()
        .call(blob_fixup_opluscamera_unpack)
        .call(blob_fixup_opluscamera_font)
        .call(blob_fixup_opluscamera_strip_oem_perms)
        .apktool_pack()
        .stripzip(),
    # OppoGallery2.apk: strip the undefined OEM permission gates (oppo/oplus/heytap)
    # from its component declarations — same crash-class as the camera. The camera binds
    # the gallery's predecode service (OplusPreTileDecodeService), which gated on the
    # orphan oppo.permission.OPPO_COMPONENT_SAFE -> "Not allowed to bind to service"
    # SecurityException -> camera dies on open. This is the manifest half of the disabled
    # patches-gallery/0001 ("Get rid of oplus permissions"), re-applied via the same
    # version-independent regex strip used for the camera. Manifest-only (-s unpack), so
    # no smali reassembly (the reason #6 disabled the gallery patch set).
    'system_ext/priv-app/OppoGallery2/OppoGallery2.apk': blob_fixup()
        .call(blob_fixup_oppogallery_unpack)
        .call(blob_fixup_opluscamera_strip_oem_perms)
        .apktool_pack()
        .stripzip(),
    'system_ext/app/FileManager/FileManager.apk': blob_fixup()
        .call(blob_fixup_apktool_unpack_full)
        .call(blob_fixup_add_oplus_camera_stubs)
        .call(blob_fixup_filemanager_select_dir_fallback)
        .call(blob_fixup_filemanager_cut_same_disk)
        .call(blob_fixup_filemanager_skip_osense_scene)
        .apktool_pack()
        .stripzip(),
    'system_ext/priv-app/UMS/UMS.apk': blob_fixup()
        .call(blob_fixup_apktool_unpack_full)
        .call(blob_fixup_add_oplus_camera_stubs)
        .call(blob_fixup_ums_permissions)
        .apktool_pack()
        .stripzip(),
    'system_ext/priv-app/FileEncryption/FileEncryption.apk': blob_fixup()
        .call(blob_fixup_apktool_unpack_full)
        .call(blob_fixup_add_oplus_camera_stubs)
        .call(blob_fixup_fileencryption_permissions)
        .call(blob_fixup_fileencryption_biometric_enrollment)
        .apktool_pack()
        .stripzip(),
    'system_ext/app/SecurityPermission/SecurityPermission.apk': blob_fixup()
        .call(blob_fixup_apktool_unpack_full)
        .call(blob_fixup_securitypermission_safe_permissions)
        .apktool_pack()
        .stripzip(),
    'system_ext/priv-app/PhoneManager/PhoneManager.apk': blob_fixup()
        .call(blob_fixup_apktool_unpack_full)
        .call(blob_fixup_add_oplus_camera_stubs)
        .call(blob_fixup_phonemanager_permissions)
        .call(blob_fixup_phonemanager_settings_category)
        .call(blob_fixup_phonemanager_permission_controller)
        .apktool_pack()
        .stripzip(),
    'system_ext/etc/permissions/vendor-oplus-hardware-cryptoeng.xml': blob_fixup()
        .call(blob_fixup_cryptoeng_permissions_xml),
    'odm/etc/permissions/vendor-oplus-hardware-cryptoeng.xml': blob_fixup()
        .call(blob_fixup_cryptoeng_permissions_xml),
    'odm/etc/init/vendor.oplus.hardware.cryptoeng@1.0-service_FDE.rc': blob_fixup()
        .call(blob_fixup_cryptoeng_init_rc),
    'odm/etc/vintf/manifest/manifest_oplus_cryptoeng.xml': blob_fixup()
        .call(blob_fixup_cryptoeng_manifest),
}  # fmt: skip

namespace_imports = [
    'vendor/oplus/camera/camera',
    'vendor/oneplus/infiniti',
    'vendor/oneplus/sm8850-common',
    'hardware/oplus',
]

module = ExtractUtilsModule(
    'camera',
    'oplus/camera',
    device_rel_path='vendor/oplus/camera',
    blob_fixups=blob_fixups,
    lib_fixups=lib_fixups,
    namespace_imports=namespace_imports,
)

if __name__ == '__main__':
    utils = ExtractUtils.device(module)
    utils.run()
