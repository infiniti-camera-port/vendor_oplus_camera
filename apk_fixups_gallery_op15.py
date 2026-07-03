from __future__ import annotations

from pathlib import Path
import re


def blob_fixup_oppogallery_wallpaper_attach_intent(ctx, file, file_path, *args, tmp_dir=None, **kwargs):
    if tmp_dir is None:
        return
    replacement = (
        '.method public final a(Landroid/app/Activity;Landroid/net/Uri;)V\n'
        '    .locals 3\n'
        '\n'
        '    const-string p0, "activity"\n'
        '\n'
        '    invoke-static {p1, p0}, Lkotlin/jvm/internal/Intrinsics;->checkNotNullParameter(Ljava/lang/Object;Ljava/lang/String;)V\n'
        '\n'
        '    const-string p0, "pickedItem"\n'
        '\n'
        '    invoke-static {p2, p0}, Lkotlin/jvm/internal/Intrinsics;->checkNotNullParameter(Ljava/lang/Object;Ljava/lang/String;)V\n'
        '\n'
        '    new-instance v0, Landroid/content/Intent;\n'
        '\n'
        '    const-string v1, "android.intent.action.ATTACH_DATA"\n'
        '\n'
        '    invoke-direct {v0, v1}, Landroid/content/Intent;-><init>(Ljava/lang/String;)V\n'
        '\n'
        '    const-string v1, "image/*"\n'
        '\n'
        '    invoke-virtual {v0, p2, v1}, Landroid/content/Intent;->setDataAndType(Landroid/net/Uri;Ljava/lang/String;)Landroid/content/Intent;\n'
        '\n'
        '    const/4 v2, 0x1\n'
        '\n'
        '    invoke-virtual {v0, v2}, Landroid/content/Intent;->setFlags(I)Landroid/content/Intent;\n'
        '\n'
        '    const-string v2, "mimeType"\n'
        '\n'
        '    invoke-virtual {v0, v2, v1}, Landroid/content/Intent;->putExtra(Ljava/lang/String;Ljava/lang/String;)Landroid/content/Intent;\n'
        '\n'
        '    invoke-virtual {p1, v0}, Landroid/app/Activity;->startActivity(Landroid/content/Intent;)V\n'
        '\n'
        '    return-void\n'
        '.end method\n'
    )
    signature = 'public final a(Landroid/app/Activity;Landroid/net/Uri;)V'
    patched = False
    for smali in Path(tmp_dir).glob('smali*/com/oplus/gallery/pictureeditorpage/PictureEditorDM.smali'):
        data = smali.read_text(encoding='utf-8')
        fixed, count = re.subn(
            rf'(?ms)^\.method {re.escape(signature)}\n.*?^\.end method',
            replacement,
            data,
            count=1,
        )
        if count != 1:
            continue
        smali.write_text(fixed, encoding='utf-8')
        patched = True
        break
    if not patched:
        raise ValueError('OppoGallery2 wallpaper attach intent patch point not found')
