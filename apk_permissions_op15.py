from pathlib import Path


SAFE_PERMISSIONS = (
    'oplus.permission.OPLUS_COMPONENT_SAFE',
    'oppo.permission.OPPO_COMPONENT_SAFE',
    'com.oplus.permission.safe.AI_APP',
    'com.oplus.permission.safe.APP_MANAGER',
    'com.oplus.permission.safe.ASSISTANT',
    'com.oplus.permission.safe.AUTHENTICATE',
    'com.oplus.permission.safe.CAMERA',
    'com.oplus.permission.safe.CAR_LINK',
    'com.oplus.permission.safe.CONNECTIVITY',
    'com.oplus.permission.safe.IOT',
    'com.oplus.permission.safe.LOG',
    'com.oplus.permission.safe.MEDIA',
    'com.oplus.permission.safe.PHONE',
    'com.oplus.permission.safe.PICTURE',
    'com.oplus.permission.safe.POWER',
    'com.oplus.permission.safe.PRIVATE',
    'com.oplus.permission.safe.PROTECT',
    'com.oplus.permission.safe.READ_COMMON',
    'com.oplus.permission.safe.SAFE_MANAGER',
    'com.oplus.permission.safe.SAU',
    'com.oplus.permission.safe.SECURITY',
    'com.oplus.permission.safe.SETTINGS',
    'com.oplus.permission.safe.SETTINGS_SEARCH',
    'com.oplus.permission.safe.WINDOW',
    'com.oppo.permission.safe.AI_APP',
    'com.oppo.permission.safe.AUTHENTICATE',
    'com.oppo.permission.safe.CAMERA',
    'com.oppo.permission.safe.PRIVATE',
    'com.oppo.permission.safe.SAU',
    'com.oppo.permission.safe.SECURITY',
)


def blob_fixup_securitypermission_safe_permissions(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    if tmp_dir is None:
        return
    manifest = Path(tmp_dir) / 'AndroidManifest.xml'
    data = manifest.read_text(encoding='utf-8')
    block = ''.join(
        f'    <permission android:name="{permission}" android:protectionLevel="signature|privileged" />\n'
        for permission in SAFE_PERMISSIONS
        if f'<permission android:name="{permission}"' not in data
    )
    if block:
        manifest.write_text(data.replace('<application ', block + '\n    <application ', 1), encoding='utf-8')
